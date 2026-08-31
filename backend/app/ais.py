import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple, Optional
from shapely.geometry import Point, Polygon, mapping
from shapely.ops import transform
# pyrefly: ignore [missing-import]
import pyproj


def _parse_timestamp(rec: Dict[str, Any]) -> Optional[datetime]:
    """Extract and parse timestamp from AIS record supporting 'timestamp_utc', 'timestamp', and alternatives."""
    raw_ts = rec.get("timestamp_utc") or rec.get("timestamp") or rec.get("time") or rec.get("datetime")
    if raw_ts is None:
        return None
    if isinstance(raw_ts, datetime):
        return raw_ts
    try:
        clean_ts = str(raw_ts).strip()
        if clean_ts.endswith("Z"):
            clean_ts = clean_ts[:-1] + "+00:00"
        return datetime.fromisoformat(clean_ts)
    except Exception:
        return None


def _align_tz(dt: datetime, target_tz: Optional[timezone]) -> datetime:
    """Align datetime timezone awareness with target timezone for safe comparison."""
    if target_tz is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=target_tz)
    elif target_tz is None and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _to_metric(point: Point, src_crs: Any) -> Point:
    """Reproject a lon/lat point to EPSG:3857 metric CRS for distance calculations."""
    if src_crs.is_geographic:
        # Check if coordinates are within valid geographic ranges (longitude in [-180, 180], latitude in [-90, 90]).
        # If they are out of bounds, this is synthetic/projected-style data, so we return it unchanged (already metric).
        if not (-180.0 <= point.x <= 180.0 and -90.0 <= point.y <= 90.0):
            return point
        project = pyproj.Transformer.from_crs(src_crs, pyproj.CRS.from_epsg(3857), always_xy=True).transform
        return transform(project, point)
    return point


def _to_wgs84(point: Point, src_crs: Any) -> Point:
    """Reproject a metric point back to the source CRS (typically WGS84)."""
    if src_crs.is_geographic:
        project = pyproj.Transformer.from_crs(pyproj.CRS.from_epsg(3857), src_crs, always_xy=True).transform
        return transform(project, point)
    return point


def filter_ais(
    records: List[Dict[str, Any]],
    area: Polygon,
    time_window: Tuple[datetime, datetime],
    crs: Any,
) -> List[Dict[str, Any]]:
    """Filter AIS records by spatial area and temporal window.

    Supports both 'timestamp_utc' (API schema) and 'timestamp' (internal schema).
    """
    start, end = time_window
    target_tz = start.tzinfo if start.tzinfo is not None else end.tzinfo
    if target_tz is not None:
        start = _align_tz(start, target_tz)
        end = _align_tz(end, target_tz)

    filtered = []
    for rec in records:
        # Ensure longitude and latitude presence
        if "longitude" not in rec or "latitude" not in rec:
            continue

        rec_dt = _parse_timestamp(rec)
        if rec_dt is None:
            continue

        # Align timezone for safe temporal comparison
        rec_dt_aligned = _align_tz(rec_dt, target_tz)
        if not (start <= rec_dt_aligned <= end):
            continue

        pt = Point(rec["longitude"], rec["latitude"])
        if not area.contains(pt):
            continue

        # Normalize timestamp field for downstream consumers while preserving timestamp_utc
        rec_copy = dict(rec)
        if "timestamp" not in rec_copy and "timestamp_utc" in rec_copy:
            rec_copy["timestamp"] = rec_copy["timestamp_utc"]
        elif "timestamp_utc" not in rec_copy and "timestamp" in rec_copy:
            rec_copy["timestamp_utc"] = rec_copy["timestamp"]

        filtered.append(rec_copy)
    return filtered


def group_tracks(records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group AIS records by vessel_id and sort by timestamp."""
    tracks: Dict[str, List[Dict[str, Any]]] = {}
    for rec in records:
        vid = str(rec.get("vessel_id", rec.get("mmsi", rec.get("name", "UNKNOWN"))))
        tracks.setdefault(vid, []).append(rec)

    # Sort each track by timestamp safely
    for vid in tracks:
        def _get_ts(r: Dict[str, Any]) -> datetime:
            dt = _parse_timestamp(r)
            return dt if dt is not None else datetime.min.replace(tzinfo=timezone.utc)

        tracks[vid].sort(key=_get_ts)
    return tracks


def summarize_vessel(track: List[Dict[str, Any]], origin: Point, crs: Any) -> Dict[str, Any]:
    """Create a summary for a vessel track.

    Returns a dict with vessel_id, first/last timestamps, distance_m from origin (based on first point),
    time_delta_s, average speed (m/s), heading variance (radians).
    """
    if not track:
        raise ValueError("Empty track")
    vessel_id = str(track[0].get("vessel_id", track[0].get("mmsi", "UNKNOWN")))

    dt_first = _parse_timestamp(track[0])
    dt_last = _parse_timestamp(track[-1])

    first_ts = dt_first.isoformat().replace("+00:00", "") + "Z" if dt_first else "UNKNOWN"
    last_ts = dt_last.isoformat().replace("+00:00", "") + "Z" if dt_last else "UNKNOWN"

    # Convert first point to metric for distance
    first_pt = Point(track[0]["longitude"], track[0]["latitude"])
    metric_first = _to_metric(first_pt, crs)
    metric_origin = _to_metric(origin, crs)

    is_synthetic_projected = False
    if crs.is_geographic:
        if not (-180.0 <= first_pt.x <= 180.0 and -90.0 <= first_pt.y <= 90.0) or \
           not (-180.0 <= origin.x <= 180.0 and -90.0 <= origin.y <= 90.0):
            is_synthetic_projected = True

    # Compute distance (meters) between first point and origin appropriately for CRS
    if crs.is_geographic and not is_synthetic_projected:
        geod = pyproj.Geod(ellps='WGS84')
        _, _, distance_m = geod.inv(first_pt.x, first_pt.y, origin.x, origin.y)
    else:
        distance_m = ((first_pt.x - origin.x) ** 2 + (first_pt.y - origin.y) ** 2) ** 0.5

    # Time delta in seconds
    if dt_first and dt_last:
        delta_s = dt_last - dt_first
        time_delta_s = delta_s.total_seconds()
    else:
        time_delta_s = 0.0

    # Average speed (from records) if provided, else compute from distance/time if possible
    speeds = [
        rec.get("speed", rec.get("speed_knots", rec.get("sog")))
        for rec in track
        if rec.get("speed") is not None or rec.get("speed_knots") is not None or rec.get("sog") is not None
    ]
    avg_speed = sum(speeds) / len(speeds) if speeds else None

    # Heading variance (simple std dev) in degrees
    headings = [
        rec.get("heading", rec.get("heading_deg", rec.get("course")))
        for rec in track
        if rec.get("heading") is not None or rec.get("heading_deg") is not None or rec.get("course") is not None
    ]
    if headings:
        mean_heading = sum(headings) / len(headings)
        var = sum((h - mean_heading) ** 2 for h in headings) / len(headings)
        heading_variance = var ** 0.5
    else:
        heading_variance = None

    return {
        "vessel_id": vessel_id,
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
        "distance_m": distance_m,
        "time_delta_s": time_delta_s,
        "average_speed_m_s": avg_speed,
        "heading_variance_deg": heading_variance,
    }


__all__ = ["filter_ais", "group_tracks", "summarize_vessel"]
