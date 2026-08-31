from __future__ import annotations
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class InvestigationSourceType(str, Enum):
    PREDEFINED_INCIDENT = "predefined_incident"
    UPLOADED_DATASET = "uploaded_dataset"


class InvestigationMode(str, Enum):
    INVESTIGATION = "investigation"
    PREVENTION = "prevention"


class InvestigationStatus(str, Enum):
    CREATED = "created"
    UPLOADING = "uploading"
    READY = "ready"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileStatus(BaseModel):
    """Status of an uploaded dataset component."""
    uploaded: bool = Field(default=False, description="Whether the file has been uploaded")
    valid: bool = Field(default=False, description="Whether the uploaded file passes format validation")
    filename: Optional[str] = Field(default=None, description="Uploaded filename")
    size_bytes: Optional[int] = Field(default=None, description="File size in bytes on disk")
    format: Optional[str] = Field(default=None, description="Detected format (e.g. SAFE, TIFF, NetCDF, CSV)")
    error: Optional[str] = Field(default=None, description="Validation error message if invalid")


class InvestigationFilesStatus(BaseModel):
    """Status of all input data files for an investigation."""
    sentinel: FileStatus = Field(default_factory=FileStatus, description="Sentinel-1 SAR raster or SAFE archive")
    wind: FileStatus = Field(default_factory=FileStatus, description="Wind data (NetCDF / CSV / JSON)")
    current: FileStatus = Field(default_factory=FileStatus, description="Ocean current data (NetCDF / CSV / JSON)")
    ais: FileStatus = Field(default_factory=FileStatus, description="AIS vessel tracking data (CSV / JSON)")


class InvestigationCreateRequest(BaseModel):
    """Request payload to create a new investigation workspace."""
    mode: InvestigationMode = Field(default=InvestigationMode.INVESTIGATION, description="Analysis mode")
    title: Optional[str] = Field(default=None, description="Optional title or user reference")
    description: Optional[str] = Field(default=None, description="Optional notes or description")


class InvestigationCreateResponse(BaseModel):
    """Response returned upon creating a new investigation."""
    analysis_id: str = Field(..., description="Unique generated investigation identifier (e.g., INV-123456)")
    status: InvestigationStatus = Field(default=InvestigationStatus.CREATED, description="Initial workspace status")
    created_at: str = Field(..., description="ISO-8601 creation timestamp")
    mode: InvestigationMode = Field(default=InvestigationMode.INVESTIGATION, description="Configured mode")


class InvestigationValidationResult(BaseModel):
    """Validation report checking data readiness for a target analysis mode."""
    analysis_id: str = Field(..., description="Investigation identifier")
    is_valid: bool = Field(..., description="True if minimum required files are uploaded and valid")
    mode: InvestigationMode = Field(..., description="Evaluated analysis mode")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings (e.g., missing optional data)")
    errors: List[str] = Field(default_factory=list, description="Fatal errors preventing execution")


class InvestigationStatusResponse(BaseModel):
    """Comprehensive status response for an uploaded or predefined investigation."""
    analysis_id: str = Field(..., description="Investigation identifier")
    status: InvestigationStatus = Field(..., description="Current processing/readiness status")
    source_type: InvestigationSourceType = Field(..., description="Source: predefined_incident or uploaded_dataset")
    mode: InvestigationMode = Field(..., description="Investigation mode: investigation or prevention")
    created_at: str = Field(..., description="ISO-8601 creation timestamp")
    files: InvestigationFilesStatus = Field(default_factory=InvestigationFilesStatus, description="Uploaded file status breakdown")
    validation: Optional[InvestigationValidationResult] = Field(default=None, description="Current validation result")
    warnings: List[str] = Field(default_factory=list, description="Top-level warnings")
    errors: List[str] = Field(default_factory=list, description="Top-level error messages")


class InvestigationRunRequest(BaseModel):
    """Request payload to trigger execution of an investigation."""
    mode: Optional[InvestigationMode] = Field(default=None, description="Optional mode override")
    configuration: Dict[str, Any] = Field(default_factory=dict, description="Runtime execution parameters")
