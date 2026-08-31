from __future__ import annotations
from typing import Dict, Any, List
from pydantic import BaseModel, Field


class AttributionCandidate(BaseModel):
    """Ranked candidate vessel with explainable evidentiary scores."""
    vessel_id: str = Field(..., description="Vessel identifier (MMSI / IMO)")
    overall_score: float = Field(..., ge=0.0, le=1.0, description="Weighted composite score [0.0, 1.0]")
    spatial_proximity: float = Field(..., ge=0.0, le=1.0, description="Normalized spatial proximity score")
    temporal_proximity: float = Field(..., ge=0.0, le=1.0, description="Normalized temporal proximity score")
    trajectory_consistency: float = Field(..., ge=0.0, le=1.0, description="Normalized trajectory consistency score")
    heading_consistency: float = Field(..., ge=0.0, le=1.0, description="Normalized heading consistency score")
    explanations: Dict[str, str] = Field(default_factory=dict, description="Human-readable rationale for each metric")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Attribution algorithm weighting and metadata")
    quality_warnings: List[str] = Field(default_factory=list, description="Caveats or data sparsity warnings")
