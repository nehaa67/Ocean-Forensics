"""Machine Learning interfaces and adapters for oil spill segmentation."""

from .interface import SegmentationModel
from .mock_segmentation import MockSegmentationModel
from .sentinel1 import (
    Sentinel1Reader,
    Sentinel1Calibration,
    normalize_sigma0_db,
    TileData,
    SAR_MIN_DB,
    SAR_MAX_DB,
    SAR_RANGE_DB,
)
from .unet_segmentation import PyTorchSegmentationModel
from .full_scene_inference import run_full_scene_inference

__all__ = [
    "SegmentationModel",
    "MockSegmentationModel",
    "PyTorchSegmentationModel",
    "Sentinel1Reader",
    "Sentinel1Calibration",
    "normalize_sigma0_db",
    "TileData",
    "SAR_MIN_DB",
    "SAR_MAX_DB",
    "SAR_RANGE_DB",
    "run_full_scene_inference",
]
