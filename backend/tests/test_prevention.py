"""Unit and integration tests for Prevention, Forward Drift Prediction, and Risk Assessment."""

import io
import json
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.prevention import (
    RiskLevel,
    AtRiskVessel,
    PreventionResult,
    PredictionRequest,
    RiskRequest,
)
from backend.app.risk import (
    get_compass_direction,
    calculate_forward_drift_and_risk,
)

client = TestClient(app)


def test_compass_direction_calculation():
    assert get_compass_direction(0.0, 1.0) == "North"
    assert get_compass_direction(1.0, 0.0) == "East"
    assert get_compass_direction(0.0, -1.0) == "South"
    assert get_compass_direction(-1.0, 0.0) == "West"
    assert get_compass_direction(1.0, 1.0) == "Northeast"
    assert get_compass_direction(0.0, 0.0) == "Stationary"


def test_forward_drift_and_impact_zone():
    spill_pt = (125.0, 30.0)
    wind = (5.0, 0.0)      # 5 m/s Eastward
    current = (0.2, 0.0)   # 0.2 m/s Eastward -> Net: 0.2 + 0.03*5 = 0.35 m/s Eastward

    result = calculate_forward_drift_and_risk(
        spill_centroid=spill_pt,
        spill_area_km2=10.0,
        observation_time_iso="2026-08-29T10:00:00Z",
        wind_vector=wind,
        current_vector=current,
        ais_records=[],
        forecast_hours=6.0,
        timestep_seconds=600.0,
    )

    assert result.status == "completed"
    assert result.mode == "prevention"
    assert result.forecast_summary.predicted_movement_direction == "East"
    assert result.forecast_summary.total_drift_distance_km > 5.0
    assert result.forecast_summary.impact_zone_radius_km == 5.0  # 2.0 + 0.5 * 6.0 = 5.0 km
    assert result.forecast_summary.trajectory_points_count == 37  # 6h * 6 steps/h + 1


def test_vessel_distance_and_risk_classification(tmp_path: Path):
    spill_pt = (125.0, 30.0)
    wind = (0.0, 5.0)     # Northward
    current = (0.0, 0.2)  # Northward -> Net northward drift

    # 3 Synthetic Vessels:
    # 1. Directly in northern forecast path -> HIGH
    # 2. 5 km East of path -> MEDIUM (within 10 km warning)
    # 3. 30 km East of path -> LOW
    ais_records = [
        {
            "vessel_id": "VESSEL_HIGH",
            "vessel_name": "Tanker Alpha",
            "mmsi": "111222333",
            "latitude": 30.04,  # ~4.4 km North
            "longitude": 125.0,
            "timestamp": "2026-08-29T10:00:00Z",
            "speed": 10.0,
            "heading": 180.0,
        },
        {
            "vessel_id": "VESSEL_MED",
            "vessel_name": "Cargo Beta",
            "mmsi": "444555666",
            "latitude": 30.04,
            "longitude": 125.05, # ~4.8 km East of trajectory
            "timestamp": "2026-08-29T10:00:00Z",
            "speed": 12.0,
            "heading": 90.0,
        },
        {
            "vessel_id": "VESSEL_LOW",
            "vessel_name": "Fishing Gamma",
            "mmsi": "777888999",
            "latitude": 30.04,
            "longitude": 125.30, # ~29 km East of trajectory
            "timestamp": "2026-08-29T10:00:00Z",
            "speed": 8.0,
            "heading": 270.0,
        },
    ]

    out_dir = tmp_path / "outputs"
    result = calculate_forward_drift_and_risk(
        spill_centroid=spill_pt,
        spill_area_km2=5.0,
        observation_time_iso="2026-08-29T10:00:00Z",
        wind_vector=wind,
        current_vector=current,
        ais_records=ais_records,
        output_dir=out_dir,
        forecast_hours=6.0,
        warning_distance_km=10.0,
        high_risk_distance_km=3.0,
    )

    assert len(result.at_risk_vessels) == 3
    assert result.high_risk_count == 1
    assert result.medium_risk_count == 1
    assert result.low_risk_count == 1

    v_high = next(v for v in result.at_risk_vessels if v.vessel_id == "VESSEL_HIGH")
    assert v_high.risk_level == RiskLevel.HIGH
    assert "HIGH RISK" in v_high.explanation
    assert v_high.distance_to_trajectory_km <= 3.0

    v_med = next(v for v in result.at_risk_vessels if v.vessel_id == "VESSEL_MED")
    assert v_med.risk_level == RiskLevel.MEDIUM
    assert "MEDIUM RISK" in v_med.explanation
    assert 3.0 < v_med.distance_to_trajectory_km <= 10.0

    v_low = next(v for v in result.at_risk_vessels if v.vessel_id == "VESSEL_LOW")
    assert v_low.risk_level == RiskLevel.LOW
    assert "LOW RISK" in v_low.explanation
    assert v_low.distance_to_trajectory_km > 10.0

    # Verify artifacts created
    assert (out_dir / "prediction" / "forward_trajectory.geojson").exists()
    assert (out_dir / "prediction" / "predicted_impact_zone.geojson").exists()
    assert (out_dir / "risk" / "at_risk_vessels.geojson").exists()
    assert (out_dir / "prediction" / "prediction_preview.png").exists()


def test_empty_ais_handling():
    result = calculate_forward_drift_and_risk(
        spill_centroid=(125.0, 30.0),
        spill_area_km2=2.0,
        observation_time_iso="2026-08-29T10:00:00Z",
        wind_vector=(2.0, 2.0),
        current_vector=(0.1, 0.1),
        ais_records=[],
    )
    assert len(result.at_risk_vessels) == 0
    assert result.high_risk_count == 0
    assert result.medium_risk_count == 0
    assert result.low_risk_count == 0


def test_api_prediction_endpoint():
    payload = {
        "spill_centroid": [125.0, 30.0],
        "spill_area_km2": 4.5,
        "wind_vector": [4.0, 1.0],
        "current_vector": [0.2, 0.1],
        "forecast_hours": 3.0,
        "warning_distance_km": 15.0,
        "ais_records": [
            {
                "vessel_id": "V1",
                "vessel_name": "Ship 1",
                "latitude": 30.01,
                "longitude": 125.02,
                "timestamp": "2026-08-29T10:00:00Z",
            }
        ],
    }
    response = client.post("/api/v1/prediction", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["mode"] == "prevention"
    assert data["forecast_summary"]["forecast_duration_hours"] == 3.0
    assert len(data["at_risk_vessels"]) == 1


def test_api_risk_endpoint():
    payload = {
        "forecast_hours": 6.0,
        "warning_distance_km": 12.0,
    }
    response = client.post("/api/v1/risk", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["mode"] == "prevention"


def test_end_to_end_prevention_synthetic_scenario(tmp_path: Path):
    """Full synthetic prevention pipeline test:
    Mock Detection/Geometry -> Forward Drift -> Impact Zone -> AIS Correlation -> Risk
    """
    # 1. Synthetic Detection & Geometry
    synthetic_centroid = (125.0, 30.0) # lon, lat
    synthetic_area_km2 = 8.5

    # 2. Synthetic Environmental Forcing: Strong Eastward Net Drift
    # Wind: 10 m/s Eastward (u=10, v=0) -> 0.03 * 10 = 0.30 m/s
    # Ocean Current: 0.20 m/s Eastward (u=0.2, v=0)
    # Net transport: 0.50 m/s Eastward (~1.8 km/h Eastward)
    wind = (10.0, 0.0)
    current = (0.2, 0.0)

    # In 6 hours, slick drifts ~10.8 km Eastward to ~125.112° E
    # 3. Synthetic AIS Fleet:
    # - Vessel A (Tanker 101): Positioned directly in path at (125.08° E, 30.0° N) -> Expected: HIGH RISK
    # - Vessel B (Cargo 202): Positioned 5 km South of path at (125.08° E, 29.955° N) -> Expected: MEDIUM RISK
    # - Vessel C (Trawler 303): Positioned 25 km South of path at (125.08° E, 29.775° N) -> Expected: LOW RISK
    ais_data = [
        {
            "vessel_id": "V_TANKER_101",
            "vessel_name": "Crude Voyager",
            "mmsi": "999000101",
            "longitude": 125.08,
            "latitude": 30.0,
            "timestamp": "2026-08-29T10:00:00Z",
            "speed": 11.5,
            "heading": 270.0,
        },
        {
            "vessel_id": "V_CARGO_202",
            "vessel_name": "Pacific Carrier",
            "mmsi": "999000202",
            "longitude": 125.08,
            "latitude": 29.955,
            "timestamp": "2026-08-29T10:00:00Z",
            "speed": 14.0,
            "heading": 45.0,
        },
        {
            "vessel_id": "V_TRAWLER_303",
            "vessel_name": "Ocean Bounty",
            "mmsi": "999000303",
            "longitude": 125.08,
            "latitude": 29.775,
            "timestamp": "2026-08-29T10:00:00Z",
            "speed": 7.0,
            "heading": 180.0,
        },
    ]

    out_workspace = tmp_path / "investigations" / "INV-TEST-PREV" / "outputs"

    result = calculate_forward_drift_and_risk(
        spill_centroid=synthetic_centroid,
        spill_area_km2=synthetic_area_km2,
        observation_time_iso="2026-08-29T10:00:00Z",
        wind_vector=wind,
        current_vector=current,
        ais_records=ais_data,
        output_dir=out_workspace,
        analysis_id="INV-TEST-PREV",
        forecast_hours=6.0,
        timestep_seconds=600.0,
        warning_distance_km=10.0,
        high_risk_distance_km=3.0,
    )

    # 4. Assert Pipeline Results
    assert result.status == "completed"
    assert result.forecast_summary.predicted_movement_direction == "East"
    assert result.forecast_summary.total_drift_distance_km > 8.0
    assert result.high_risk_count == 1
    assert result.medium_risk_count == 1
    assert result.low_risk_count == 1

    # Verify Ranked Ordering: High risk first
    assert result.at_risk_vessels[0].vessel_id == "V_TANKER_101"
    assert result.at_risk_vessels[0].risk_level == RiskLevel.HIGH
    assert result.at_risk_vessels[0].eta_minutes is not None
    assert result.at_risk_vessels[0].inside_impact_zone is True

    assert result.at_risk_vessels[1].vessel_id == "V_CARGO_202"
    assert result.at_risk_vessels[1].risk_level == RiskLevel.MEDIUM

    assert result.at_risk_vessels[2].vessel_id == "V_TRAWLER_303"
    assert result.at_risk_vessels[2].risk_level == RiskLevel.LOW

    # Verify JSON and GeoJSON outputs
    assert (out_workspace / "prediction" / "prediction.json").exists()
    assert (out_workspace / "risk" / "risk.json").exists()
    with open(out_workspace / "risk" / "risk.json", "r", encoding="utf-8") as f:
        saved_json = json.load(f)
    assert saved_json["analysis_id"] == "INV-TEST-PREV"


def test_api_prediction_exact_user_payload():
    """Regression test reproducing the exact user POST /api/v1/prediction payload."""
    payload = {
        "analysis_id": "INV-PREV-01",
        "forecast_hours": 6.0,
        "timestep_seconds": 600.0,
        "windage": 0.03,
        "warning_distance_km": 10.0,
        "high_risk_distance_km": 3.0,
        "spill_centroid": [125.0, 30.0],
        "spill_area_km2": 8.5,
        "wind_vector": [10.0, 0.0],
        "current_vector": [0.2, 0.0],
        "ais_records": [
            {
                "vessel_id": "V_TANKER_101",
                "vessel_name": "Crude Voyager",
                "latitude": 30.0,
                "longitude": 125.08,
                "speed_knots": 11.5,
                "heading_deg": 270.0,
            },
            {
                "vessel_id": "V_CARGO_202",
                "vessel_name": "Ocean Trader",
                "latitude": 30.05,
                "longitude": 125.15,
                "speed_knots": 8.0,
                "heading_deg": 90.0,
            },
        ],
    }
    response = client.post("/api/v1/prediction", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["analysis_id"] == "INV-PREV-01"
    assert len(data["at_risk_vessels"]) == 2
    assert data["at_risk_vessels"][0]["risk_level"] == "HIGH"
    assert data["at_risk_vessels"][1]["risk_level"] == "MEDIUM"


