"""Unit tests for georeferenced oil spill geometry extraction, masking, and calculations."""

import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from backend.app.geometry_extraction import (
    Sentinel1GeoTransformer,
    extract_corrected_masks_and_geometry,
)


@pytest.fixture
def mock_geometry_pipeline_fixture(tmp_path: Path):
    """Creates synthetic probability, VV, VH rasters and annotation XML for testing."""
    height, width = 300, 300
    transform = from_origin(125.0, 30.0, 0.001, 0.001)

    prob_tif = tmp_path / "mock_prob.tif"
    vv_tif = tmp_path / "mock_vv.tif"
    vh_tif = tmp_path / "mock_vh.tif"
    xml_path = tmp_path / "mock_annotation.xml"
    out_dir = tmp_path / "outputs" / "geometry"

    # Synthetic rasters:
    # Outer 50px border has DN=0 (invalid swath)
    # Inner region has valid ocean with an oil patch at center (y:100..150, x:100..150)
    vv_data = np.full((height, width), 100, dtype=np.uint16)
    vv_data[:50, :] = 0
    vv_data[-50:, :] = 0

    vh_data = np.full((height, width), 30, dtype=np.uint16)
    vh_data[:50, :] = 0
    vh_data[-50:, :] = 0

    prob_data = np.full((height, width), 0.2, dtype=np.float32)
    # Artificial high prob on DN=0 margin to test invalid masking
    prob_data[:50, :] = 0.95
    # Genuine oil patch in valid center:
    prob_data[100:150, 100:150] = 0.85

    for p, d, dtype in [(prob_tif, prob_data, "float32"), (vv_tif, vv_data, "uint16"), (vh_tif, vh_data, "uint16")]:
        with rasterio.open(
            p, "w", driver="GTiff", height=height, width=width, count=1, dtype=dtype, transform=transform
        ) as dst:
            dst.write(d, 1)

    # Synthetic Annotation XML with 4 GCP points
    root = ET.Element("product")
    grid = ET.SubElement(root, "geolocationGridPointList")
    for l, lat in [(0, 30.0), (300, 29.0)]:
        for pix, lon in [(0, 125.0), (300, 126.0)]:
            pt = ET.SubElement(grid, "geolocationGridPoint")
            ET.SubElement(pt, "line").text = str(l)
            ET.SubElement(pt, "pixel").text = str(pix)
            ET.SubElement(pt, "latitude").text = str(lat)
            ET.SubElement(pt, "longitude").text = str(lon)
    ET.ElementTree(root).write(xml_path)

    return prob_tif, vv_tif, vh_tif, xml_path, out_dir


def test_geo_transformer(mock_geometry_pipeline_fixture):
    """Test Sentinel-1 GCP grid bilinear transformation to WGS84 and UTM."""
    _, _, _, xml_path, _ = mock_geometry_pipeline_fixture
    transformer = Sentinel1GeoTransformer(xml_path)

    lons, lats = transformer.pixel_to_lonlat(np.array([150.0]), np.array([150.0]))
    assert pytest.approx(lons[0], 0.01) == 125.5
    assert pytest.approx(lats[0], 0.01) == 29.5

    utmx, utmy = transformer.pixel_to_utm(np.array([150.0]), np.array([150.0]))
    assert utmx[0] > 0
    assert utmy[0] > 0


def test_geometry_extraction_pipeline(mock_geometry_pipeline_fixture):
    """Test end-to-end geometry extraction, masking, filtering, and polygon generation."""
    prob_tif, vv_tif, vh_tif, xml_path, out_dir = mock_geometry_pipeline_fixture

    stats = extract_corrected_masks_and_geometry(
        probability_map_path=prob_tif,
        vv_tif_path=vv_tif,
        vh_tif_path=vh_tif,
        annotation_xml_path=xml_path,
        output_dir=out_dir,
        min_component_pixels=10,
        block_size=100,
    )

    assert stats["valid_pixel_count"] > 0
    assert stats["invalid_pixel_count"] > 0
    # Oil pixels in the invalid margin should be excluded from valid mask
    assert stats["predicted_oil_pixels_before_filter"] > 0
    assert stats["spill"]["area_m2"] > 0
    assert stats["spill"]["area_km2"] > 0
    assert stats["spill"]["perimeter_m"] > 0

    # Verify generated files
    assert (out_dir / "sanchi_oil_mask_valid.tif").is_file()
    assert (out_dir / "sanchi_oil_core_070.tif").is_file()
    assert (out_dir / "sanchi_spill.geojson").is_file()
    assert (out_dir / "sanchi_geometry.json").is_file()
    assert (out_dir / "sanchi_geometry_preview.png").is_file()

    with open(out_dir / "sanchi_spill.geojson") as f:
        geojson = json.load(f)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) > 0
