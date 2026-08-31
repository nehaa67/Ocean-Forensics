from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class SourceZone(BaseModel):
    """Estimated spill origin location, backward drift trajectory, and uncertainty zone."""
    estimated_origin: Tuple[float, float] = Field(..., description="Estimated origin coordinate (lon, lat)")
    estimated_spill_time: Optional[str] = Field(default=None, description="Estimated release time in UTC (ISO-8601)")
    drift_trajectory: List[Dict[str, Any]] = Field(
        default_factory=list, description="Step-by-step drift points with lon, lat, timestamp"
    )
    drift_direction: str = Field(
        default="backward", description="Drift direction: 'forward' (forecast) or 'backward' (hindcast)"
    )
    duration_hours: float = Field(default=1.0, description="Simulation duration in hours")
    timestep_seconds: float = Field(default=600.0, description="Time step in seconds between trajectory points")
    effective_velocity_m_s: Dict[str, float] = Field(
        default_factory=dict, description="Net drift velocity {'vx': float, 'vy': float} in m/s"
    )
    uncertainty_radius_m: float = Field(default=5000.0, description="Estimated search buffer radius in meters")
    crs_epsg: int = Field(default=4326, description="EPSG code of the coordinates")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Drift model and environmental inputs metadata")
    quality_warnings: List[str] = Field(default_factory=list, description="Drift warnings")
