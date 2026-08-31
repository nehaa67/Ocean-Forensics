"""Pydantic schemas and data contracts for Prevention and Early-Warning Risk Assessment."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    """Deterministic risk classification level for vessels in the forecast zone."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class AtRiskVessel(BaseModel):
    """Characterization of a vessel potentially affected by the predicted oil spill."""
    vessel_id: str = Field(..., description="Vessel identifier (Name or MMSI)")
    vessel_name: Optional[str] = Field(default=None, description="Vessel name")
    mmsi: Optional[str] = Field(default=None, description="Maritime Mobile Service Identity")
    risk_level: RiskLevel = Field(..., description="Risk tier: HIGH, MEDIUM, or LOW")
    distance_to_spill_km: float = Field(..., description="Current distance to observed spill centroid in km")
    distance_to_trajectory_km: float = Field(..., description="Minimum distance to predicted drift trajectory in km")
    inside_impact_zone: bool = Field(default=False, description="True if within the forecast impact uncertainty zone")
    eta_minutes: Optional[float] = Field(default=None, description="Estimated time to encounter in minutes (if approaching)")
    closest_approach_time: Optional[str] = Field(default=None, description="ISO-8601 timestamp of closest encounter")
    current_position: Tuple[float, float] = Field(..., description="Vessel position (lon, lat)")
    speed_knots: Optional[float] = Field(default=None, description="Speed over ground in knots")
    heading_deg: Optional[float] = Field(default=None, description="Heading / course in degrees")
    explanation: str = Field(..., description="Human-readable deterministic explanation of the assigned risk level")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Metadata lineage for this calculation")


class SpillSummary(BaseModel):
    """Summary of detected oil spill characteristics."""
    detected: bool = Field(default=True, description="Whether oil was detected")
    area_m2: float = Field(default=0.0, description="Spill surface area in square meters")
    area_km2: float = Field(default=0.0, description="Spill surface area in square kilometers")
    confidence: float = Field(default=0.95, description="Model detection confidence")
    centroid: Tuple[float, float] = Field(..., description="Spill centroid (lon, lat)")
    bbox: Optional[Tuple[float, float, float, float]] = Field(default=None, description="Bounding box [min_x, min_y, max_x, max_y]")


class ForecastSummary(BaseModel):
    """Kinematic forward drift trajectory and impact zone forecast summary."""
    forecast_duration_hours: float = Field(..., description="Forecast horizon in hours (e.g. 1, 3, 6, 12, 24)")
    timestep_seconds: float = Field(default=600.0, description="Integration step in seconds")
    predicted_movement_direction: str = Field(..., description="General compass direction of predicted transport (e.g. Northeast, South)")
    total_drift_distance_km: float = Field(..., description="Total forward displacement in km")
    mean_drift_speed_m_s: float = Field(..., description="Average transport velocity in m/s")
    impact_zone_radius_km: float = Field(..., description="Uncertainty radius of the predicted impact zone in km")
    trajectory_points_count: int = Field(..., description="Number of waypoints in forecast")
    effective_velocity_m_s: Dict[str, float] = Field(default_factory=dict, description="Net velocity components {'vx': float, 'vy': float}")


class PreventionResult(BaseModel):
    """Complete end-to-end early-warning prevention and risk assessment response."""
    analysis_id: str = Field(..., description="Investigation workspace or incident identifier")
    mode: str = Field(default="prevention", description="Operational mode: 'prevention'")
    status: str = Field(default="completed", description="Status: 'completed' or 'failed'")
    observation_time: str = Field(..., description="Observation timestamp of the initial spill detection")
    forecast_start_time: str = Field(..., description="Start timestamp of the forward forecast")
    forecast_target_time: str = Field(..., description="End timestamp of the forward forecast")
    spill_summary: SpillSummary = Field(..., description="Detected spill geometry and area")
    forecast_summary: ForecastSummary = Field(..., description="Forward drift forecast and movement trajectory")
    at_risk_vessels: List[AtRiskVessel] = Field(default_factory=list, description="Ranked list of vessels by risk level")
    high_risk_count: int = Field(default=0, description="Count of HIGH risk vessels")
    medium_risk_count: int = Field(default=0, description="Count of MEDIUM risk vessels")
    low_risk_count: int = Field(default=0, description="Count of LOW risk vessels")
    environment: Dict[str, Any] = Field(default_factory=dict, description="Environmental wind and current forcing used")
    artifacts: Dict[str, str] = Field(default_factory=dict, description="File paths/URIs for generated GeoJSON, JSON, and PNG preview artifacts")
    quality_warnings: List[str] = Field(default_factory=list, description="Caveats, assumptions, and forecast limitations")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Execution runtime metadata and software versions")


class PredictionRequest(BaseModel):
    """Payload to trigger forward drift prediction and risk assessment."""
    analysis_id: Optional[str] = Field(default=None, description="Existing investigation analysis_id (if referencing workspace)")
    forecast_hours: float = Field(default=6.0, description="Forecast duration in hours (e.g. 1, 3, 6, 12, 24)")
    timestep_seconds: float = Field(default=600.0, description="Integration timestep in seconds")
    windage: float = Field(default=0.03, description="Windage leeway fraction (default 3%)")
    warning_distance_km: float = Field(default=10.0, description="Warning distance threshold for MEDIUM risk in km")
    high_risk_distance_km: float = Field(default=3.0, description="Impact distance threshold for HIGH risk in km")
    spill_centroid: Optional[Tuple[float, float]] = Field(default=None, description="Optional manual spill centroid (lon, lat)")
    spill_area_km2: Optional[float] = Field(default=None, description="Optional manual spill area in km2")
    wind_vector: Optional[Tuple[float, float]] = Field(default=None, description="Optional manual wind vector (u, v) in m/s")
    current_vector: Optional[Tuple[float, float]] = Field(default=None, description="Optional manual ocean current vector (u, v) in m/s")
    ais_records: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional direct AIS records list")


class RiskRequest(BaseModel):
    """Payload for risk assessment queries."""
    analysis_id: Optional[str] = Field(default=None, description="Investigation analysis_id")
    forecast_hours: float = Field(default=6.0, description="Forecast horizon in hours")
    warning_distance_km: float = Field(default=10.0, description="Distance threshold for warning in km")
