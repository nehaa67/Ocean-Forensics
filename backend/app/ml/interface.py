from __future__ import annotations
from typing import Protocol, Any, Dict, Optional, Tuple, runtime_checkable
import numpy as np

from backend.app.schemas.detection import OilProbabilityMask


@runtime_checkable
class SegmentationModel(Protocol):
    """Abstract model-agnostic contract for oil-spill segmentation.
    
    Any ML implementation (e.g. U-Net ResNet-18, DeepLabV3, mock detector)
    must adhere to this interface without leaking framework internals.
    """

    @property
    def model_version(self) -> str:
        """Identifier and version of the model checkpoint."""
        ...

    @property
    def preprocessing_version(self) -> str:
        """Version of the preprocessing pipeline matching model training."""
        ...

    def predict(
        self,
        vv_raster: np.ndarray,
        vh_raster: np.ndarray,
        threshold: float = 0.5,
        **kwargs: Any,
    ) -> OilProbabilityMask:
        """Run segmentation inference on co-registered SAR polarizations.
        
        Args:
            vv_raster: 2D numpy array of VV polarization backscatter
            vh_raster: 2D numpy array of VH polarization backscatter
            threshold: Probability threshold for binary mask creation
            **kwargs: Optional runtime configurations (tile size, batch size, etc.)
            
        Returns:
            OilProbabilityMask containing probability map and binary mask.
        """
        ...
