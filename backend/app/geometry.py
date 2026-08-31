import numpy as np
from typing import Any, Dict, Tuple
import rasterio
from rasterio import features, warp
from rasterio.transform import Affine
from shapely.geometry import shape, Polygon, MultiPolygon, mapping
from shapely.ops import unary_union


def _mask_to_polygons(mask: np.ndarray, transform: Affine) -> MultiPolygon:
    """Convert a binary mask to a shapely MultiPolygon.

    Args:
        mask: 2‑D binary numpy array where 1 indicates oil.
        transform: Affine transform mapping pixel space to geographic coordinates.

    Returns:
        MultiPolygon containing all oil regions (may be empty)."""
    shapes = list(
        features.shapes(
            mask.astype(np.uint8),
            mask=mask.astype(bool),
            transform=transform,
        )
    )
    polygons = [shape(geom) for geom, value in shapes if value == 1]
    if not polygons:
        return MultiPolygon()
    merged = unary_union(polygons)
    if isinstance(merged, Polygon):
        merged = MultiPolygon([merged])
    return merged


def _reproject_geom(geom: MultiPolygon, src_crs: rasterio.crs.CRS, dst_crs: rasterio.crs.CRS) -> MultiPolygon:
    """Reproject a MultiPolygon from src_crs to dst_crs using rasterio.warp."""
    if src_crs == dst_crs:
        return geom
    geojson = mapping(geom)
    reprojected = warp.transform_geom(src_crs, dst_crs, geojson, precision=6)
    return shape(reprojected)


def calculate_geometry(mask: np.ndarray, transform: Affine, crs: rasterio.crs.CRS = rasterio.crs.CRS.from_epsg(3857)) -> Dict[str, Any]:
    """Calculate geometry and basic measurements from a binary oil mask.

    Returns a dict with keys:
        has_oil (bool), polygon (GeoJSON dict or None), area (float),
        centroid (Tuple[float,float]|None), bbox (Tuple[float,float,float,float]|None),
        perimeter (float), pixel_count (int).
    """
    if mask.ndim != 2:
        raise ValueError("Mask must be a 2‑D array")
    pixel_count = int(mask.sum())
    has_oil = pixel_count > 0
    if not has_oil:
        return {
            "has_oil": False,
            "polygon": None,
            "area": 0.0,
            "centroid": None,
            "bbox": None,
            "perimeter": 0.0,
            "pixel_count": 0,
        }
    multipolygon = _mask_to_polygons(mask, transform)
    if multipolygon.is_empty:
        return {
            "has_oil": False,
            "polygon": None,
            "area": 0.0,
            "centroid": None,
            "bbox": None,
            "perimeter": 0.0,
            "pixel_count": pixel_count,
        }
    # Determine metric CRS for area/perimeter calculations
    metric_crs = rasterio.crs.CRS.from_epsg(3857)
    if crs.is_geographic:
        # Reproject to metric CRS for metric measurements
        metric_geom = _reproject_geom(multipolygon, crs, metric_crs)
        area = metric_geom.area
        perimeter = metric_geom.length
    else:
        # Assume input CRS is already metric
        area = multipolygon.area
        perimeter = multipolygon.length
    centroid = (multipolygon.centroid.x, multipolygon.centroid.y)
    bbox = multipolygon.bounds
    return {
        "has_oil": True,
        "polygon": mapping(multipolygon),
        "area": area,
        "centroid": centroid,
        "bbox": bbox,
        "perimeter": perimeter,
        "pixel_count": pixel_count,
    }

__all__ = ["calculate_geometry"]
