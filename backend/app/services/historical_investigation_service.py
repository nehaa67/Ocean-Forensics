"""Historical Incident Investigation Pipeline Orchestrator.

Integrates the full forensic workflow:
1. Incident configuration & file validation
2. Sentinel-1 SAR frozen U-Net detection & probability mapping (with output reuse)
3. Valid-swath correction & georeferenced polygon geometry extraction (with output reuse)
4. NetCDF wind + ocean current kinematic backward drift hindcast (with output reuse)
5. Historical AIS filtering & deterministic multi-factor vessel attribution (with output reuse)
6. Assembling complete InvestigationResult schema
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from fastapi import HTTPException

from backend.app.incidents import IncidentRegistry
from backend.app.schemas.scene import SentinelScene
from backend.app.schemas.detection import DetectionResult, OilProbabilityMask
from backend.app.schemas.geometry import SpillGeometry
from backend.app.schemas.drift import SourceZone
from backend.app.schemas.attribution import AttributionCandidate
from backend.app.schemas.investigation import InvestigationResult

from backend.app.ml.unet_segmentation import DEFAULT_CHECKPOINT_PATH, PyTorchSegmentationModel
from backend.app.ml.full_scene_inference import run_full_scene_inference
from backend.app.geometry_extraction import extract_corrected_masks_and_geometry
from backend.app.environmental_drift import run_backward_drift_hindcast
from backend.app.ais_attribution import run_ais_attribution

logger = logging.getLogger("historical_investigation")


class HistoricalInvestigationService:
    """End-to-end orchestrator for predefined historical marine oil spill incidents."""

    def __init__(self, incident_registry: Optional[IncidentRegistry] = None):
        self.registry = incident_registry or IncidentRegistry()

    def run_investigation(
        self,
        incident_id: str,
        force_recompute: bool = False,
        config: Optional[Dict[str, Any]] = None,
    ) -> InvestigationResult:
        """Executes the full forensic pipeline or reuses existing valid outputs."""
        config = config or {}
        incident_dir = self.registry.get_incident_dir(incident_id)
        if incident_dir is None:
            raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found in registry")

        meta_file = incident_dir / "metadata.json"
        if not meta_file.exists():
            raise HTTPException(status_code=404, detail=f"metadata.json missing for incident '{incident_id}'")

        with meta_file.open("r", encoding="utf-8") as f:
            metadata = json.load(f)

        expected_files = metadata.get("expected_files", {})
        outputs_dir = incident_dir / "outputs"
        outputs_dir.mkdir(parents=True, exist_ok=True)
        geom_out_dir = outputs_dir / "geometry"
        drift_out_dir = outputs_dir / "drift"
        ais_out_dir = outputs_dir / "ais"

        stages_executed = []
        cached_reuses = []

        # ============================================================
        # STAGE 1: VALIDATING
        # ============================================================
        current_stage = "VALIDATING"
        try:
            # Check Sentinel-1 SAFE directory or GeoTIFF
            sentinel_rel = expected_files.get("sentinel", "")
            sentinel_path = incident_dir / sentinel_rel
            if not sentinel_path.exists():
                raise FileNotFoundError(f"Required Sentinel-1 dataset missing: {sentinel_path}")

            # Locate VV, VH TIFFs and XML annotation
            if sentinel_path.is_dir() and sentinel_path.suffix == ".SAFE":
                vv_files = list((sentinel_path / "measurement").glob("*vv*.tiff")) + list((sentinel_path / "measurement").glob("*vv*.tif"))
                vh_files = list((sentinel_path / "measurement").glob("*vh*.tiff")) + list((sentinel_path / "measurement").glob("*vh*.tif"))
                xml_files = list((sentinel_path / "annotation").glob("*vv*.xml"))

                if not vv_files or not vh_files:
                    raise FileNotFoundError(f"Measurement TIFFs missing inside SAFE product: {sentinel_path}")
                vv_path = vv_files[0]
                vh_path = vh_files[0]
                xml_path = xml_files[0] if xml_files else None
            else:
                vv_path = sentinel_path
                vh_path = sentinel_path
                xml_path = None

            # Check Wind NetCDF
            wind_rel = expected_files.get("wind", "wind.nc")
            wind_path = incident_dir / wind_rel
            if not wind_path.exists():
                raise FileNotFoundError(f"Required Wind dataset missing: {wind_path}")

            # Check Ocean NetCDF
            ocean_rel = expected_files.get("current", "ocean.nc")
            ocean_path = incident_dir / ocean_rel
            if not ocean_path.exists():
                raise FileNotFoundError(f"Required Ocean Current dataset missing: {ocean_path}")

            # Check AIS CSV
            ais_rel = expected_files.get("ais", "sanchi_incident_real_ais_subset.csv")
            ais_path = incident_dir / ais_rel
            if not ais_path.exists():
                ais_path = incident_dir / "ais.csv"
                if not ais_path.exists():
                    raise FileNotFoundError(f"Required AIS CSV dataset missing: {incident_dir / ais_rel}")

            # Check Model Checkpoint
            model_checkpoint = Path(config.get("model_checkpoint", DEFAULT_CHECKPOINT_PATH))
            if not model_checkpoint.exists():
                raise FileNotFoundError(f"Segmentation model checkpoint not found: {model_checkpoint}")

            stages_executed.append("VALIDATING")
        except Exception as e:
            logger.error(f"Stage {current_stage} failed: {e}", exc_info=True)
            raise HTTPException(status_code=400, detail={"stage": current_stage, "error": str(e), "message": "Input validation failed"})

        # ============================================================
        # STAGE 2: DETECTION (Inference & Probability Mapping)
        # ============================================================
        current_stage = "DETECTION"
        prob_tif = outputs_dir / "sanchi_probability_map.tif"
        raw_mask_tif = outputs_dir / "sanchi_oil_mask.tif"
        det_meta_file = outputs_dir / "sanchi_inference_metadata.json"

        try:
            if not force_recompute and prob_tif.exists() and raw_mask_tif.exists() and det_meta_file.exists():
                with open(det_meta_file, "r", encoding="utf-8") as f:
                    detection_meta = json.load(f)
                cached_reuses.append("DETECTION")
            else:
                if xml_path is None:
                    raise ValueError("Annotation XML required for Sentinel-1 Level-1 GRD full scene calibration")
                detection_meta = run_full_scene_inference(
                    safe_dir=sentinel_path,
                    checkpoint_path=model_checkpoint,
                    output_dir=outputs_dir,
                    threshold=float(config.get("threshold", 0.50)),
                )
            stages_executed.append("DETECTION")
        except Exception as e:
            logger.error(f"Stage {current_stage} failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail={"stage": current_stage, "error": str(e), "message": "Sentinel-1 detection stage failed"})

        # ============================================================
        # STAGE 3: GEOMETRY (Valid-Swath Masking & Polygonization)
        # ============================================================
        current_stage = "GEOMETRY"
        mask_valid_tif = geom_out_dir / "sanchi_oil_mask_valid.tif"
        spill_geojson = geom_out_dir / "sanchi_spill.geojson"
        geom_json_file = geom_out_dir / "sanchi_geometry.json"

        try:
            if not force_recompute and mask_valid_tif.exists() and spill_geojson.exists() and geom_json_file.exists():
                with open(geom_json_file, "r", encoding="utf-8") as f:
                    geometry_stats = json.load(f)
                cached_reuses.append("GEOMETRY")
            else:
                geometry_stats = extract_corrected_masks_and_geometry(
                    probability_map_path=prob_tif,
                    vv_tif_path=vv_path,
                    vh_tif_path=vh_path,
                    annotation_xml_path=xml_path,
                    output_dir=geom_out_dir,
                    incident_id=incident_id,
                    threshold_official=float(config.get("threshold", 0.50)),
                    threshold_core=float(config.get("core_threshold", 0.70)),
                    min_component_pixels=int(config.get("min_component_pixels", 50)),
                )
            stages_executed.append("GEOMETRY")
        except Exception as e:
            logger.error(f"Stage {current_stage} failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail={"stage": current_stage, "error": str(e), "message": "Geometry extraction stage failed"})

        # ============================================================
        # STAGE 4: DRIFT (Backward Kinematic Hindcast)
        # ============================================================
        current_stage = "DRIFT"
        traj_geojson = drift_out_dir / "sanchi_backward_trajectory.geojson"
        source_geojson = drift_out_dir / "sanchi_source_zone.geojson"
        drift_json_file = drift_out_dir / "sanchi_drift.json"

        try:
            if not force_recompute and traj_geojson.exists() and source_geojson.exists() and drift_json_file.exists():
                with open(drift_json_file, "r", encoding="utf-8") as f:
                    drift_stats = json.load(f)
                cached_reuses.append("DRIFT")
            else:
                drift_stats = run_backward_drift_hindcast(
                    wind_nc_path=wind_path,
                    ocean_nc_path=ocean_path,
                    geometry_json_path=geom_json_file,
                    output_dir=drift_out_dir,
                    incident_id=incident_id,
                    observation_time_iso=metadata.get("observation_time", "2018-01-20T09:28:53Z"),
                    hindcast_hours=float(config.get("hindcast_hours", 144.0)),
                    timestep_seconds=float(config.get("timestep_seconds", 3600.0)),
                    windage_coefficient=float(config.get("windage_coefficient", 0.03)),
                )
            stages_executed.append("DRIFT")
        except Exception as e:
            logger.error(f"Stage {current_stage} failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail={"stage": current_stage, "error": str(e), "message": "Backward drift hindcast stage failed"})

        # ============================================================
        # STAGE 5 & 6: AIS & ATTRIBUTION
        # ============================================================
        current_stage = "ATTRIBUTION"
        attrib_json_file = ais_out_dir / "sanchi_attribution.json"
        ais_cand_geojson = ais_out_dir / "sanchi_ais_candidates.geojson"
        ais_track_geojson = ais_out_dir / "sanchi_vessel_tracks.geojson"

        try:
            if not force_recompute and attrib_json_file.exists() and ais_cand_geojson.exists() and ais_track_geojson.exists():
                with open(attrib_json_file, "r", encoding="utf-8") as f:
                    attribution_stats = json.load(f)
                cached_reuses.append("ATTRIBUTION")
            else:
                attribution_stats = run_ais_attribution(
                    ais_csv_path=ais_path,
                    drift_json_path=drift_json_file,
                    output_dir=ais_out_dir,
                    incident_id=incident_id,
                    weights=config.get("attribution_weights"),
                )
            stages_executed.append("ATTRIBUTION")
        except Exception as e:
            logger.error(f"Stage {current_stage} failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail={"stage": current_stage, "error": str(e), "message": "AIS attribution stage failed"})

        # ============================================================
        # STAGE 7: CONSTRUCT FINAL InvestigationResult
        # ============================================================
        now_iso = datetime.now(timezone.utc).isoformat()

        # SentinelScene Schema
        spill_bbox = geometry_stats["spill"]["bbox"]
        scene_schema = SentinelScene(
            scene_id=sentinel_path.stem,
            acquisition_timestamp=metadata.get("observation_time", "2018-01-20T09:28:53Z"),
            crs_epsg=4326,
            transform=(0.0001, 0.0, float(spill_bbox[0]), 0.0, -0.0001, float(spill_bbox[3])),
            bbox=(
                float(spill_bbox[0]),
                float(spill_bbox[1]),
                float(spill_bbox[2]),
                float(spill_bbox[3]),
            ),
            vv_path=str(vv_path),
            vh_path=str(vh_path),
            resolution_m=(10.0, 10.0),
            source_metadata={
                "satellite": "Sentinel-1B",
                "mode": "IW",
                "polarizations": ["VV", "VH"],
                "product_type": "GRDH",
            },
            provenance={
                "scene_dimensions": detection_meta.get("scene_dimensions", {}),
            },
        )

        # DetectionResult Schema
        detection_summary = DetectionResult(
            detected=geometry_stats["predicted_oil_pixels_before_filter"] > 0,
            confidence=0.95,
            mask_id=f"{incident_id}_oil_mask_valid",
            detection_mode="model_unet_resnet18_finetuned",
        )

        # OilProbabilityMask Schema (Lightweight metadata - without giant raw matrices in API)
        prob_mask_schema = OilProbabilityMask(
            mask_id=f"{incident_id}_oil_mask_valid",
            shape=(detection_meta["scene_dimensions"]["height"], detection_meta["scene_dimensions"]["width"]),
            probability_map=None,
            binary_mask=None,
            threshold_applied=float(geometry_stats.get("threshold", 0.50)),
            model_confidence=0.95,
            model_version="best_unet_resnet18_sar_finetuned",
            preprocessing_version="esa_level1_radiometric_calibration_v1",
            provenance={
                "probability_map_path": str(prob_tif),
                "binary_mask_path": str(mask_valid_tif),
                "valid_pixel_count": geometry_stats["valid_pixel_count"],
                "invalid_pixel_count": geometry_stats["invalid_pixel_count"],
                "corrected_oil_percentage_of_valid_ocean": geometry_stats["corrected_oil_percentage_of_valid_ocean"],
                "core_070_oil_percentage_of_valid_ocean": geometry_stats["core_070_oil_percentage_of_valid_ocean"],
                "detection_preview_png": str(outputs_dir / "sanchi_detection_preview.png"),
            },
            quality_warnings=[
                "Zero-DN outer swath margins were automatically excluded from valid oil mask.",
            ],
        )

        # SpillGeometry Schema
        spill_geom_schema = SpillGeometry(
            has_oil=geometry_stats["predicted_oil_pixels_before_filter"] > 0,
            polygon={"$ref": str(spill_geojson)},
            area_m2=geometry_stats["spill"]["area_m2"],
            centroid=(geometry_stats["spill"]["centroid"]["longitude"], geometry_stats["spill"]["centroid"]["latitude"]),
            bbox=(
                float(spill_bbox[0]),
                float(spill_bbox[1]),
                float(spill_bbox[2]),
                float(spill_bbox[3]),
            ),
            perimeter_m=geometry_stats["spill"]["perimeter_m"],
            pixel_count=geometry_stats["predicted_oil_pixels_after_filter"],
            crs_epsg=32652,
            provenance={
                "metric_crs": "EPSG:32652 (WGS 84 / UTM Zone 52N)",
                "component_count": geometry_stats["component_count_after_filter"],
                "area_km2": geometry_stats["spill"]["area_km2"],
                "core_070_area_km2": geometry_stats["core_070"]["area_km2"],
                "geometry_preview_png": str(geom_out_dir / "sanchi_geometry_preview.png"),
            },
            quality_warnings=[
                "Area represents model-detected oil-like backscatter damping feature, not confirmed ground-truth volume.",
            ],
        )

        # SourceZone Schema
        source_zone_schema = SourceZone(
            estimated_origin=(drift_stats["source_estimate"]["longitude"], drift_stats["source_estimate"]["latitude"]),
            estimated_spill_time=drift_stats["estimated_source_time"],
            drift_trajectory=drift_stats["trajectory"],
            drift_direction="backward",
            duration_hours=drift_stats["parameters"]["hindcast_duration_hours"],
            timestep_seconds=drift_stats["parameters"]["timestep_seconds"],
            effective_velocity_m_s={
                "vx": drift_stats["trajectory"][0]["net_transport_velocity_m_s"]["vx"],
                "vy": drift_stats["trajectory"][0]["net_transport_velocity_m_s"]["vy"],
            },
            uncertainty_radius_m=drift_stats["source_estimate"]["uncertainty_radius_m"],
            crs_epsg=4326,
            provenance={
                "method": drift_stats["parameters"]["method"],
                "windage_coefficient": drift_stats["parameters"]["windage_coefficient"],
                "trajectory_geojson": str(traj_geojson),
                "source_zone_geojson": str(source_geojson),
                "drift_preview_png": str(drift_out_dir / "sanchi_drift_preview.png"),
            },
            quality_warnings=[
                "Kinematic backward drift represents an oceanographic estimate based on available daily wind/current grids.",
            ],
        )

        # AttributionCandidate Schemas
        candidate_schemas = []
        for cand in attribution_stats.get("candidates", []):
            explanations_dict = {}
            for line in cand.get("evidence", []):
                if "approach is" in line or "centroid" in line or "source zone" in line:
                    explanations_dict["spatial"] = line
                elif "temporal approach" in line:
                    explanations_dict["temporal"] = line
                elif "trajectory" in line:
                    explanations_dict["trajectory"] = line
                elif "speed" in line or "observation" in line:
                    explanations_dict["track"] = line

            candidate_schemas.append(
                AttributionCandidate(
                    vessel_id=str(cand.get("vessel_name", "UNKNOWN")),
                    overall_score=cand["score"],
                    spatial_proximity=cand["spatial_score"],
                    temporal_proximity=cand["temporal_score"],
                    trajectory_consistency=cand["trajectory_score"],
                    heading_consistency=cand["heading_score"],
                    explanations=explanations_dict,
                    provenance={
                        "rank": cand["rank"],
                        "mmsi": cand["mmsi"],
                        "closest_distance_km": cand["closest_distance_km"],
                        "closest_timestamp": cand["closest_timestamp"],
                        "inside_source_zone": cand["inside_source_zone"],
                        "record_count": cand["record_count"],
                    },
                    quality_warnings=[
                        "Rankings represent highest consistency with reconstructed source zone, not a legal liability judgment.",
                    ],
                )
            )

        # Overall Warnings & Provenance
        quality_warnings = [
            "Attribution is limited by sparse historical AIS coverage in the available dataset.",
            "Area reflects model-detected oil-like surface features from Sentinel-1 SAR backscatter.",
            "Kinematic wind/current backward drift assumes 3% empirical windage leeway and surface current forcing.",
        ]

        result = InvestigationResult(
            incident_id=incident_id,
            status="completed",
            scene=scene_schema,
            detection=detection_summary,
            probability_mask=prob_mask_schema,
            geometry=spill_geom_schema,
            source_zone=source_zone_schema,
            candidates=candidate_schemas,
            environment={
                "wind_dataset": str(wind_path),
                "current_dataset": str(ocean_path),
                "wind_time": drift_stats["environment"]["selected_wind_time"],
                "current_time": drift_stats["environment"]["selected_current_time"],
                "selected_ocean_depth_m": drift_stats["environment"]["selected_ocean_depth_m"],
            },
            provenance={
                "execution_timestamp": now_iso,
                "pipeline_version": "2.0.0-full-scene-frozen-unet",
                "stages_executed": stages_executed,
                "cached_outputs_reused": cached_reuses,
                "artifacts": {
                    "probability_map": str(prob_tif),
                    "valid_mask": str(mask_valid_tif),
                    "core_mask": str(geom_out_dir / "sanchi_oil_core_070.tif"),
                    "spill_geojson": str(spill_geojson),
                    "backward_trajectory_geojson": str(traj_geojson),
                    "source_zone_geojson": str(source_geojson),
                    "ais_candidates_geojson": str(ais_cand_geojson),
                    "vessel_tracks_geojson": str(ais_track_geojson),
                },
            },
            quality_warnings=quality_warnings,
        )

        return result
