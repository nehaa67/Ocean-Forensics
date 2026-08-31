from __future__ import annotations
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class PredefinedIncidentSummary(BaseModel):
    """Brief metadata summary for a predefined historical incident."""
    incident_id: str = Field(..., description="Unique predefined incident identifier")
    name: str = Field(..., description="Incident name")
    description: str = Field(..., description="Brief description of the incident")
    observation_time: str = Field(..., description="ISO-8601 observation timestamp")
    available: bool = Field(default=True, description="Whether incident dataset files are present on disk")


class PredefinedIncidentDetail(BaseModel):
    """Detailed metadata and dataset file status for a predefined incident."""
    incident_id: str = Field(..., description="Unique incident identifier")
    name: str = Field(..., description="Incident name")
    description: str = Field(..., description="Incident description")
    observation_time: str = Field(..., description="ISO-8601 observation timestamp")
    location: Dict[str, Any] = Field(default_factory=dict, description="Geographic region and coordinates")
    timeline: Dict[str, Any] = Field(default_factory=dict, description="Key timeline timestamps")
    expected_files: Dict[str, str] = Field(default_factory=dict, description="Expected relative file paths")
    files_available: Dict[str, bool] = Field(default_factory=dict, description="Presence check on disk for each file")
    model_available: bool = Field(default=True, description="Whether the frozen U-Net segmentation checkpoint exists")
    outputs_available: Dict[str, bool] = Field(default_factory=dict, description="Presence of precomputed outputs")
    pipeline_readiness: str = Field(default="ready", description="Pipeline execution readiness status (ready, partial, missing_inputs)")
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="SAR sensor and product metadata")


class PredefinedIncidentRunRequest(BaseModel):
    """Request payload to trigger an investigation run on a predefined incident."""
    incident_id: Optional[str] = Field(default=None, description="Predefined incident identifier")
    mode: str = Field(default="investigation", description="Mode: 'investigation' or 'prevention'")
    force_recompute: bool = Field(default=False, description="Force recomputation instead of reusing valid cached outputs")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Analysis runtime configurations")
