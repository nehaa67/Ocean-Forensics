from __future__ import annotations
from typing import Dict, Any, Optional, Tuple, List
from pydantic import BaseModel, Field


class SpillGeometry(BaseModel):
    """Standardized georeferenced characterization of detected oil spill."""
    has_oil: bool = Field(..., description="True if any oil pixels are detected")
    polygon: Optional[Dict[str, Any]] = Field(
        default=None, description="GeoJSON Polygon or MultiPolygon representation"
    )
    area_m2: float = Field(default=0.0, description="Calculated spill surface area in square meters")
    centroid: Optional[Tuple[float, float]] = Field(default=None, description="Centroid coordinate (lon/x, lat/y)")
    bbox: Optional[Tuple[float, float, float, float]] = Field(
        default=None, description="Bounding box (min_x, min_y, max_x, max_y)"
    )
    perimeter_m: float = Field(default=0.0, description="Perimeter length in meters")
    pixel_count: int = Field(default=0, description="Number of oil positive pixels")
    crs_epsg: int = Field(default=4326, description="EPSG code of coordinate reference system")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Geometric calculation lineage")
    quality_warnings: List[str] = Field(default_factory=list, description="Topology or boundary warnings")
