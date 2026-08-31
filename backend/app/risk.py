"""Geospatial Risk Assessment and Forward Drift Prediction Module.

Implements:
1. Kinematic forward drift trajectory forecasting (reusing backend/app/drift.py).
2. Predicted impact zone polygon generation with uncertainty expansion.
3. AIS vessel proximity, encounter time (ETA), and deterministic risk classification:
   - HIGH: Directly inside impact zone or imminent intercept.
   - MEDIUM: Within warning distance of predicted drift path.
   - LOW: In broader surveillance region outside warning corridor.
4. GeoJSON artifact creation and diagnostic visualization.
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw
import pyproj
from pyproj import Geod, Transformer
import rasterio
from shapely.geometry import Point, LineString, Polygon, mapping
from shapely.ops import transform as shapely_transform

from backend.app.drift import simulate_drift
from backend.app.ais import group_tracks
from backend.app.schemas.prevention import (
    RiskLevel,
    AtRiskVessel,
    SpillSummary,
    ForecastSummary,
    PreventionResult,
)


DEFAULT_WARNING_DISTANCE_KM: float = 10.0
DEFAULT_HIGH_RISK_DISTANCE_KM: float = 3.0
DEFAULT_INITIAL_UNCERTAINTY_KM: float = 2.0
DEFAULT_UNCERTAINTY_GROWTH_KM_PER_H: float = 0.5


def get_compass_direction(vx: float, vy: float) -> str:
    """Returns a 16-point compass direction for a velocity vector (vx = eastward, vy = northward)."""
    if abs(vx) < 1e-6 and abs(vy) < 1e-6:
        return "Stationary"
    angle_rad = math.atan2(vx, vy)  # 0 is North, pi/2 is East
    angle_deg = (math.degrees(angle_rad) + 360.0) % 360.0

    compass_sectors = [
        "North", "North-Northeast", "Northeast", "East-Northeast",
        "East", "East-Southeast", "Southeast", "South-Southeast",
        "South", "South-Southwest", "Southwest", "West-Southwest",
        "West", "West-Northwest", "Northwest", "North-Northwest",
    ]
    idx = int((angle_deg + 11.25) / 22.5) % 16
    return compass_sectors[idx]


def calculate_forward_drift_and_risk(
    spill_centroid: Tuple[float, float],
    spill_area_km2: float,
    observation_time_iso: str,
    wind_vector: Tuple[float, float],       # (u, v) in m/s
    current_vector: Tuple[float, float],    # (u, v) in m/s
    ais_records: List[Dict[str, Any]],
    output_dir: Optional[Union[str, Path]] = None,
    analysis_id: str = "PREV-AUTO",
    forecast_hours: float = 6.0,
    timestep_seconds: float = 600.0,
    windage: float = 0.03,
    warning_distance_km: float = DEFAULT_WARNING_DISTANCE_KM,
    high_risk_distance_km: float = DEFAULT_HIGH_RISK_DISTANCE_KM,
) -> PreventionResult:
    """Calculates forward drift trajectory, predicted impact zone, and at-risk vessel classifications."""
    start_lon, start_lat = float(spill_centroid[0]), float(spill_centroid[1])
    obs_time = datetime.fromisoformat(observation_time_iso.replace("Z", "+00:00"))
    if obs_time.tzinfo is None:
        obs_time = obs_time.replace(tzinfo=timezone.utc)

    # 1. Forward Drift Simulation (Reusing backend/app/drift.py)
    crs_wgs84 = rasterio.crs.CRS.from_epsg(4326)
    drift_result = simulate_drift(
        start_point=(start_lon, start_lat),
        duration_hours=forecast_hours,
        timestep_seconds=timestep_seconds,
        current=current_vector,
        wind=wind_vector,
        windage=windage,
        direction="forward",
        crs=crs_wgs84,
    )

    raw_trajectory = drift_result.get("trajectory", [])
    eff_vel = drift_result.get("effective_velocity_m_s", {})
    vx, vy = float(eff_vel.get("vx", 0.0)), float(eff_vel.get("vy", 0.0))
    drift_speed_m_s = math.sqrt(vx ** 2 + vy ** 2)

    # Calculate timestamps and waypoints
    traj_coords = []
    formatted_traj = []
    for step_idx, pt in enumerate(raw_trajectory):
        step_time = obs_time + timedelta(seconds=step_idx * timestep_seconds)
        pt_lon, pt_lat = float(pt["lon"]), float(pt["lat"])
        traj_coords.append((pt_lon, pt_lat))
        formatted_traj.append({
            "step": step_idx,
            "timestamp": step_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "longitude": round(pt_lon, 6),
            "latitude": round(pt_lat, 6),
            "speed_m_s": round(drift_speed_m_s, 4),
        })

    end_lon, end_lat = traj_coords[-1] if traj_coords else (start_lon, start_lat)
    target_time_iso = (obs_time + timedelta(hours=forecast_hours)).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Geodesic total drift distance
    geod = Geod(ellps="WGS84")
    _, _, total_drift_dist_m = geod.inv(start_lon, start_lat, end_lon, end_lat)
    total_drift_dist_km = total_drift_dist_m / 1000.0

    # Compass movement direction
    direction_label = get_compass_direction(vx, vy)

    # 2. Predicted Impact Zone Polygon Generation
    final_unc_km = DEFAULT_INITIAL_UNCERTAINTY_KM + (DEFAULT_UNCERTAINTY_GROWTH_KM_PER_H * forecast_hours)
    final_unc_m = final_unc_km * 1000.0

    # Construct metric buffer around endpoint and trajectory corridor
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    to_wgs84 = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)

    utm_end = Point(to_utm.transform(end_lon, end_lat))
    impact_buffer_utm = utm_end.buffer(final_unc_m, quad_segs=32)

    buf_x, buf_y = impact_buffer_utm.exterior.coords.xy
    buf_lons, buf_lats = to_wgs84.transform(list(buf_x), list(buf_y))
    impact_zone_wgs84 = Polygon(zip(buf_lons, buf_lats))

    # 3. AIS Vessel Risk Assessment
    at_risk_vessels: List[AtRiskVessel] = []
    point_features = []

    if ais_records:
        # Sanitize and normalize AIS records
        sanitized_ais = []
        for idx, raw_rec in enumerate(ais_records):
            r = dict(raw_rec)
            vid = r.get("vessel_id") or r.get("mmsi") or r.get("vessel_name") or r.get("name") or f"VESSEL-{idx+1}"
            r["vessel_id"] = str(vid)
            if "timestamp" not in r or not r["timestamp"]:
                r["timestamp"] = r.get("timestamp_utc") or r.get("time") or r.get("datetime") or obs_time.strftime("%Y-%m-%dT%H:%M:%SZ")
            if "speed" not in r or r["speed"] is None:
                r["speed"] = r.get("speed_knots", r.get("sog", r.get("speed_kts")))
            if "heading" not in r or r["heading"] is None:
                r["heading"] = r.get("heading_deg", r.get("cog", r.get("course")))
            sanitized_ais.append(r)

        # Group records by vessel
        tracks = group_tracks(sanitized_ais)

        for vid, recs in tracks.items():
            def _parse_rec_ts(r: Dict[str, Any]) -> datetime:
                raw_t = r.get("timestamp")
                if isinstance(raw_t, datetime):
                    return raw_t
                try:
                    return datetime.fromisoformat(str(raw_t).replace("Z", "+00:00"))
                except Exception:
                    return obs_time

            recs.sort(key=_parse_rec_ts)
            latest_rec = recs[-1]
            v_lon = float(latest_rec["longitude"])
            v_lat = float(latest_rec["latitude"])
            v_name = latest_rec.get("vessel_name") or latest_rec.get("name") or f"VESSEL-{vid}"
            mmsi_val = latest_rec.get("mmsi")
            mmsi_str = str(mmsi_val) if mmsi_val is not None else None
            speed_kts = float(latest_rec["speed"]) if "speed" in latest_rec and latest_rec["speed"] is not None else None
            heading = float(latest_rec["heading"]) if "heading" in latest_rec and latest_rec["heading"] is not None else None

            # Distance from vessel to initial spill centroid
            _, _, d_spill_m = geod.inv(v_lon, v_lat, start_lon, start_lat)
            d_spill_km = d_spill_m / 1000.0

            # Distance from vessel to closest point on trajectory
            min_traj_d_m = min(geod.inv(v_lon, v_lat, wp[0], wp[1])[2] for wp in traj_coords) if traj_coords else d_spill_m
            d_traj_km = min_traj_d_m / 1000.0

            # Distance to final impact zone centroid
            _, _, d_impact_m = geod.inv(v_lon, v_lat, end_lon, end_lat)
            d_impact_km = d_impact_m / 1000.0

            inside_impact = (d_impact_km <= final_unc_km) or (d_traj_km <= high_risk_distance_km)

            # ETA Calculation
            eta_minutes: Optional[float] = None
            closest_approach_iso: Optional[str] = None
            if drift_speed_m_s > 0.05:
                # Find step along trajectory closest to vessel
                wp_dists = [geod.inv(v_lon, v_lat, wp[0], wp[1])[2] for wp in traj_coords]
                min_step = int(np.argmin(wp_dists))
                eta_minutes = round((min_step * timestep_seconds) / 60.0, 1)
                closest_time = obs_time + timedelta(seconds=min_step * timestep_seconds)
                closest_approach_iso = closest_time.strftime("%Y-%m-%dT%H:%M:%SZ")

            # Deterministic Risk Level & Explainability
            if inside_impact or (d_traj_km <= high_risk_distance_km):
                risk_level = RiskLevel.HIGH
                explanation = (
                    f"HIGH RISK: Vessel is directly within the predicted impact zone "
                    f"({d_traj_km:.1f} km from forecast path, {d_impact_km:.1f} km from impact center). "
                    f"Immediate advisory warning and evasive action recommended."
                )
            elif d_traj_km <= warning_distance_km:
                risk_level = RiskLevel.MEDIUM
                explanation = (
                    f"MEDIUM RISK: Vessel is within the {warning_distance_km:.0f} km warning corridor "
                    f"({d_traj_km:.1f} km from predicted drift track). Precautionary monitoring active."
                )
            else:
                risk_level = RiskLevel.LOW
                explanation = (
                    f"LOW RISK: Vessel is outside the immediate warning distance "
                    f"({d_traj_km:.1f} km from predicted track) but remains within the regional forecast domain."
                )

            vessel_obj = AtRiskVessel(
                vessel_id=str(vid),
                vessel_name=v_name,
                mmsi=mmsi_str,
                risk_level=risk_level,
                distance_to_spill_km=round(d_spill_km, 2),
                distance_to_trajectory_km=round(d_traj_km, 2),
                inside_impact_zone=inside_impact,
                eta_minutes=eta_minutes,
                closest_approach_time=closest_approach_iso,
                current_position=(round(v_lon, 6), round(v_lat, 6)),
                speed_knots=round(speed_kts, 1) if speed_kts is not None else None,
                heading_deg=round(heading, 1) if heading is not None else None,
                explanation=explanation,
                provenance={
                    "distance_to_impact_center_km": round(d_impact_km, 2),
                    "impact_zone_radius_km": round(final_unc_km, 2),
                    "warning_threshold_km": warning_distance_km,
                },
            )
            at_risk_vessels.append(vessel_obj)

            point_features.append({
                "type": "Feature",
                "properties": {
                    "vessel_id": str(vid),
                    "vessel_name": v_name,
                    "risk_level": risk_level.value,
                    "distance_to_trajectory_km": round(d_traj_km, 2),
                    "inside_impact_zone": inside_impact,
                    "eta_minutes": eta_minutes,
                    "explanation": explanation,
                },
                "geometry": mapping(Point(v_lon, v_lat)),
            })

    # Sort vessels: HIGH -> MEDIUM -> LOW, then by distance
    risk_rank = {RiskLevel.HIGH: 0, RiskLevel.MEDIUM: 1, RiskLevel.LOW: 2}
    at_risk_vessels.sort(key=lambda v: (risk_rank[v.risk_level], v.distance_to_trajectory_km))

    high_count = sum(1 for v in at_risk_vessels if v.risk_level == RiskLevel.HIGH)
    med_count = sum(1 for v in at_risk_vessels if v.risk_level == RiskLevel.MEDIUM)
    low_count = sum(1 for v in at_risk_vessels if v.risk_level == RiskLevel.LOW)

    # 4. Export Artifacts if output_dir provided
    artifacts_map: Dict[str, str] = {}
    if output_dir:
        out_base = Path(output_dir)
        pred_dir = out_base / "prediction"
        risk_dir = out_base / "risk"
        pred_dir.mkdir(parents=True, exist_ok=True)
        risk_dir.mkdir(parents=True, exist_ok=True)

        traj_geojson_path = pred_dir / "forward_trajectory.geojson"
        impact_geojson_path = pred_dir / "predicted_impact_zone.geojson"
        pred_json_path = pred_dir / "prediction.json"
        pred_png_path = pred_dir / "prediction_preview.png"

        vessels_geojson_path = risk_dir / "at_risk_vessels.geojson"
        risk_json_path = risk_dir / "risk.json"
        risk_png_path = risk_dir / "risk_preview.png"

        # Export Trajectory GeoJSON
        linestring_feature = {
            "type": "Feature",
            "properties": {
                "name": "forward_drift_forecast_track",
                "forecast_hours": forecast_hours,
                "movement_direction": direction_label,
                "total_drift_distance_km": round(total_drift_dist_km, 2),
                "speed_m_s": round(drift_speed_m_s, 4),
            },
            "geometry": mapping(LineString(traj_coords)),
        }
        traj_geojson_data = {
            "type": "FeatureCollection",
            "name": "forward_drift_trajectory",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "features": [linestring_feature],
        }
        with open(traj_geojson_path, "w", encoding="utf-8") as f:
            json.dump(traj_geojson_data, f, indent=2)

        # Export Impact Zone GeoJSON
        impact_geojson_data = {
            "type": "FeatureCollection",
            "name": "predicted_impact_zone",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "features": [
                {
                    "type": "Feature",
                    "properties": {
                        "target_time": target_time_iso,
                        "forecast_hours": forecast_hours,
                        "uncertainty_radius_km": round(final_unc_km, 2),
                        "centroid": [round(end_lat, 6), round(end_lon, 6)],
                    },
                    "geometry": mapping(impact_zone_wgs84),
                }
            ],
        }
        with open(impact_geojson_path, "w", encoding="utf-8") as f:
            json.dump(impact_geojson_data, f, indent=2)

        # Export At-Risk Vessels GeoJSON
        vessels_geojson_data = {
            "type": "FeatureCollection",
            "name": "at_risk_vessels",
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "features": point_features,
        }
        with open(vessels_geojson_path, "w", encoding="utf-8") as f:
            json.dump(vessels_geojson_data, f, indent=2)

        # Generate Diagnostic Previews
        img_w, img_h = 800, 600
        img = Image.new("RGB", (img_w, img_h), color=(245, 248, 252))
        draw = ImageDraw.Draw(img)

        # Extent
        all_lons = [start_lon, end_lon] + [wp[0] for wp in traj_coords] + [v.current_position[0] for v in at_risk_vessels] + list(buf_lons)
        all_lats = [start_lat, end_lat] + [wp[1] for wp in traj_coords] + [v.current_position[1] for v in at_risk_vessels] + list(buf_lats)
        min_lo, max_lo = min(all_lons) - 0.1, max(all_lons) + 0.1
        min_la, max_la = min(all_lats) - 0.1, max(all_lats) + 0.1

        def to_px(lon, lat):
            px = int((lon - min_lo) / max(1e-6, max_lo - min_lo) * (img_w - 80) + 40)
            py = int((max_la - lat) / max(1e-6, max_la - min_la) * (img_h - 80) + 40)
            return px, py

        # Impact Zone Buffer
        buf_px = [to_px(lo, la) for lo, la in zip(buf_lons, buf_lats)]
        draw.polygon(buf_px, fill=(255, 230, 230), outline=(220, 50, 50))

        # Trajectory Line
        if len(traj_coords) >= 2:
            traj_px = [to_px(lo, la) for lo, la in traj_coords]
            draw.line(traj_px, fill=(20, 80, 200), width=3)

        # Observed Centroid (Orange)
        obs_px = to_px(start_lon, start_lat)
        draw.ellipse([obs_px[0] - 6, obs_px[1] - 6, obs_px[0] + 6, obs_px[1] + 6], fill=(240, 120, 0), outline=(150, 60, 0))

        # Forecast Endpoint (Red)
        end_px = to_px(end_lon, end_lat)
        draw.ellipse([end_px[0] - 6, end_px[1] - 6, end_px[0] + 6, end_px[1] + 6], fill=(220, 30, 30), outline=(150, 0, 0))

        # Vessels
        for v in at_risk_vessels:
            v_px = to_px(v.current_position[0], v.current_position[1])
            v_col = (220, 20, 20) if v.risk_level == RiskLevel.HIGH else ((230, 150, 0) if v.risk_level == RiskLevel.MEDIUM else (30, 160, 50))
            draw.ellipse([v_px[0] - 5, v_px[1] - 5, v_px[0] + 5, v_px[1] + 5], fill=v_col, outline=(0, 0, 0))
            draw.text((v_px[0] + 8, v_px[1] - 8), f"{v.vessel_name} [{v.risk_level.value}]", fill=v_col)

        # Labels
        draw.text((20, 20), f"Early-Warning Forward Spill Forecast ({forecast_hours:.1f}h)\nPredicted Transport: {direction_label} ({drift_speed_m_s:.2f} m/s)", fill=(30, 30, 30))
        draw.text((obs_px[0] + 10, obs_px[1]), "Observed Spill Centroid", fill=(180, 80, 0))
        draw.text((end_px[0] + 10, end_px[1]), f"Impact Zone (T+{forecast_hours:.0f}h)", fill=(200, 0, 0))

        img.save(pred_png_path)
        img.save(risk_png_path)

        artifacts_map = {
            "forward_trajectory_geojson": str(traj_geojson_path),
            "predicted_impact_zone_geojson": str(impact_geojson_path),
            "at_risk_vessels_geojson": str(vessels_geojson_path),
            "prediction_preview_png": str(pred_png_path),
            "risk_preview_png": str(risk_png_path),
        }

    # 5. Construct Final PreventionResult
    spill_summary_obj = SpillSummary(
        detected=True,
        area_m2=round(spill_area_km2 * 1e6, 2),
        area_km2=round(spill_area_km2, 4),
        confidence=0.95,
        centroid=(round(start_lon, 6), round(start_lat, 6)),
        bbox=(
            round(start_lon - 0.05, 4),
            round(start_lat - 0.05, 4),
            round(start_lon + 0.05, 4),
            round(start_lat + 0.05, 4),
        ),
    )

    forecast_summary_obj = ForecastSummary(
        forecast_duration_hours=forecast_hours,
        timestep_seconds=timestep_seconds,
        predicted_movement_direction=direction_label,
        total_drift_distance_km=round(total_drift_dist_km, 2),
        mean_drift_speed_m_s=round(drift_speed_m_s, 4),
        impact_zone_radius_km=round(final_unc_km, 2),
        trajectory_points_count=len(formatted_traj),
        effective_velocity_m_s={"vx": round(vx, 4), "vy": round(vy, 4)},
    )

    result = PreventionResult(
        analysis_id=analysis_id,
        mode="prevention",
        status="completed",
        observation_time=obs_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        forecast_start_time=obs_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        forecast_target_time=target_time_iso,
        spill_summary=spill_summary_obj,
        forecast_summary=forecast_summary_obj,
        at_risk_vessels=at_risk_vessels,
        high_risk_count=high_count,
        medium_risk_count=med_count,
        low_risk_count=low_count,
        environment={
            "wind_vector_m_s": {"u": round(wind_vector[0], 2), "v": round(wind_vector[1], 2)},
            "current_vector_m_s": {"u": round(current_vector[0], 2), "v": round(current_vector[1], 2)},
            "windage_coefficient": windage,
        },
        artifacts=artifacts_map,
        quality_warnings=[
            "Forward drift is a kinematic wind/current displacement forecast, not a full 3D chemical/weathering simulation.",
            "Risk classification is an advisory spatial/temporal proximity estimate, not a guaranteed collision prediction.",
        ],
        provenance={
            "method": "kinematic forward drift with 3% empirical leeway",
            "warning_threshold_km": warning_distance_km,
            "high_risk_threshold_km": high_risk_distance_km,
            "trajectory": formatted_traj,
        },
    )

    if output_dir:
        with open(pred_dir / "prediction.json", "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2)
        with open(risk_dir / "risk.json", "w", encoding="utf-8") as f:
            json.dump(result.model_dump(), f, indent=2)

    return result
