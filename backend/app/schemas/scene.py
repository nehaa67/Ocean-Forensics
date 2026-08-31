from __future__ import annotations
from typing import Tuple, Dict, Any, List, Optional
from pydantic import BaseModel, Field


class SentinelScene(BaseModel):
    """Standardized representation of a Sentinel-1 SAR acquisition."""
    scene_id: str = Field(..., description="Unique product or scene identifier")
    acquisition_timestamp: str = Field(..., description="ISO-8601 acquisition timestamp in UTC")
    crs_epsg: int = Field(default=4326, description="EPSG code of coordinate reference system")
    transform: Tuple[float, float, float, float, float, float] = Field(
        ..., description="Affine transform (a, b, c, d, e, f) mapping pixel coordinates to CRS"
    )
    bbox: Tuple[float, float, float, float] = Field(
        ..., description="Bounding box (min_lon/min_x, min_lat/min_y, max_lon/max_x, max_lat/max_y)"
    )
    vv_path: Optional[str] = Field(default=None, description="Path or URI to VV polarization GeoTIFF/raster")
    vh_path: Optional[str] = Field(default=None, description="Path or URI to VH polarization GeoTIFF/raster")
    resolution_m: Tuple[float, float] = Field(
        default=(10.0, 10.0), description="Spatial pixel resolution in meters (x_res, y_res)"
    )
    source_metadata: Dict[str, Any] = Field(default_factory=dict, description="Satellite/instrument metadata")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Data acquisition and processing lineage")
    quality_warnings: List[str] = Field(default_factory=list, description="Data quality or coverage warnings")
