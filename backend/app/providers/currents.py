"""currents.py – provider interface and mock implementation for ocean current data.

The production version will query marine hydrodynamic models (e.g., HYCOM, CMEMS).
The mock version reads deterministic current vectors for automated unit tests.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Optional, Dict, Any

from backend.app.schemas.environment import CurrentField


# ---------------------------------------------------------------------------
# Data structures (preserved for backward compatibility)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class CurrentData:
    """Simple ocean current representation.

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
class CurrentsProvider(Protocol):
    """Abstract interface for a current data provider.

    Implementations must provide :meth:`get_current` returning a
    :class:`CurrentData` or :class:`CurrentField` for a given ``scene_id``.
    """

    def get_current(self, scene_id: str) -> CurrentData: ...


# ---------------------------------------------------------------------------
# Mock implementation – deterministic, reads from synthetic sample data.
# ---------------------------------------------------------------------------
class MockCurrentsProvider:
    """Deterministic mock that returns the current vector stored in
    ``data/sample/environment.json``.
    """

    def __init__(self, data_root: Optional[Path] = None) -> None:
        if data_root is None:
            data_root = Path(__file__).resolve().parents[3] / "data" / "sample"
        self._env_path = data_root / "environment.json"
        with self._env_path.open() as f:
            data = json.load(f)
        self._current = CurrentData(u=float(data["current"][0]), v=float(data["current"][1]))

    def get_current(self, scene_id: str) -> CurrentData:
        # Ignore scene_id – deterministic mock.
        return self._current

    def get_current_field(self, scene_id: str) -> CurrentField:
        """Returns standard CurrentField Pydantic contract."""
        speed = (self._current.u ** 2 + self._current.v ** 2) ** 0.5
        return CurrentField(
            u=self._current.u,
            v=self._current.v,
            speed_m_s=speed,
            source="MockCurrentsProvider",
            provenance={"mode": "synthetic_test"},
            quality_warnings=[],
        )
