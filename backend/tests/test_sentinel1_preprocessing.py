"""Unit tests for Sentinel-1 radiometric calibration, normalization, and windowed reading."""

import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from backend.app.ml.sentinel1 import (
    Sentinel1Calibration,
    Sentinel1Reader,
    normalize_sigma0_db,
    bilinear_interp_regular_grid,
    SAR_MIN_DB,
    SAR_MAX_DB,
)


@pytest.fixture
def mock_safe_structure(tmp_path: Path):
    """Creates a minimal synthetic Sentinel-1 SAFE directory for unit testing."""
    safe_dir = tmp_path / "S1_SYNTHETIC.SAFE"
    meas_dir = safe_dir / "measurement"
    cal_dir = safe_dir / "annotation" / "calibration"
    meas_dir.mkdir(parents=True)
    cal_dir.mkdir(parents=True)

    height, width = 600, 700  # Non-multiple of 512 to test reflect padding
    transform = from_origin(125.0, 30.0, 0.0001, 0.0001)

    # 1. Create synthetic TIFF rasters (uint16)
    vv_tif = meas_dir / "s1_synthetic_vv.tiff"
    vh_tif = meas_dir / "s1_synthetic_vh.tiff"

    # Synthetic DN values: VV around 100, VH around 30, with some 0s and extreme values
    vv_data = np.full((height, width), 100, dtype=np.uint16)
    vv_data[0, 0] = 0        # Zero DN
    vv_data[1, 1] = 50000    # Extreme DN
    
    vh_data = np.full((height, width), 30, dtype=np.uint16)
    vh_data[0, 0] = 0

    for path, data in [(vv_tif, vv_data), (vh_tif, vh_data)]:
        with rasterio.open(
            path,
            "w",
            driver="GTiff",
            height=height,
            width=width,
            count=1,
            dtype="uint16",
            transform=transform,
        ) as dst:
            dst.write(data, 1)

    # 2. Create synthetic calibration XMLs
    # Grid: 3 lines (0, 300, 600) and 3 pixels (0, 350, 700)
    def create_cal_xml(filename: str, lut_val: float):
        root = ET.Element("calibration")
        vec_list = ET.SubElement(root, "calibrationVectorList")
        for line_val in [0, 300, 600]:
            vec = ET.SubElement(vec_list, "calibrationVector")
            ET.SubElement(vec, "line").text = str(line_val)
            ET.SubElement(vec, "pixel").text = "0 350 700"
            ET.SubElement(vec, "sigmaNought").text = f"{lut_val} {lut_val} {lut_val}"
        tree = ET.ElementTree(root)
        tree.write(cal_dir / filename)

    create_cal_xml("calibration-s1-vv.xml", 500.0)
    create_cal_xml("calibration-s1-vh.xml", 500.0)

    return safe_dir, vv_tif, vh_tif


def test_bilinear_interpolation():
    """Test 2D bilinear interpolation on regular grid."""
    gy = np.array([0.0, 100.0])
    gx = np.array([0.0, 100.0])
    gz = np.array([[10.0, 20.0], [30.0, 40.0]])

    ty = np.array([50.0])
    tx = np.array([50.0])

    res = bilinear_interp_regular_grid(gy, gx, gz, ty, tx)
    assert res.shape == (1, 1)
    # Center should be exactly 25.0
    assert pytest.approx(res[0, 0], 0.001) == 25.0


def test_dn_to_sigma0_and_db_conversion(tmp_path: Path):
    """Test radiometric calibration formula: sigma0 = DN^2 / A_sigma^2."""
    cal_file = tmp_path / "cal.xml"
    root = ET.Element("calibration")
    vec_list = ET.SubElement(root, "calibrationVectorList")
    for l in [0, 100]:
        v = ET.SubElement(vec_list, "calibrationVector")
        ET.SubElement(v, "line").text = str(l)
        ET.SubElement(v, "pixel").text = "0 100"
        ET.SubElement(v, "sigmaNought").text = "500.0 500.0"
    ET.ElementTree(root).write(cal_file)

    cal = Sentinel1Calibration(cal_file)
    dn = np.array([[50.0, 0.0]], dtype=np.float32)
    # With DN=50 and A_sigma=500 -> sigma0_linear = (50/500)^2 = 0.01 -> 10*log10(0.01) = -20.0 dB
    db = cal.dn_to_sigma0_db(dn, np.array([50.0]), np.array([25.0, 75.0]))

    assert pytest.approx(db[0, 0], 0.01) == -20.0
    # Zero DN should be mapped to SAR_MIN_DB (-50.0)
    assert db[0, 1] == SAR_MIN_DB


def test_normalization_and_clipping():
    """Test physical clipping to [-50, 5] dB and scaling to [0, 1]."""
    db_values = np.array([-60.0, -50.0, -22.5, 5.0, 10.0, np.nan], dtype=np.float32)
    normalized = normalize_sigma0_db(db_values)

    # -60 dB clipped to -50 -> 0.0
    assert normalized[0] == 0.0
    # -50 dB -> 0.0
    assert normalized[1] == 0.0
    # -22.5 dB -> (-22.5 + 50) / 55 = 27.5 / 55 = 0.5
    assert pytest.approx(normalized[2], 0.001) == 0.5
    # 5.0 dB -> 1.0
    assert pytest.approx(normalized[3], 0.001) == 1.0
    # 10.0 dB clipped to 5 -> 1.0
    assert pytest.approx(normalized[4], 0.001) == 1.0
    # NaN -> replaced with -50 -> 0.0
    assert normalized[5] == 0.0


def test_sentinel1_reader_window_and_channel_order(mock_safe_structure):
    """Test Sentinel1Reader reading window, channel order (VV=0, VH=1), and shapes."""
    safe_dir, _, _ = mock_safe_structure
    reader = Sentinel1Reader(safe_dir)

    assert reader.height == 600
    assert reader.width == 700

    # Read a 100x100 window
    window_data = reader.read_calibrated_window(col_off=50, row_off=50, width=100, height=100)
    assert window_data.shape == (2, 100, 100)
    assert window_data.dtype == np.float32
    assert 0.0 <= window_data.min() <= window_data.max() <= 1.0

    # Channel 0 (VV) should have higher intensity than Channel 1 (VH) since DN_VV=100 > DN_VH=30
    assert window_data[0].mean() > window_data[1].mean()


def test_generate_512_tiles_and_reflect_padding(mock_safe_structure):
    """Test 512x512 tile generation, boundary reflect padding, and crop metadata."""
    safe_dir, _, _ = mock_safe_structure
    reader = Sentinel1Reader(safe_dir)

    tiles = list(reader.generate_512_tiles(tile_size=512, stride=512))
    # 600 height / 512 stride -> 2 rows
    # 700 width / 512 stride -> 2 cols
    # Total tiles = 2 * 2 = 4
    assert len(tiles) == 4

    # Top-left tile: exactly 512x512 valid
    t0 = tiles[0]
    assert t0.tensor.shape == (2, 512, 512)
    assert t0.valid_height == 512
    assert t0.valid_width == 512
    assert t0.pad_h == 0
    assert t0.pad_w == 0

    # Bottom-right tile: height 600-512=88, width 700-512=188
    t_br = tiles[3]
    assert t_br.tensor.shape == (2, 512, 512)
    assert t_br.valid_height == 88
    assert t_br.valid_width == 188
    assert t_br.pad_h == 512 - 88
    assert t_br.pad_w == 512 - 188
    assert not np.isnan(t_br.tensor).any()
