"""Historical AIS Filtering and Vessel Attribution Pipeline.

Implements:
1. Historical AIS CSV ingestion, cleaning, and trajectory reconstruction.
2. Geodesic spatial and temporal correlation with the backward drift source zone and trajectory.
3. Multi-factor attribution scoring with deterministic evidence generation.
4. GeoJSON and metadata export for forensic analysis.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
import pyproj
from pyproj import Geod
from shapely.geometry import Point, LineString, Polygon, mapping

from backend.app.geometry_extraction import DEFAULT_METRIC_CRS, DEFAULT_GEOGRAPHIC_CRS


# Default Attribution Weights
DEFAULT_WEIGHTS = {
    "spatial": 0.35,
    "temporal": 0.30,
    "trajectory": 0.20,
    "heading": 0.15,
}


def parse_iso_datetime(dt_str: Any) -> datetime:
    """Parses standard ISO or SQL datetime strings into UTC datetime."""
    s = str(dt_str).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        dt = pd.to_datetime(s, utc=True).to_pydatetime()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def run_ais_attribution(
    ais_csv_path: Union[str, Path],
    drift_json_path: Union[str, Path],
    output_dir: Union[str, Path],
    incident_id: str = "sanchi_20180120",
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Correlates historical AIS tracks with estimated source zone and scores candidates."""
    csv_path = Path(ais_csv_path)
    drift_path = Path(drift_json_path)
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if weights is None:
        weights = DEFAULT_WEIGHTS

    candidates_geojson_path = out_dir / "sanchi_ais_candidates.geojson"
    tracks_geojson_path = out_dir / "sanchi_vessel_tracks.geojson"
    attribution_json_path = out_dir / "sanchi_attribution.json"
    preview_png_path = out_dir / "sanchi_ais_preview.png"

    # 1. Load Drift Results & Estimated Source Zone
    with open(drift_path, "r", encoding="utf-8") as f:
        drift_data = json.load(f)

    source_info = drift_data.get("source_estimate", {})
    src_lat = float(source_info.get("latitude", 0.0))
    src_lon = float(source_info.get("longitude", 0.0))
    src_target_time = parse_iso_datetime(source_info.get("target_time", "2018-01-14T09:28:53Z"))
    src_radius_km = float(source_info.get("uncertainty_radius_km", 48.2))
    src_radius_m = src_radius_km * 1000.0

    traj_points = drift_data.get("trajectory", [])
    traj_coords = [(p["longitude"], p["latitude"]) for p in traj_points]
    drift_linestring = LineString(traj_coords) if len(traj_coords) >= 2 else None

    # 2. Read and Parse AIS CSV
    if not csv_path.is_file():
        raise FileNotFoundError(f"AIS CSV not found: {csv_path}")

    df_ais = pd.read_csv(csv_path)
    total_raw_records = len(df_ais)

    # Standardize Column Names
    col_map = {}
    for col in df_ais.columns:
        c_low = col.lower().strip()
        if "time" in c_low or "date" in c_low:
            col_map[col] = "timestamp"
        elif "vessel" in c_low or "name" in c_low:
            col_map[col] = "vessel_name"
        elif "mmsi" in c_low:
            col_map[col] = "mmsi"
        elif "lat" in c_low:
            col_map[col] = "latitude"
        elif "lon" in c_low:
            col_map[col] = "longitude"
        elif "sog" in c_low or "speed" in c_low:
            col_map[col] = "speed"
        elif "cog" in c_low or "course" in c_low:
            col_map[col] = "cog"
        elif "heading" in c_low:
            col_map[col] = "heading"

    df_clean = df_ais.rename(columns=col_map)
    required = ["timestamp", "latitude", "longitude"]
    for r in required:
        if r not in df_clean.columns:
            raise ValueError(f"Missing required column '{r}' in AIS dataset: {csv_path}")

    # Fill default identifiers if missing
    if "vessel_name" not in df_clean.columns:
        df_clean["vessel_name"] = "UNKNOWN_VESSEL"
    if "mmsi" not in df_clean.columns:
        df_clean["mmsi"] = None

    parsed_dt_list = []
    # Group by vessel identifier (vessel_name or MMSI)
    vessel_groups: Dict[str, List[Dict[str, Any]]] = {}
    for _, row in df_clean.iterrows():
        v_name = str(row.get("vessel_name", "UNKNOWN")).strip()
        mmsi_val = row.get("mmsi")
        mmsi_str = str(int(mmsi_val)) if pd.notna(mmsi_val) and isinstance(mmsi_val, (int, float)) else str(mmsi_val)
        
        v_key = v_name if v_name and v_name != "nan" else (f"MMSI_{mmsi_str}" if mmsi_str != "nan" else "UNKNOWN")

        dt_val = parse_iso_datetime(row["timestamp"])
        parsed_dt_list.append(dt_val)

        rec = {
            "vessel_name": v_name if v_name != "nan" else "UNKNOWN",
            "mmsi": mmsi_str if mmsi_str != "nan" else None,
            "timestamp": dt_val,
            "timestamp_iso": dt_val.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"]),
            "speed_knots": float(row["speed"]) if "speed" in row and pd.notna(row["speed"]) else None,
            "cog_deg": float(row["cog"]) if "cog" in row and pd.notna(row["cog"]) else None,
            "heading_deg": float(row["heading"]) if "heading" in row and pd.notna(row["heading"]) else None,
        }
        vessel_groups.setdefault(v_key, []).append(rec)

    # 3. Geodesic & Spatial Correlation
    geod = Geod(ellps="WGS84")
    candidate_analyses = []
    track_features = []
    point_features = []

    for v_key, records in vessel_groups.items():
        records.sort(key=lambda r: r["timestamp"])
        v_name = records[0]["vessel_name"]
        mmsi = records[0]["mmsi"]

        first_ts = records[0]["timestamp"]
        last_ts = records[-1]["timestamp"]
        obs_count = len(records)

        # Distances to source centroid
        dists_to_source_m = []
        dists_to_drift_track_m = []
        for r in records:
            _, _, d_m = geod.inv(r["longitude"], r["latitude"], src_lon, src_lat)
            dists_to_source_m.append(d_m)

            if traj_coords:
                min_wp_d = min(geod.inv(r["longitude"], r["latitude"], wp[0], wp[1])[2] for wp in traj_coords)
                dists_to_drift_track_m.append(min_wp_d)
            else:
                dists_to_drift_track_m.append(d_m)

        min_dist_src_m = min(dists_to_source_m)
        min_dist_src_km = min_dist_src_m / 1000.0
        closest_idx = int(np.argmin(dists_to_source_m))
        closest_rec = records[closest_idx]

        min_dist_traj_m = min(dists_to_drift_track_m) if dists_to_drift_track_m else min_dist_src_m
        min_dist_traj_km = min_dist_traj_m / 1000.0

        # Source Zone Intersection: point falls inside the uncertainty buffer
        inside_source_zone_count = sum(1 for d in dists_to_source_m if d <= src_radius_m)
        intersects_source_zone = inside_source_zone_count > 0

        # Temporal delta to estimated source time
        dt_seconds = abs((closest_rec["timestamp"] - src_target_time).total_seconds())
        dt_days = dt_seconds / 86400.0

        # Speeds and Headings
        speeds = [r["speed_knots"] for r in records if r["speed_knots"] is not None]
        avg_speed_knots = float(np.mean(speeds)) if speeds else None

        headings = [r["heading_deg"] for r in records if r["heading_deg"] is not None]
        heading_std = float(np.std(headings)) if len(headings) >= 2 else (0.0 if headings else None)

        # Trajectory Geometry
        v_coords = [(r["longitude"], r["latitude"]) for r in records]
        if len(v_coords) >= 2:
            v_geom = LineString(v_coords)
            track_features.append({
                "type": "Feature",
                "properties": {
                    "vessel_name": v_name,
                    "mmsi": mmsi,
                    "observation_count": obs_count,
                    "first_timestamp": first_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "last_timestamp": last_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "closest_distance_km": round(min_dist_src_km, 2),
                },
                "geometry": mapping(v_geom),
            })

        # Closest Point Feature
        point_features.append({
            "type": "Feature",
            "properties": {
                "vessel_name": v_name,
                "mmsi": mmsi,
                "closest_timestamp": closest_rec["timestamp_iso"],
                "distance_to_source_km": round(min_dist_src_km, 2),
                "distance_to_trajectory_km": round(min_dist_traj_km, 2),
                "speed_knots": closest_rec["speed_knots"],
                "heading_deg": closest_rec["heading_deg"],
            },
            "geometry": mapping(Point(closest_rec["longitude"], closest_rec["latitude"])),
        })

        candidate_analyses.append({
            "vessel_name": v_name,
            "mmsi": mmsi,
            "record_count": obs_count,
            "first_timestamp": first_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_timestamp": last_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "closest_timestamp": closest_rec["timestamp_iso"],
            "closest_latitude": closest_rec["latitude"],
            "closest_longitude": closest_rec["longitude"],
            "closest_distance_to_source_km": round(min_dist_src_km, 2),
            "closest_distance_to_trajectory_km": round(min_dist_traj_km, 2),
            "inside_source_zone": intersects_source_zone,
            "source_zone_intersection_count": inside_source_zone_count,
            "temporal_difference_to_source_days": round(dt_days, 2),
            "temporal_difference_seconds": dt_seconds,
            "average_speed_knots": round(avg_speed_knots, 2) if avg_speed_knots is not None else None,
            "heading_variance_deg": round(heading_std, 2) if heading_std is not None else None,
        })

    # 4. Multi-Factor Attribution Scoring
    scored_candidates = []
    for cand in candidate_analyses:
        # Spatial score: decays with distance from source centroid
        spatial_score = math.exp(-cand["closest_distance_to_source_km"] / max(10.0, src_radius_km * 2.0))
        
        # Temporal score: decays with difference from source time
        temporal_score = math.exp(-cand["temporal_difference_to_source_days"] / 10.0)

        # Trajectory proximity score
        traj_score = math.exp(-cand["closest_distance_to_trajectory_km"] / max(10.0, src_radius_km * 2.0))

        # Heading score
        if cand["heading_variance_deg"] is not None:
            heading_score = math.exp(-cand["heading_variance_deg"] / 30.0)
        else:
            heading_score = 0.5

        # Overall composite score
        overall_score = (
            weights["spatial"] * spatial_score
            + weights["temporal"] * temporal_score
            + weights["trajectory"] * traj_score
            + weights["heading"] * heading_score
        )

        # Generate deterministic evidence explanations
        evidence_lines = []
        if cand["inside_source_zone"]:
            evidence_lines.append(f"Vessel AIS observations intersect the estimated source zone ({cand['source_zone_intersection_count']} records within {src_radius_km:.1f} km).")
        else:
            evidence_lines.append(f"Closest approach is {cand['closest_distance_to_source_km']:.1f} km from the estimated source centroid.")

        evidence_lines.append(f"Closest temporal approach occurred at {cand['closest_timestamp']} (delta: {cand['temporal_difference_to_source_days']:.1f} days from hindcast epoch).")
        evidence_lines.append(f"Minimum distance to reconstructed backward drift trajectory is {cand['closest_distance_to_trajectory_km']:.1f} km.")

        if cand["record_count"] >= 2:
            evidence_lines.append(f"Reconstructed track contains {cand['record_count']} AIS points with mean speed {cand['average_speed_knots']} knots.")
        else:
            evidence_lines.append(f"Single isolated AIS transmission recorded ({cand['record_count']} observation).")

        cand_output = {
            "vessel_name": cand["vessel_name"],
            "mmsi": cand["mmsi"],
            "score": round(overall_score, 4),
            "spatial_score": round(spatial_score, 4),
            "temporal_score": round(temporal_score, 4),
            "trajectory_score": round(traj_score, 4),
            "heading_score": round(heading_score, 4),
            "closest_distance_km": cand["closest_distance_to_source_km"],
            "closest_distance_to_trajectory_km": cand["closest_distance_to_trajectory_km"],
            "closest_timestamp": cand["closest_timestamp"],
            "inside_source_zone": cand["inside_source_zone"],
            "record_count": cand["record_count"],
            "evidence": evidence_lines,
        }
        scored_candidates.append(cand_output)

    # Sort descending by attribution score
    scored_candidates.sort(key=lambda c: c["score"], reverse=True)
    for rank_idx, c in enumerate(scored_candidates, 1):
        c["rank"] = rank_idx

    # 5. Export GeoJSON Files
    candidates_geojson_data = {
        "type": "FeatureCollection",
        "name": "sanchi_ais_candidate_points",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": point_features,
    }
    with open(candidates_geojson_path, "w", encoding="utf-8") as f:
        json.dump(candidates_geojson_data, f, indent=2)

    tracks_geojson_data = {
        "type": "FeatureCollection",
        "name": "sanchi_ais_vessel_tracks",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
        "features": track_features,
    }
    with open(tracks_geojson_path, "w", encoding="utf-8") as f:
        json.dump(tracks_geojson_data, f, indent=2)

    # 6. Generate Diagnostic Map Preview
    print("Generating AIS diagnostic preview map...")
    img_w, img_h = 800, 600
    img = Image.new("RGB", (img_w, img_h), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)

    # Determine bounding extent
    all_lons = [src_lon] + [p["longitude"] for p in traj_points] + [float(r["longitude"]) for r in df_clean.to_dict("records")]
    all_lats = [src_lat] + [p["latitude"] for p in traj_points] + [float(r["latitude"]) for r in df_clean.to_dict("records")]
    min_lo, max_lo = min(all_lons) - 0.5, max(all_lons) + 0.5
    min_la, max_la = min(all_lats) - 0.5, max(all_lats) + 0.5

    def to_px(lon, lat):
        px = int((lon - min_lo) / max(1e-6, max_lo - min_lo) * (img_w - 80) + 40)
        py = int((max_la - lat) / max(1e-6, max_la - min_la) * (img_h - 80) + 40)
        return px, py

    # Draw Source Zone Circle
    src_px = to_px(src_lon, src_lat)
    r_px = int(src_radius_km / max(1e-6, (max_lo - min_lo) * 111.0) * (img_w - 80))
    draw.ellipse([src_px[0] - r_px, src_px[1] - r_px, src_px[0] + r_px, src_px[1] + r_px], fill=(255, 220, 220), outline=(220, 50, 50))

    # Draw Drift Trajectory Line
    if traj_coords:
        traj_px = [to_px(lo, la) for lo, la in traj_coords]
        draw.line(traj_px, fill=(30, 100, 200), width=2)

    # Draw AIS Vessel Tracks & Points
    colors = [(200, 30, 30), (30, 150, 30), (150, 30, 180), (200, 120, 0)]
    for idx, (v_key, records) in enumerate(vessel_groups.items()):
        col = colors[idx % len(colors)]
        pts_px = [to_px(r["longitude"], r["latitude"]) for r in records]
        if len(pts_px) >= 2:
            draw.line(pts_px, fill=col, width=3)
        for p in pts_px:
            draw.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], fill=col, outline=(0, 0, 0))
        draw.text((pts_px[0][0] + 8, pts_px[0][1] - 8), f"{records[0]['vessel_name']} ({len(records)} pts)", fill=col)

    # Header and Legend
    draw.text((20, 20), f"Sanchi Forensic AIS Vessel Attribution\nSource Zone Centroid: ({src_lat:.2f}N, {src_lon:.2f}E) +/- {src_radius_km:.1f} km", fill=(30, 30, 30))
    draw.text((src_px[0] + 10, src_px[1]), "Estimated Source Zone", fill=(200, 0, 0))

    img.save(preview_png_path)

    earliest_iso = min(parsed_dt_list).strftime("%Y-%m-%dT%H:%M:%SZ") if parsed_dt_list else "N/A"
    latest_iso = max(parsed_dt_list).strftime("%Y-%m-%dT%H:%M:%SZ") if parsed_dt_list else "N/A"

    # 7. Complete Attribution JSON Output
    attribution_data = {
        "incident_id": incident_id,
        "source_zone": {
            "centroid": {"latitude": src_lat, "longitude": src_lon},
            "uncertainty_radius_km": src_radius_km,
            "target_time": source_info.get("target_time"),
        },
        "ais_dataset": {
            "path": str(csv_path),
            "row_count": total_raw_records,
            "vessel_count": len(vessel_groups),
            "time_range": {
                "earliest": earliest_iso,
                "latest": latest_iso,
            },
        },
        "scoring_parameters": {
            "weights": weights,
            "description": "Multi-factor geodesic spatial, temporal, trajectory, and heading consistency ranking",
        },
        "candidates": scored_candidates,
        "output_files": {
            "candidates_geojson": str(candidates_geojson_path),
            "tracks_geojson": str(tracks_geojson_path),
            "attribution_json": str(attribution_json_path),
            "preview_png": str(preview_png_path),
        },
    }

    with open(attribution_json_path, "w", encoding="utf-8") as f:
        json.dump(attribution_data, f, indent=2)

    print(f"Attribution complete. Scored {len(scored_candidates)} candidates.")
    return attribution_data
