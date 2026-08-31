"""weather.py – provider interface and mock implementation for wind data.

In production this will call meteorological APIs / NetCDF models (e.g., GFS, ERA5).
The mock reads synthetic environment data for unit tests.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Optional, Dict, Any

from backend.app.schemas.environment import WindField


# ---------------------------------------------------------------------------
# Data structures (preserved for backward compatibility)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class WindData:
    """Simple wind representation.

    Attributes
    ----------
    u: float
        East‑west component (m/s).
    v: float
        North‑south component (m/s).
    """

    u: float
    v: float


# ---------------------------------------------------------------------------
# Provider protocol
# ---------------------------------------------------------------------------
class WeatherProvider(Protocol):
    """Abstract interface for a wind data provider.

    Implementations must implement :meth:`get_wind` returning a
    :class:`WindData` or :class:`WindField` for a given ``scene_id``.
    """

    def get_wind(self, scene_id: str) -> WindData: ...


# ---------------------------------------------------------------------------
# Mock implementation – deterministic, reads from synthetic sample data.
# ---------------------------------------------------------------------------
class MockWeatherProvider:
    """Deterministic mock that returns the wind vector stored in
    ``data/sample/environment.json``.
    """

    def __init__(self, data_root: Optional[Path] = None) -> None:
        if data_root is None:
            data_root = Path(__file__).resolve().parents[3] / "data" / "sample"
        self._env_path = data_root / "environment.json"
        with self._env_path.open() as f:
            data = json.load(f)
        # The JSON stores "wind": [u, v]
        self._wind = WindData(u=float(data["wind"][0]), v=float(data["wind"][1]))

    def get_wind(self, scene_id: str) -> WindData:
        # Ignore scene_id – deterministic mock.
        return self._wind

    def get_wind_field(self, scene_id: str) -> WindField:
        """Returns standard WindField Pydantic contract."""
        speed = (self._wind.u ** 2 + self._wind.v ** 2) ** 0.5
        return WindField(
            u=self._wind.u,
            v=self._wind.v,
            speed_m_s=speed,
            source="MockWeatherProvider",
            provenance={"mode": "synthetic_test"},
            quality_warnings=[],
        )
