"""ais_provider.py – provider interface and mock implementation for AIS vessel records.

The production system will query historical/live AIS services (e.g., Spire, AISHub).
The deterministic mock reads synthetic data for automated tests.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, List, Optional

from backend.app.schemas.ais import AISRecord as SchemaAISRecord


# ---------------------------------------------------------------------------
# Data structures (preserved for backward compatibility)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AISRecord:
    """A single AIS vessel observation.

    Attributes
    ----------
    vessel_id: str
    latitude: float
    longitude: float
    timestamp: str  # ISO‑8601 string
    speed: float   # m/s
    heading: float # degrees
    """

    vessel_id: str
    latitude: float
    longitude: float
    timestamp: str
    speed: float
    heading: float


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------
class AISProvider(Protocol):
    """Abstract interface for an AIS data provider.

    Implementations must provide :meth:`get_records` returning a list of
    :class:`AISRecord` for the requested ``scene_id`` (or any identifier).
    """

    def get_records(self, scene_id: str) -> List[AISRecord]: ...


# ---------------------------------------------------------------------------
# Mock implementation – deterministic, reads from synthetic sample data.
# ---------------------------------------------------------------------------
class MockAISProvider:
    """Deterministic mock that returns the AIS records stored in
    ``data/sample/ais.json`` regardless of the requested ``scene_id``.
    """

    def __init__(self, data_root: Optional[Path] = None) -> None:
        if data_root is None:
            data_root = Path(__file__).resolve().parents[3] / "data" / "sample"
        self._ais_path = data_root / "ais.json"
        with self._ais_path.open() as f:
            raw = json.load(f)
        # Convert numeric values explicitly to float
        self._records: List[AISRecord] = [
            AISRecord(
                vessel_id=str(rec["vessel_id"]),
                latitude=float(rec["latitude"]),
                longitude=float(rec["longitude"]),
                timestamp=str(rec["timestamp"]),
                speed=float(rec.get("speed", 0.0)),
                heading=float(rec.get("heading", 0.0)),
            )
            for rec in raw
        ]

    def get_records(self, scene_id: str) -> List[AISRecord]:
        # Ignore scene_id – deterministic mock.
        return self._records

    def get_schema_records(self, scene_id: str) -> List[SchemaAISRecord]:
        """Returns records as standard AISRecord Pydantic models."""
        return [
            SchemaAISRecord(
                vessel_id=r.vessel_id,
                latitude=r.latitude,
                longitude=r.longitude,
                timestamp=r.timestamp,
                speed=r.speed,
                heading=r.heading,
                source="MockAISProvider",
                provenance={"mode": "synthetic_test"},
            )
            for r in self._records
        ]
