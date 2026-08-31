import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any

import rasterio
from rasterio import warp
from shapely.geometry import Point, mapping
import pyproj
from shapely.ops import transform


def _to_metric(point: Point, src_crs: rasterio.crs.CRS) -> Point:
    """Reproject a lon/lat point to EPSG:3857 metric CRS for distance calculations."""
    if src_crs.is_geographic:
        geom = mapping(point)
        reprojected = warp.transform_geom(src_crs, rasterio.crs.CRS.from_epsg(3857), geom)
        return Point(reprojected["coordinates"][0], reprojected["coordinates"][1])
    # If already metric, return unchanged
    return point


def _to_wgs84(geom: Any, src_crs: rasterio.crs.CRS) -> Any:
    """Reproject a metric geometry back to the source CRS (typically WGS84).

    If the source CRS is geographic (lon/lat), this converts from EPSG:3857
    metric coordinates to the source CRS. For projected CRS (e.g., EPSG:3857),
    the geometry is already in metric units and is returned unchanged.
    """
    if src_crs.is_geographic:
        # Transform from metric (EPSG:3857) to the source geographic CRS.
        geojson = mapping(geom)
        reprojected = warp.transform_geom(rasterio.crs.CRS.from_epsg(3857), src_crs, geojson)
        # Convert GeoJSON back to shapely geometry.
        if reprojected["type"] == "Point":
            return Point(reprojected["coordinates"][0], reprojected["coordinates"][1])
        from shapely.geometry import shape as shapely_shape
        return shapely_shape(reprojected)
    # For projected CRS, no transformation needed.
    return geom


def simulate_drift(
    start_point: Tuple[float, float],
    duration_hours: float,
    timestep_seconds: float,
    current: Tuple[float, float],
    wind: Tuple[float, float],
    windage: float = 0.03,
    direction: str = "forward",
    crs: rasterio.crs.CRS = rasterio.crs.CRS.from_epsg(4326),
) -> Dict[str, Any]:
    """Simulate a simple linear drift.

    Parameters
    ----------
    start_point: (lon, lat) tuple in the supplied CRS.
    duration_hours: total simulation time.
    timestep_seconds: interval between trajectory points.
    current: (vx, vy) current velocity in metres per second.
    wind: (vx, vy) wind velocity in metres per second.
    windage: fraction of wind speed that contributes to drift.
    direction: "forward" for forecast, "backward" for hindcast.
    crs: CRS of the input coordinates (default WGS84).

    Returns
    -------
    dict with trajectory, start/end points, direction and used parameters.
    """
    if direction not in {"forward", "backward"}:
        raise ValueError("direction must be 'forward' or 'backward'")

    # Effective velocity in metres per second
    vx = current[0] + wind[0] * windage
    vy = current[1] + wind[1] * windage
    if direction == "backward":
        vx, vy = -vx, -vy

    # Reproject start point to metric CRS for displacement calculations
    start_pt = Point(start_point[0], start_point[1])
    metric_start = _to_metric(start_pt, crs)

    num_steps = max(1, int(duration_hours * 3600 / timestep_seconds))
    trajectory: List[Dict[str, Any]] = []
    current_time = datetime.utcnow()
    for step in range(num_steps + 1):
        # linear displacement
        dx = vx * timestep_seconds * step
        dy = vy * timestep_seconds * step
        metric_pt = Point(metric_start.x + dx, metric_start.y + dy)
        # back to original CRS for output
        # Convert back to original CRS only if needed
        if crs.is_geographic:
            out_pt = _to_wgs84(metric_pt, crs)
        else:
            out_pt = metric_pt
        timestamp = current_time + timedelta(seconds=step * timestep_seconds)
        trajectory.append({
            "lon": out_pt.x,
            "lat": out_pt.y,
            "timestamp": timestamp.isoformat() + "Z",
        })

    result = {
        "direction": direction,
        "duration_hours": duration_hours,
        "timestep_seconds": timestep_seconds,
        "effective_velocity_m_s": {"vx": vx, "vy": vy},
        "start_point": {"lon": trajectory[0]["lon"], "lat": trajectory[0]["lat"]},
        "end_point": {"lon": trajectory[-1]["lon"], "lat": trajectory[-1]["lat"]},
        "trajectory": trajectory,
        "crs": crs.to_string(),
    }
    return result

__all__ = ["simulate_drift"]
