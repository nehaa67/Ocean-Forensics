"""Unit tests for PyTorch U-Net ResNet-18 frozen segmentation model."""

from pathlib import Path
import numpy as np
import pytest
import torch

from backend.app.ml import SegmentationModel, PyTorchSegmentationModel
from backend.app.schemas.detection import OilProbabilityMask

CHECKPOINT_PATH = Path("models/segmentation/best_unet_resnet18_sar_finetuned.pth")


@pytest.mark.skipif(not CHECKPOINT_PATH.is_file(), reason="Checkpoint file not found")
def test_pytorch_segmentation_model_loading():
    """Verify loading frozen checkpoint and protocol compliance."""
    model = PyTorchSegmentationModel(checkpoint_path=CHECKPOINT_PATH, device="cpu")
    assert isinstance(model, SegmentationModel)
    assert model.metadata.get("epoch") == 5
    assert not next(model.model.parameters()).requires_grad or not model.model.training


@pytest.mark.skipif(not CHECKPOINT_PATH.is_file(), reason="Checkpoint file not found")
def test_pytorch_single_tile_inference():
    """Verify single 512x512 tile inference produces valid logits, probabilities, and mask."""
    model = PyTorchSegmentationModel(checkpoint_path=CHECKPOINT_PATH, device="cpu")

    # Synthetic 2x512x512 tile in [0, 1]
    synthetic_tile = np.full((2, 512, 512), 0.5, dtype=np.float32)
    logits, probs, mask = model.predict_tile(synthetic_tile, threshold=0.5)

    assert logits.shape == (512, 512)
    assert logits.dtype == np.float32

    assert probs.shape == (512, 512)
    assert probs.dtype == np.float32
    assert 0.0 <= probs.min() <= probs.max() <= 1.0

    assert mask.shape == (512, 512)
    assert mask.dtype == np.uint8
    assert set(np.unique(mask)).issubset({0, 1})


@pytest.mark.skipif(not CHECKPOINT_PATH.is_file(), reason="Checkpoint file not found")
def test_pytorch_predict_protocol_method():
    """Verify predict method returns valid OilProbabilityMask."""
    model = PyTorchSegmentationModel(checkpoint_path=CHECKPOINT_PATH, device="cpu")
    vv = np.full((512, 512), 0.55, dtype=np.float32)
    vh = np.full((512, 512), 0.35, dtype=np.float32)

    result = model.predict(vv, vh, threshold=0.5)
    assert isinstance(result, OilProbabilityMask)
    assert result.shape == (512, 512)
    assert result.threshold_applied == 0.5
    assert len(result.probability_map) == 512
    assert len(result.probability_map[0]) == 512
