from __future__ import annotations
from typing import Any, Optional
import numpy as np

from backend.app.schemas.detection import OilProbabilityMask
from backend.app.ml.interface import SegmentationModel


class MockSegmentationModel:
    """Deterministic mock segmentation model for testing and prototype pipelines."""

    def __init__(
        self,
        model_version: str = "mock-unet-v0.1",
        preprocessing_version: str = "synthetic-v1",
        fixed_confidence: float = 1.0,
    ) -> None:
        self._model_version = model_version
        self._preprocessing_version = preprocessing_version
        self.fixed_confidence = fixed_confidence

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def preprocessing_version(self) -> str:
        return self._preprocessing_version

    def predict(
        self,
        vv_raster: np.ndarray,
        vh_raster: np.ndarray,
        threshold: float = 0.5,
        mask_id: str = "mock_prediction",
        **kwargs: Any,
    ) -> OilProbabilityMask:
        """Generate a deterministic synthetic probability mask matching input raster dimensions."""
        if vv_raster.ndim != 2:
            raise ValueError(f"Expected 2D VV raster, got shape {vv_raster.shape}")

        height, width = vv_raster.shape
        # Create deterministic pseudo probability map:
        # If input has values > 0 at center, create oil region
        prob_map = np.zeros((height, width), dtype=np.float32)
        if height >= 2 and width >= 2:
            prob_map[0, 0] = 0.95  # Deterministic test oil pixel

        binary_mask = (prob_map >= threshold).astype(np.uint8)

        return OilProbabilityMask(
            mask_id=mask_id,
            shape=(height, width),
            probability_map=prob_map.tolist(),
            binary_mask=binary_mask.tolist(),
            threshold_applied=threshold,
            model_confidence=self.fixed_confidence,
            model_version=self.model_version,
            preprocessing_version=self.preprocessing_version,
            provenance={
                "engine": "MockSegmentationModel",
                "vv_shape": list(vv_raster.shape),
                "vh_shape": list(vh_raster.shape),
            },
            quality_warnings=[],
        )
