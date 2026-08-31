import numpy as np
from rasterio.transform import Affine
from backend.app.geometry import calculate_geometry


def test_geometry_with_oil_region():
    # 2x2 mask with a single oil pixel at top-left (row 0, col 0)
    mask = np.array(
        [[1, 0],
         [0, 0]],
        dtype=np.uint8,
    )
    # Affine: pixel width=10, height=-10 (north-up), origin at (100, 200)
    transform = Affine(10, 0, 100, 0, -10, 200)
    result = calculate_geometry(mask, transform)
    assert result["has_oil"] is True
    # area should be 10*10 = 100
    assert result["area"] == 100.0
    # centroid should be at centre of the 10x10 square
    assert result["centroid"] == (105.0, 195.0)
    # bounding box: (minx, miny, maxx, maxy)
    assert result["bbox"] == (100.0, 190.0, 110.0, 200.0)
    # perimeter of a 10x10 square = 40
    assert result["perimeter"] == 40.0
    assert result["polygon"] is not None


def test_geometry_empty_mask():
    mask = np.zeros((2, 2), dtype=np.uint8)
    transform = Affine(10, 0, 0, 0, -10, 0)
    result = calculate_geometry(mask, transform)
    assert result["has_oil"] is False
    assert result["area"] == 0.0
    assert result["centroid"] is None
    assert result["bbox"] is None
    assert result["perimeter"] == 0.0
    assert result["polygon"] is None
