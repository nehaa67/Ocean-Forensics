from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AISRecord(BaseModel):
    """Standardized single AIS vessel observation."""
    vessel_id: str = Field(..., description="MMSI, IMO, or unique vessel identifier")
    latitude: float = Field(..., description="Latitude coordinate in degrees")
    longitude: float = Field(..., description="Longitude coordinate in degrees")
    timestamp: str = Field(..., description="ISO-8601 timestamp in UTC")
    speed: float = Field(default=0.0, description="Vessel speed over ground in m/s")
    heading: float = Field(default=0.0, description="Vessel true heading or course over ground in degrees")
    vessel_name: Optional[str] = Field(default=None, description="Vessel name if available")
    vessel_type: Optional[str] = Field(default=None, description="Vessel type category (e.g., Tanker, Cargo)")
    source: str = Field(default="unknown", description="AIS provider source (e.g., Spire, AISHub, synthetic)")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Lineage metadata")
    quality_warnings: List[str] = Field(default_factory=list, description="Quality flags or warnings")


class VesselTrack(BaseModel):
    """Standardized chronological sequence and summary of vessel observations."""
    vessel_id: str = Field(..., description="Vessel identifier")
    first_timestamp: str = Field(..., description="First observed ISO-8601 timestamp in window")
    last_timestamp: str = Field(..., description="Last observed ISO-8601 timestamp in window")
    distance_m: float = Field(..., description="Distance in meters from spill reference point")
    time_delta_s: float = Field(..., description="Duration between first and last observation in seconds")
    average_speed_m_s: Optional[float] = Field(default=None, description="Average speed in m/s")
    heading_variance_deg: Optional[float] = Field(default=None, description="Heading standard deviation/variance in degrees")
    records: List[AISRecord] = Field(default_factory=list, description="Chronological list of AIS pings")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Track processing metadata")
    quality_warnings: List[str] = Field(default_factory=list, description="Quality warnings")
