import numpy as np

from backend.app.ml.interface import SegmentationModel
from backend.app.ml.mock_segmentation import MockSegmentationModel
from backend.app.schemas.detection import OilProbabilityMask


def test_segmentation_protocol_compliance():
    model = MockSegmentationModel(model_version="test-unet-v1", preprocessing_version="test-prep-v1")
    assert isinstance(model, SegmentationModel)
    assert model.model_version == "test-unet-v1"
    assert model.preprocessing_version == "test-prep-v1"


def test_mock_segmentation_prediction_contract():
    model = MockSegmentationModel()
    vv_tile = np.ones((512, 512), dtype=np.float32)
    vh_tile = np.ones((512, 512), dtype=np.float32)

    result = model.predict(vv_tile, vh_tile, threshold=0.5, mask_id="sanchi_test_mask")

    assert isinstance(result, OilProbabilityMask)
    assert result.mask_id == "sanchi_test_mask"
    assert result.shape == (512, 512)
    assert result.threshold_applied == 0.5
    assert result.model_confidence == 1.0
    assert result.probability_map is not None
    assert result.binary_mask is not None
    assert len(result.binary_mask) == 512
    assert len(result.binary_mask[0]) == 512
