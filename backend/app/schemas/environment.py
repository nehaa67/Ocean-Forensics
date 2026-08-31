from __future__ import annotations
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class WindField(BaseModel):
    """Standardized wind observation or forecast at a given time and area."""
    u: float = Field(..., description="Zonal (East-West) component in m/s")
    v: float = Field(..., description="Meridional (North-South) component in m/s")
    speed_m_s: Optional[float] = Field(default=None, description="Scalar wind speed in m/s")
    direction_deg: Optional[float] = Field(default=None, description="Wind direction (degrees from North, blowing towards)")
    timestamp: Optional[str] = Field(default=None, description="ISO-8601 observation/forecast timestamp")
    source: str = Field(default="unknown", description="Data source identifier (e.g., GFS, ERA5, synthetic)")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Metadata lineage")
    quality_warnings: List[str] = Field(default_factory=list, description="Quality warnings or flags")


class CurrentField(BaseModel):
    """Standardized ocean surface current observation or model output."""
    u: float = Field(..., description="Zonal (East-West) current component in m/s")
    v: float = Field(..., description="Meridional (North-South) current component in m/s")
    speed_m_s: Optional[float] = Field(default=None, description="Scalar current speed in m/s")
    direction_deg: Optional[float] = Field(default=None, description="Current flow direction in degrees")
    timestamp: Optional[str] = Field(default=None, description="ISO-8601 observation/model timestamp")
    source: str = Field(default="unknown", description="Data source identifier (e.g., HYCOM, CMEMS, synthetic)")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Metadata lineage")
    quality_warnings: List[str] = Field(default_factory=list, description="Quality warnings or flags")
