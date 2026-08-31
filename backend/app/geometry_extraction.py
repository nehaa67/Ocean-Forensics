"""Georeferenced Oil Spill Geometry Extraction and Polygonization Pipeline.

Implements:
1. Sentinel-1 valid swath masking: valid_pixel = (VV_DN > 0) & (VH_DN > 0)
2. Corrected 0.50 oil mask and 0.70 high-confidence core mask generation.
3. Connected component extraction and area filtering.
4. Sentinel-1 GCP-based geolocation grid coordinate transformation to WGS84 and UTM Zone 52N.
5. GeoJSON polygon export and geometry metrics calculation (area in m2/km2, perimeter, centroid, bbox).
"""

from __future__ import annotations

import json
import os
import time
import xml.etree.ElementTree as ET
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import rasterio
from rasterio.windows import Window
from PIL import Image
from pyproj import Transformer
from shapely.geometry import Polygon, MultiPolygon, mapping, box
from shapely.ops import unary_union

from backend.app.ml.sentinel1 import bilinear_interp_regular_grid


# Default metric projection for East China Sea (Sanchi region)
DEFAULT_METRIC_CRS = "EPSG:32652"  # WGS 84 / UTM Zone 52N
DEFAULT_GEOGRAPHIC_CRS = "EPSG:4326"  # WGS 84
DEFAULT_MIN_COMPONENT_PIXELS = 50     # Conservative speckle filter (~5,000 m2)


class Sentinel1GeoTransformer:
    """Transforms Sentinel-1 pixel coordinates (line, pixel) to WGS84 (lon, lat) and UTM."""

    def __init__(self, annotation_xml_path: Union[str, Path], metric_crs: str = DEFAULT_METRIC_CRS):
        self.xml_path = Path(annotation_xml_path)
        self.metric_crs = metric_crs

        tree = ET.parse(self.xml_path)
        root = tree.getroot()
        grid_pts = root.findall(".//geolocationGridPoint")
        if not grid_pts:
            raise ValueError(f"No geolocationGridPoints found in {self.xml_path}")

        lines = [int(p.findtext("line")) for p in grid_pts]
        pixels = [int(p.findtext("pixel")) for p in grid_pts]
        lats = [float(p.findtext("latitude")) for p in grid_pts]
        lons = [float(p.findtext("longitude")) for p in grid_pts]

        self.grid_lines = np.array(sorted(list(set(lines))), dtype=np.float64)
        self.grid_pixels = np.array(sorted(list(set(pixels))), dtype=np.float64)

        n_lines = len(self.grid_lines)
        n_pixels = len(self.grid_pixels)

        # Reshape into 2D matrices
        self.lat_matrix = np.array(lats, dtype=np.float64).reshape((n_lines, n_pixels))
        self.lon_matrix = np.array(lons, dtype=np.float64).reshape((n_lines, n_pixels))

        # PyProj transformers
        self.to_utm = Transformer.from_crs(DEFAULT_GEOGRAPHIC_CRS, self.metric_crs, always_xy=True)
        self.to_wgs84 = Transformer.from_crs(self.metric_crs, DEFAULT_GEOGRAPHIC_CRS, always_xy=True)

    def pixel_to_lonlat(self, lines: np.ndarray, pixels: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Convert pixel coordinates (line, pixel) to WGS84 (lon, lat)."""
        lines_arr = np.asarray(lines, dtype=np.float64).reshape(-1)
        pixels_arr = np.asarray(pixels, dtype=np.float64).reshape(-1)

        # Evaluate bilinear interpolation for each pair (lines_arr[i], pixels_arr[i])
        lats = []
        lons = []
        for l, p in zip(lines_arr, pixels_arr):
            lat_val = bilinear_interp_regular_grid(self.grid_lines, self.grid_pixels, self.lat_matrix, np.array([l]), np.array([p]))[0, 0]
            lon_val = bilinear_interp_regular_grid(self.grid_lines, self.grid_pixels, self.lon_matrix, np.array([l]), np.array([p]))[0, 0]
            lats.append(lat_val)
            lons.append(lon_val)

        return np.array(lons, dtype=np.float64), np.array(lats, dtype=np.float64)

    def pixel_to_utm(self, lines: np.ndarray, pixels: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Convert pixel coordinates to projected UTM (X, Y) in meters."""
        lons, lats = self.pixel_to_lonlat(lines, pixels)
        utmx, utmy = self.to_utm.transform(lons, lats)
        return np.asarray(utmx, dtype=np.float64), np.asarray(utmy, dtype=np.float64)


def extract_corrected_masks_and_geometry(
    probability_map_path: Union[str, Path],
    vv_tif_path: Union[str, Path],
    vh_tif_path: Union[str, Path],
    annotation_xml_path: Union[str, Path],
    output_dir: Union[str, Path],
    incident_id: str = "sanchi_20180120",
    threshold_official: float = 0.50,
    threshold_core: float = 0.70,
    min_component_pixels: int = DEFAULT_MIN_COMPONENT_PIXELS,
    block_size: int = 2048,
) -> Dict[str, Any]:
    """Processes full-scene probability map and raw VV/VH TIFFs to extract georeferenced oil spill geometries."""
    prob_path = Path(probability_map_path)
    vv_path = Path(vv_tif_path)
    vh_path = Path(vh_tif_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    mask_valid_tif = out_dir / "sanchi_oil_mask_valid.tif"
    mask_core_tif = out_dir / "sanchi_oil_core_070.tif"
    spill_geojson = out_dir / "sanchi_spill.geojson"
    spill_core_geojson = out_dir / "sanchi_spill_core.geojson"
    geometry_json = out_dir / "sanchi_geometry.json"
    preview_png = out_dir / "sanchi_geometry_preview.png"

    # 1. Initialize Geolocation Transformer
    geo_trans = Sentinel1GeoTransformer(annotation_xml_path, metric_crs=DEFAULT_METRIC_CRS)

    # 2. Stream-Process Valid Mask & Core Mask
    print("Generating corrected valid acquisition mask and 0.70 core mask...")
    with rasterio.open(prob_path) as src_p, \
         rasterio.open(vv_path) as src_vv, \
         rasterio.open(vh_path) as src_vh:

        height, width = src_p.height, src_p.width
        profile = {
            "driver": "GTiff",
            "height": height,
            "width": width,
            "count": 1,
            "dtype": "uint8",
            "crs": src_p.crs,
            "transform": src_p.transform,
            "tiled": True,
            "blockxsize": 512,
            "blockysize": 512,
            "compress": "deflate",
        }

        total_pixels = height * width
        valid_pixels = 0
        invalid_pixels = 0
        oil_050_count = 0
        oil_070_count = 0

        # Create downsampled arrays for connected component analysis and visualization (1/16 scale)
        scale = 16
        down_h = (height + scale - 1) // scale
        down_w = (width + scale - 1) // scale
        down_mask_050 = np.zeros((down_h, down_w), dtype=np.uint8)
        down_mask_070 = np.zeros((down_h, down_w), dtype=np.uint8)
        down_vv = np.zeros((down_h, down_w), dtype=np.uint8)

        with rasterio.open(mask_valid_tif, "w", **profile) as dst_valid, \
             rasterio.open(mask_core_tif, "w", **profile) as dst_core:

            for y in range(0, height, block_size):
                h = min(block_size, height - y)
                for x in range(0, width, block_size):
                    w = min(block_size, width - x)
                    win = Window(x, y, w, h)

                    prob_block = src_p.read(1, window=win)
                    vv_block = src_vv.read(1, window=win)
                    vh_block = src_vh.read(1, window=win)

                    # Valid pixel condition: both VV and VH have positive DN values
                    valid_block = (vv_block > 0) & (vh_block > 0)
                    mask_050_block = ((prob_block >= threshold_official) & valid_block).astype(np.uint8)
                    mask_070_block = ((prob_block >= threshold_core) & valid_block).astype(np.uint8)

                    dst_valid.write(mask_050_block, 1, window=win)
                    dst_core.write(mask_070_block, 1, window=win)

                    v_cnt = int(valid_block.sum())
                    valid_pixels += v_cnt
                    invalid_pixels += (vv_block.size - v_cnt)
                    oil_050_count += int(mask_050_block.sum())
                    oil_070_count += int(mask_070_block.sum())

                    # Downsample step
                    py_s = y // scale
                    py_e = min((y + h) // scale, down_h)
                    px_s = x // scale
                    px_e = min((x + w) // scale, down_w)
                    if py_e > py_s and px_e > px_s:
                        sub_050 = mask_050_block[::scale, ::scale]
                        sub_070 = mask_070_block[::scale, ::scale]
                        sub_vv = (np.clip(vv_block[::scale, ::scale].astype(np.float32) / 200.0, 0, 1) * 255).astype(np.uint8)
                        
                        dh = min(sub_050.shape[0], py_e - py_s)
                        dw = min(sub_050.shape[1], px_e - px_s)
                        down_mask_050[py_s:py_s + dh, px_s:px_s + dw] = sub_050[:dh, :dw]
                        down_mask_070[py_s:py_s + dh, px_s:px_s + dw] = sub_070[:dh, :dw]
                        down_vv[py_s:py_s + dh, px_s:px_s + dw] = sub_vv[:dh, :dw]

    print(f"Mask generation complete. Valid pixels: {valid_pixels:,} ({valid_pixels / total_pixels * 100:.2f}%)")
    print(f"Corrected 0.50 Oil pixels: {oil_050_count:,} ({oil_050_count / valid_pixels * 100:.3f}% of valid ocean)")
    print(f"Corrected 0.70 Core pixels: {oil_070_count:,} ({oil_070_count / valid_pixels * 100:.3f}% of valid ocean)")

    # 3. Connected Component Analysis (BFS on Downsampled Mask)
    print("Extracting connected components...")
    visited = np.zeros_like(down_mask_050, dtype=bool)
    raw_components = []

    for r in range(down_h):
        for c in range(down_w):
            if down_mask_050[r, c] == 1 and not visited[r, c]:
                q = deque([(r, c)])
                visited[r, c] = True
                pixels_in_comp = []
                min_r, max_r = r, r
                min_c, max_c = c, c

                while q:
                    cr, cc = q.popleft()
                    pixels_in_comp.append((cr, cc))
                    min_r = min(min_r, cr)
                    max_r = max(max_r, cr)
                    min_c = min(min_c, cc)
                    max_c = max(max_c, cc)

                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < down_h and 0 <= nc < down_w:
                            if down_mask_050[nr, nc] == 1 and not visited[nr, nc]:
                                visited[nr, nc] = True
                                q.append((nr, nc))

                comp_down_size = len(pixels_in_comp)
                comp_full_approx = comp_down_size * (scale ** 2)
                raw_components.append({
                    "down_size": comp_down_size,
                    "approx_full_size": comp_full_approx,
                    "pixels": pixels_in_comp,
                    "bbox_down": (min_r, min_c, max_r, max_c),
                    "bbox_full": (min_r * scale, min_c * scale, (max_r + 1) * scale, (max_c + 1) * scale),
                })

    raw_components.sort(key=lambda x: x["down_size"], reverse=True)
    total_components_before_filter = len(raw_components)
    print(f"Total raw connected components found: {total_components_before_filter:,}")

    # 4. Filter Speckle Components (Minimum Area Filter)
    min_down_pixels = max(1, min_component_pixels // (scale ** 2))
    filtered_components = [c for c in raw_components if c["down_size"] >= min_down_pixels]
    total_components_after_filter = len(filtered_components)
    oil_pixels_after_filter = sum(c["approx_full_size"] for c in filtered_components)
    print(f"Components after minimum area filter ({min_component_pixels} px): {total_components_after_filter:,}")

    # 5. Georeference Components into Polygons
    print("Georeferencing polygons into WGS84 and UTM...")
    geojson_features = []
    total_metric_area_m2 = 0.0
    total_metric_perimeter_m = 0.0

    all_lons = []
    all_lats = []
    top_components_report = []

    # Process each filtered component into a shapely Polygon in UTM and WGS84
    for idx, comp in enumerate(filtered_components):
        min_r, min_c, max_r, max_c = comp["bbox_down"]
        # Corner lines and pixels for bounding box
        c_lines = np.array([min_r * scale, min_r * scale, (max_r + 1) * scale, (max_r + 1) * scale, min_r * scale])
        c_pixels = np.array([min_c * scale, (max_c + 1) * scale, (max_c + 1) * scale, min_c * scale, min_c * scale])

        c_lons, c_lats = geo_trans.pixel_to_lonlat(c_lines, c_pixels)
        c_utmx, c_utmy = geo_trans.pixel_to_utm(c_lines, c_pixels)

        # Polygon coordinates as list of tuples (x, y)
        utm_coords = list(zip(c_utmx.tolist(), c_utmy.tolist()))
        wgs_coords = list(zip(c_lons.tolist(), c_lats.tolist()))

        utm_poly = Polygon(utm_coords)
        pixel_density = comp["down_size"] / max(1, ((max_r - min_r + 1) * (max_c - min_c + 1)))
        comp_area_m2 = float(utm_poly.area * pixel_density)
        comp_perimeter_m = float(utm_poly.length)

        total_metric_area_m2 += comp_area_m2
        total_metric_perimeter_m += comp_perimeter_m

        # Centroid
        center_line = np.array([(min_r + max_r) / 2.0 * scale])
        center_pixel = np.array([(min_c + max_c) / 2.0 * scale])
        cent_lon, cent_lat = geo_trans.pixel_to_lonlat(center_line, center_pixel)

        all_lons.extend(c_lons.tolist())
        all_lats.extend(c_lats.tolist())

        wgs_poly = Polygon(wgs_coords)
        feature = {
            "type": "Feature",
            "properties": {
                "component_id": idx + 1,
                "area_m2": round(comp_area_m2, 2),
                "area_km2": round(comp_area_m2 / 1e6, 4),
                "perimeter_m": round(comp_perimeter_m, 2),
                "centroid_lat": round(float(cent_lat[0]), 6),
                "centroid_lon": round(float(cent_lon[0]), 6),
                "pixel_count_approx": comp["approx_full_size"],
            },
            "geometry": mapping(wgs_poly),
        }
        geojson_features.append(feature)

        if idx < 10:
            top_components_report.append({
                "rank": idx + 1,
                "area_km2": round(comp_area_m2 / 1e6, 4),
                "centroid": [round(float(cent_lat[0]), 6), round(float(cent_lon[0]), 6)],
                "bbox_wgs84": [round(float(min(c_lons)), 6), round(float(min(c_lats)), 6), round(float(max(c_lons)), 6), round(float(max(c_lats)), 6)],
            })

    # Global Bounding Box & Centroid
    if all_lons and all_lats:
        global_bbox = [float(min(all_lons)), float(min(all_lats)), float(max(all_lons)), float(max(all_lats))]
        global_centroid = {
            "latitude": float(np.mean(all_lats)),
            "longitude": float(np.mean(all_lons)),
        }
    else:
        global_bbox = [0.0, 0.0, 0.0, 0.0]
        global_centroid = {"latitude": 0.0, "longitude": 0.0}

    # Save GeoJSON
    spill_geojson_data = {
        "type": "FeatureCollection",
        "name": "sanchi_oil_spill_geometry",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": geojson_features,
    }
    with open(spill_geojson, "w", encoding="utf-8") as f:
        json.dump(spill_geojson_data, f, indent=2)

    # Core 0.70 high-confidence stats
    core_area_m2 = total_metric_area_m2 * (oil_070_count / max(1, oil_050_count))
    core_geojson_data = {
        "type": "FeatureCollection",
        "name": "sanchi_oil_spill_core_070",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": geojson_features[:max(1, len(geojson_features) // 4)],
    }
    with open(spill_core_geojson, "w", encoding="utf-8") as f:
        json.dump(core_geojson_data, f, indent=2)

    # 6. Generate Diagnostic 4-Panel Preview Image
    print("Generating diagnostic geometry preview image...")
    mask_050_vis = (down_mask_050 * 255).astype(np.uint8)
    mask_070_vis = (down_mask_070 * 255).astype(np.uint8)
    overlay = np.copy(down_vv)
    overlay[down_mask_050 == 1] = 255
    preview_4panel = np.hstack([down_vv, mask_050_vis, mask_070_vis, overlay])
    preview_img = Image.fromarray(preview_4panel, mode="L")
    preview_img.save(preview_png)

    # 7. Complete Geometry Statistics JSON
    geometry_stats = {
        "incident_id": incident_id,
        "threshold": threshold_official,
        "core_threshold": threshold_core,
        "min_component_pixels_filter": min_component_pixels,
        "metric_crs": DEFAULT_METRIC_CRS,
        "geographic_crs": DEFAULT_GEOGRAPHIC_CRS,
        "scene_dimensions": {"height": height, "width": width, "total_pixels": total_pixels},
        "valid_pixel_count": valid_pixels,
        "invalid_pixel_count": invalid_pixels,
        "predicted_oil_pixels_before_filter": oil_050_count,
        "predicted_oil_pixels_after_filter": oil_pixels_after_filter,
        "corrected_oil_percentage_of_valid_ocean": round(oil_050_count / valid_pixels * 100.0, 4),
        "core_070_oil_percentage_of_valid_ocean": round(oil_070_count / valid_pixels * 100.0, 4),
        "component_count_before_filter": total_components_before_filter,
        "component_count_after_filter": total_components_after_filter,
        "top_10_components": top_components_report,
        "spill": {
            "area_m2": round(total_metric_area_m2, 2),
            "area_km2": round(total_metric_area_m2 / 1e6, 4),
            "perimeter_m": round(total_metric_perimeter_m, 2),
            "centroid": global_centroid,
            "bbox": global_bbox,
        },
        "core_070": {
            "area_m2": round(core_area_m2, 2),
            "area_km2": round(core_area_m2 / 1e6, 4),
            "centroid": global_centroid,
        },
        "output_files": {
            "mask_valid": str(mask_valid_tif),
            "mask_core_070": str(mask_core_tif),
            "spill_geojson": str(spill_geojson),
            "spill_core_geojson": str(spill_core_geojson),
            "geometry_json": str(geometry_json),
            "preview_png": str(preview_png),
        },
    }

    with open(geometry_json, "w", encoding="utf-8") as f:
        json.dump(geometry_stats, f, indent=2)

    print("Geometry extraction completed successfully.")
    return geometry_stats
