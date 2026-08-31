from __future__ import annotations
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, Field


class DetectionResult(BaseModel):
    """Prototype detection result (backward compatibility)."""
    detected: bool = Field(
        description="Whether an oil-spill region was detected."
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Detection confidence between 0 and 1."
    )

    mask_id: str = Field(
        description="Identifier for the segmentation mask."
    )

    detection_mode: str = Field(
        description="Source of detection: prototype or model."
    )


class OilProbabilityMask(BaseModel):
    """Standardized output from oil-spill segmentation model."""
    mask_id: str = Field(..., description="Unique mask identifier")
    shape: Tuple[int, int] = Field(..., description="Raster dimensions (height, width)")
    probability_map: Optional[List[List[float]]] = Field(
        default=None, description="2D matrix of pixel oil probabilities [0.0, 1.0]"
    )
    binary_mask: Optional[List[List[int]]] = Field(
        default=None, description="2D binary mask matrix (0 = clean water, 1 = oil)"
    )
    threshold_applied: float = Field(default=0.5, ge=0.0, le=1.0, description="Probability threshold for binarization")
    model_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Estimated model certainty")
    model_version: str = Field(default="unet-resnet18-v1", description="Model architecture and version")
    preprocessing_version: str = Field(default="sar-standard-v1", description="Preprocessing recipe version")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Inference runtime lineage")
    quality_warnings: List[str] = Field(default_factory=list, description="Inference warnings")
