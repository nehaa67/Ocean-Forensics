from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

from backend.app.schemas.incident import (
    PredefinedIncidentSummary,
    PredefinedIncidentDetail,
)
from backend.app.ml.unet_segmentation import DEFAULT_CHECKPOINT_PATH


class IncidentRegistry:
    """Registry and resolver for predefined historical marine oil spill incidents."""

    def __init__(self, data_root: Optional[Path] = None) -> None:
        if data_root is not None:
            self._data_root = Path(data_root)
        else:
            env_root = os.environ.get("INVESTIGATION_DATA_ROOT") or os.environ.get("INCIDENTS_DATA_ROOT")
            if env_root:
                self._data_root = Path(env_root)
                if not (self._data_root / "incidents").exists() and self._data_root.name != "incidents":
                    self._data_root = self._data_root / "incidents"
            else:
                # Default search paths relative to project root
                candidates = [
                    Path(__file__).resolve().parents[3] / "data" / "incidents",
                    Path(__file__).resolve().parents[3] / "backend" / "data" / "incidents",
                    Path("data/incidents").resolve(),
                ]
                self._data_root = next((c for c in candidates if c.exists()), candidates[0])

    @property
    def data_root(self) -> Path:
        return self._data_root

    def list_incidents(self) -> List[PredefinedIncidentSummary]:
        """Discover and list all registered predefined incidents."""
        if not self._data_root.exists():
            return []

        summaries: List[PredefinedIncidentSummary] = []
        for item in self._data_root.iterdir():
            if item.is_dir():
                meta_file = item / "metadata.json"
                if meta_file.exists():
                    try:
                        with meta_file.open("r", encoding="utf-8") as f:
                            data = json.load(f)
                        incident_id = data.get("incident_id", item.name)
                        summaries.append(
                            PredefinedIncidentSummary(
                                incident_id=incident_id,
                                name=data.get("name", item.name),
                                description=data.get("description", ""),
                                observation_time=data.get("observation_time", ""),
                                available=True,
                            )
                        )
                    except Exception:
                        continue
        summaries.sort(key=lambda s: s.incident_id)
        return summaries

    def get_incident(self, incident_id: str) -> Optional[PredefinedIncidentDetail]:
        """Retrieve detailed metadata and file availability status for an incident."""
        incident_dir = self.get_incident_dir(incident_id)
        if incident_dir is None:
            return None

        meta_file = incident_dir / "metadata.json"
        if not meta_file.exists():
            return None

        with meta_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        expected_files = data.get("expected_files", {})
        files_available: Dict[str, bool] = {}
        for key, rel_path in expected_files.items():
            full_path = incident_dir / rel_path
            # Check fallback for AIS if not directly at expected path
            if not full_path.exists() and key == "ais":
                fallback = incident_dir / "ais.csv"
                files_available[key] = fallback.exists()
            else:
                files_available[key] = full_path.exists()

        # Check Model Checkpoint Existence
        model_available = DEFAULT_CHECKPOINT_PATH.exists()

        # Check Previous Output Artifacts Existence
        outputs_dir = incident_dir / "outputs"
        outputs_available = {
            "probability_map": (outputs_dir / "sanchi_probability_map.tif").exists(),
            "oil_mask": (outputs_dir / "sanchi_oil_mask.tif").exists(),
            "geometry_json": (outputs_dir / "geometry" / "sanchi_geometry.json").exists(),
            "spill_geojson": (outputs_dir / "geometry" / "sanchi_spill.geojson").exists(),
            "drift_json": (outputs_dir / "drift" / "sanchi_drift.json").exists(),
            "source_zone_geojson": (outputs_dir / "drift" / "sanchi_source_zone.geojson").exists(),
            "attribution_json": (outputs_dir / "ais" / "sanchi_attribution.json").exists(),
        }

        all_files_ok = all(files_available.values()) if files_available else False
        pipeline_readiness = "ready" if (all_files_ok and model_available) else "missing_inputs"

        return PredefinedIncidentDetail(
            incident_id=data.get("incident_id", incident_id),
            name=data.get("name", incident_id),
            description=data.get("description", ""),
            observation_time=data.get("observation_time", ""),
            location=data.get("location", {}),
            timeline=data.get("timeline", {}),
            expected_files=expected_files,
            files_available=files_available,
            model_available=model_available,
            outputs_available=outputs_available,
            pipeline_readiness=pipeline_readiness,
            source_metadata=data.get("source_metadata", {}),
        )

    def get_incident_dir(self, incident_id: str) -> Optional[Path]:
        """Resolve the directory path for an incident ID."""
        target_dir = self._data_root / incident_id
        if target_dir.is_dir():
            return target_dir
        return None
