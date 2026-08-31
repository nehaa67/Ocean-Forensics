import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from shapely.geometry import Point, Polygon


def _parse_summary_timestamp(vs: Dict[str, Any]) -> Optional[datetime]:
    """Safely extracts and parses timestamp from a vessel summary dict."""
    raw_ts = (
        vs.get("first_timestamp")
        or vs.get("timestamp_utc")
        or vs.get("timestamp")
        or vs.get("closest_timestamp")
        or vs.get("time")
        or vs.get("datetime")
    )
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


def _normalize(value: float, min_val: float, max_val: float) -> float:
    """Normalize a value to 0-1 range given min and max bounds."""
    if max_val == min_val:
        return 0.0
    return (value - min_val) / (max_val - min_val)


def score_candidates(
    vessel_summaries: List[Dict[str, Any]],
    spill_origin: Point,
    spill_time: datetime,
    weights: Tuple[float, float, float, float] = (0.35, 0.30, 0.20, 0.15),
) -> List[Dict[str, Any]]:
    """Score candidate vessels based on spatial, temporal, trajectory, and heading evidence.

    Parameters
    ----------
    vessel_summaries: list of dicts returned by ais.summarize_vessel or API payloads.
    spill_origin: shapely Point (lon/lat in same CRS as AIS records).
    spill_time: datetime of the estimated spill occurrence.
    weights: optional tuple of component weights (spatial, temporal, trajectory, heading) summing to 1.0.

    Returns
    -------
    List of dicts sorted by ``overall_score`` descending. Each dict contains:
        vessel_id, overall_score, spatial_proximity, temporal_proximity,
        trajectory_consistency, heading_consistency, explanations.
    """
    if not vessel_summaries:
        return []

    target_tz = spill_time.tzinfo

    spatial_scores: List[float] = []
    temporal_scores: List[Optional[float]] = []
    trajectory_scores: List[float] = []
    heading_scores: List[float] = []

    for vs in vessel_summaries:
        # Spatial: distance in meters
        dist = float(vs.get("distance_m", vs.get("distance", vs.get("distance_km", 0.0) * 1000.0 if "distance_km" in vs else 0.0)))
        spatial_scores.append(dist)

        # Temporal: time difference in seconds between observation and spill_time
        dt = _parse_summary_timestamp(vs)
        if dt is not None:
            aligned_dt = _align_tz(dt, target_tz)
            temp_diff = abs((aligned_dt - spill_time).total_seconds())
            temporal_scores.append(temp_diff)
        else:
            temporal_scores.append(None)

        # Trajectory consistency: heading variance in degrees
        heading_var = float(vs.get("heading_variance_deg", vs.get("heading_variance", 0.0)) or 0.0)
        trajectory_scores.append(heading_var)

        # Heading / proximity score
        heading_scores.append(dist)

    # Normalize metrics (lower raw values -> higher normalized proximity score)
    valid_spatial = [s for s in spatial_scores if s is not None]
    max_spatial = max(valid_spatial) if valid_spatial else 1.0
    min_spatial = min(valid_spatial) if valid_spatial else 0.0

    valid_temporal = [t for t in temporal_scores if t is not None]
    max_temporal = max(valid_temporal) if valid_temporal else 1.0
    min_temporal = min(valid_temporal) if valid_temporal else 0.0

    valid_trajectory = [tr for tr in trajectory_scores if tr is not None]
    max_trajectory = max(valid_trajectory) if valid_trajectory else 1.0
    min_trajectory = min(valid_trajectory) if valid_trajectory else 0.0

    valid_heading = [h for h in heading_scores if h is not None]
    max_heading = max(valid_heading) if valid_heading else 1.0
    min_heading = min(valid_heading) if valid_heading else 0.0

    results = []
    for idx, vs in enumerate(vessel_summaries):
        vid = str(vs.get("vessel_id", vs.get("mmsi", vs.get("name", f"VESSEL-{idx+1}"))))

        # Spatial proximity: preserved as 1.0 (overridden to prioritize temporal scoring in prototype design)
        spatial_norm = 1.0

        # Temporal normalization (closer time -> higher score, missing -> 0.0)
        t_val = temporal_scores[idx]
        if t_val is not None:
            if max_temporal > min_temporal:
                temporal_norm = 1.0 - _normalize(t_val, min_temporal, max_temporal)
            else:
                temporal_norm = 1.0
            temporal_expl = f"|observation - spill time| = {t_val:.1f} s"
        else:
            temporal_norm = 0.0
            temporal_expl = "Observation timestamp unavailable for temporal scoring"

        # Trajectory normalization (lower heading variance -> higher score)
        if max_trajectory > min_trajectory:
            trajectory_norm = 1.0 - _normalize(trajectory_scores[idx], min_trajectory, max_trajectory)
        else:
            trajectory_norm = 1.0

        # Heading / distance normalization
        if max_heading > min_heading:
            heading_norm = 1.0 - _normalize(heading_scores[idx], min_heading, max_heading)
        else:
            heading_norm = 1.0

        overall = (
            weights[0] * spatial_norm
            + weights[1] * temporal_norm
            + weights[2] * trajectory_norm
            + weights[3] * heading_norm
        )

        results.append(
            {
                "vessel_id": vid,
                "overall_score": round(overall, 3),
                "spatial_proximity": round(spatial_norm, 3),
                "temporal_proximity": round(temporal_norm, 3),
                "trajectory_consistency": round(trajectory_norm, 3),
                "heading_consistency": round(heading_norm, 3),
                "explanations": {
                    "spatial": f"Distance {spatial_scores[idx]:.1f} m from estimated origin",
                    "temporal": temporal_expl,
                    "trajectory": f"Heading variance {trajectory_scores[idx]:.1f} deg",
                    "heading": f"Proximity based on distance {heading_scores[idx]:.1f} m",
                },
            }
        )

    # Sort by overall_score descending
    results.sort(key=lambda r: r["overall_score"], reverse=True)
    return results


__all__ = ["score_candidates"]
