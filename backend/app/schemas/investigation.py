from __future__ import annotations
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.scene import SentinelScene
from backend.app.schemas.detection import DetectionResult, OilProbabilityMask
from backend.app.schemas.geometry import SpillGeometry
from backend.app.schemas.drift import SourceZone
from backend.app.schemas.attribution import AttributionCandidate


class InvestigationResult(BaseModel):
    """Complete end-to-end investigation result for an incident."""
    incident_id: str = Field(..., description="Incident identifier (e.g., SANCHI-2018-01-20)")
    status: str = Field(default="completed", description="Investigation status (completed, failed, partial)")
    scene: Optional[SentinelScene] = Field(default=None, description="Observed SAR scene metadata")
    detection: Optional[DetectionResult] = Field(default=None, description="Detection mask summary")
    probability_mask: Optional[OilProbabilityMask] = Field(default=None, description="Full oil probability mask")
    geometry: Optional[SpillGeometry] = Field(default=None, description="Spill geometric characterization")
    source_zone: Optional[SourceZone] = Field(default=None, description="Hindcast origin and trajectory")
    candidates: List[AttributionCandidate] = Field(default_factory=list, description="Ranked candidate vessels")
    environment: Dict[str, Any] = Field(default_factory=dict, description="Environmental conditions used")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Execution timestamp and pipeline version")
    quality_warnings: List[str] = Field(default_factory=list, description="Overall quality warnings")
