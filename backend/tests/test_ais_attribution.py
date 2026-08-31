"""Unit tests for historical AIS filtering and vessel attribution pipeline."""

import json
from pathlib import Path
import pandas as pd
import pytest

from backend.app.ais_attribution import run_ais_attribution


@pytest.fixture
def synthetic_ais_and_drift_fixtures(tmp_path: Path):
    """Creates synthetic AIS CSV and drift JSON fixtures for deterministic unit testing."""
    csv_file = tmp_path / "synthetic_ais.csv"
    drift_file = tmp_path / "synthetic_drift.json"
    out_dir = tmp_path / "outputs" / "ais"

    # Synthetic Drift JSON
    drift_data = {
        "incident_id": "test_incident",
        "source_estimate": {
            "latitude": 30.0,
            "longitude": 125.0,
            "target_time": "2018-01-14T00:00:00Z",
            "uncertainty_radius_km": 50.0,
        },
        "trajectory": [
            {"latitude": 30.0, "longitude": 125.0, "timestamp": "2018-01-14T00:00:00Z"},
            {"latitude": 29.5, "longitude": 126.0, "timestamp": "2018-01-17T00:00:00Z"},
            {"latitude": 29.0, "longitude": 127.0, "timestamp": "2018-01-20T00:00:00Z"},
        ],
    }
    with open(drift_file, "w") as f:
        json.dump(drift_data, f)

    # Synthetic AIS Data with 3 distinct vessels:
    # 1. Vessel Alpha: Close to source zone and close in time (high score)
    # 2. Vessel Beta: Far from source zone (low spatial score)
    # 3. Vessel Gamma: Single isolated observation with missing heading
    records = [
        # Vessel Alpha (2 points inside source zone near 30.0N, 125.0E on Jan 14)
        {
            "timestamp_utc": "2018-01-14 01:00:00",
            "vessel_name": "VESSEL_ALPHA",
            "mmsi": 111222333,
            "latitude": 30.05,
            "longitude": 125.05,
            "sog_knots": 12.0,
            "cog_deg": 45.0,
            "heading_deg": 45.0,
        },
        {
            "timestamp_utc": "2018-01-14 02:00:00",
            "vessel_name": "VESSEL_ALPHA",
            "mmsi": 111222333,
            "latitude": 30.15,
            "longitude": 125.15,
            "sog_knots": 12.0,
            "cog_deg": 45.0,
            "heading_deg": 46.0,
        },
        # Vessel Beta (Far away: 25.0N, 120.0E on Jan 10)
        {
            "timestamp_utc": "2018-01-10 12:00:00",
            "vessel_name": "VESSEL_BETA",
            "mmsi": 444555666,
            "latitude": 25.0,
            "longitude": 120.0,
            "sog_knots": 15.0,
            "cog_deg": 180.0,
            "heading_deg": 180.0,
        },
        # Vessel Gamma (Single point, missing heading: 29.8N, 125.2E on Jan 15)
        {
            "timestamp_utc": "2018-01-15 06:00:00",
            "vessel_name": "VESSEL_GAMMA",
            "mmsi": 777888999,
            "latitude": 29.8,
            "longitude": 125.2,
            "sog_knots": 8.0,
            "cog_deg": 90.0,
            "heading_deg": None,
        },
    ]
    pd.DataFrame(records).to_csv(csv_file, index=False)

    return csv_file, drift_file, out_dir


def test_ais_attribution_pipeline(synthetic_ais_and_drift_fixtures):
    """Test full AIS attribution pipeline with candidate ranking and deterministic scoring."""
    csv_file, drift_file, out_dir = synthetic_ais_and_drift_fixtures

    result = run_ais_attribution(
        ais_csv_path=csv_file,
        drift_json_path=drift_file,
        output_dir=out_dir,
        incident_id="test_incident",
    )

    assert result["incident_id"] == "test_incident"
    assert result["ais_dataset"]["row_count"] == 4
    assert result["ais_dataset"]["vessel_count"] == 3

    candidates = result["candidates"]
    assert len(candidates) == 3

    # Vessel Alpha must be ranked #1 due to proximity and temporal alignment
    assert candidates[0]["vessel_name"] == "VESSEL_ALPHA"
    assert candidates[0]["rank"] == 1
    assert candidates[0]["inside_source_zone"] is True
    assert candidates[0]["score"] > candidates[1]["score"]

    # Vessel Beta must have the lowest score
    assert candidates[-1]["vessel_name"] == "VESSEL_BETA"
    assert candidates[-1]["inside_source_zone"] is False

    # Check generated files
    assert (out_dir / "sanchi_ais_candidates.geojson").is_file()
    assert (out_dir / "sanchi_vessel_tracks.geojson").is_file()
    assert (out_dir / "sanchi_attribution.json").is_file()
    assert (out_dir / "sanchi_ais_preview.png").is_file()
