"""satellite.py – provider interface and mock implementation for Sentinel/SAR data.

The production system will query a real satellite product archive / SAFE directory.
The deterministic mock reads from synthetic sample data for automated unit tests.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Optional, Dict, Any, Tuple

from backend.app.schemas.scene import SentinelScene


# ---------------------------------------------------------------------------
# Data structures (preserved for backward compatibility)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SatelliteMetadata:
    """Metadata describing a Sentinel‑1 SAR scene.

    Attributes
    ----------
    scene_id: str
        Identifier of the SAR scene.
    timestamp: str
        ISO‑8601 timestamp of the acquisition.
    transform: tuple[float, float, float, float, float, float]
        Affine transform that maps pixel coordinates to CRS coordinates.
    crs_epsg: int
        EPSG code of the coordinate reference system.
    """

    scene_id: str
    timestamp: str
    transform: Tuple[float, float, float, float, float, float]
    crs_epsg: int


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------
class SatelliteProvider(Protocol):
    """Abstract interface for a satellite metadata provider.

    Implementations must provide :meth:`get_scene_metadata` which returns a
    :class:`SatelliteMetadata` or :class:`SentinelScene` instance for the requested ``scene_id``.
    """

    def get_scene_metadata(self, scene_id: str) -> SatelliteMetadata: ...


# ---------------------------------------------------------------------------
# Mock implementation – deterministic, reads from synthetic sample data.
# ---------------------------------------------------------------------------
class MockSatelliteProvider:
    """Deterministic mock that returns the metadata stored in
    ``data/sample/metadata.json`` regardless of the requested ``scene_id``.
    """

    def __init__(self, data_root: Optional[Path] = None) -> None:
        if data_root is None:
            data_root = Path(__file__).resolve().parents[3] / "data" / "sample"
        self._metadata_path = data_root / "metadata.json"
        with self._metadata_path.open() as f:
            data = json.load(f)
        self._metadata = SatelliteMetadata(
            scene_id="synthetic_scene",
            timestamp="2023-01-01T00:00:00Z",
            transform=tuple(data["transform"]),
            crs_epsg=data["crs_epsg"],
        )

    def get_scene_metadata(self, scene_id: str) -> SatelliteMetadata:
        # In the deterministic mock we ignore ``scene_id`` and always return the
        # same synthetic metadata.
        return self._metadata

    def get_scene(self, scene_id: str) -> SentinelScene:
        """Returns standard SentinelScene Pydantic contract."""
        return SentinelScene(
            scene_id=self._metadata.scene_id,
            acquisition_timestamp=self._metadata.timestamp,
            crs_epsg=self._metadata.crs_epsg,
            transform=self._metadata.transform,
            bbox=(-180.0, -90.0, 180.0, 90.0),
            source_metadata={"provider": "MockSatelliteProvider"},
            provenance={"mode": "synthetic_test"},
            quality_warnings=[],
        )
