"""Unit and integration tests for Historical Investigation Service and pipeline orchestration."""

import json
from pathlib import Path
import pytest
from fastapi import HTTPException

from backend.app.incidents import IncidentRegistry
from backend.app.services.historical_investigation_service import HistoricalInvestigationService


@pytest.fixture
def mock_incident_environment(tmp_path: Path):
    """Creates a lightweight mock incident directory with synthetic outputs for fast unit testing."""
    inc_root = tmp_path / "incidents"
    inc_dir = inc_root / "test_mock_incident"
    inc_dir.mkdir(parents=True)

    metadata = {
        "incident_id": "test_mock_incident",
        "name": "Test Mock Incident",
        "observation_time": "2018-01-20T09:00:00Z",
        "expected_files": {
            "sentinel": "sentinel_mock.tif",
            "wind": "wind_mock.nc",
            "current": "ocean_mock.nc",
            "ais": "ais_mock.csv",
        },
    }
    with open(inc_dir / "metadata.json", "w") as f:
        json.dump(metadata, f)

    # Create dummy input files
    (inc_dir / "sentinel_mock.tif").touch()
    (inc_dir / "wind_mock.nc").touch()
    (inc_dir / "ocean_mock.nc").touch()
    (inc_dir / "ais_mock.csv").touch()

    # Create pre-computed mock outputs
    outputs_dir = inc_dir / "outputs"
    geom_dir = outputs_dir / "geometry"
    drift_dir = outputs_dir / "drift"
    ais_dir = outputs_dir / "ais"
    for d in [outputs_dir, geom_dir, drift_dir, ais_dir]:
        d.mkdir(parents=True, exist_ok=True)

    (outputs_dir / "sanchi_probability_map.tif").touch()
    (outputs_dir / "sanchi_oil_mask.tif").touch()
    with open(outputs_dir / "sanchi_inference_metadata.json", "w") as f:
        json.dump({"scene_dimensions": {"height": 512, "width": 512, "total_pixels": 262144}}, f)

    (geom_dir / "sanchi_oil_mask_valid.tif").touch()
    (geom_dir / "sanchi_spill.geojson").touch()
    with open(geom_dir / "sanchi_geometry.json", "w") as f:
        json.dump({
            "threshold": 0.5,
            "valid_pixel_count": 200000,
            "invalid_pixel_count": 62144,
            "predicted_oil_pixels_before_filter": 5000,
            "predicted_oil_pixels_after_filter": 4800,
            "corrected_oil_percentage_of_valid_ocean": 2.5,
            "core_070_oil_percentage_of_valid_ocean": 0.5,
            "component_count_after_filter": 1,
            "spill": {
                "area_m2": 500000.0,
                "area_km2": 0.5,
                "perimeter_m": 3000.0,
                "centroid": {"latitude": 30.0, "longitude": 125.0},
                "bbox": [124.9, 29.9, 125.1, 30.1],
            },
            "core_070": {"area_km2": 0.1},
        }, f)

    (drift_dir / "sanchi_backward_trajectory.geojson").touch()
    (drift_dir / "sanchi_source_zone.geojson").touch()
    with open(drift_dir / "sanchi_drift.json", "w") as f:
        json.dump({
            "estimated_source_time": "2018-01-14T09:00:00Z",
            "parameters": {"hindcast_duration_hours": 144.0, "timestep_seconds": 3600.0, "method": "kinematic", "windage_coefficient": 0.03},
            "source_estimate": {"latitude": 30.2, "longitude": 125.1, "uncertainty_radius_m": 48000.0},
            "environment": {"selected_wind_time": "2018-01-20T00:00:00Z", "selected_current_time": "2018-01-20T00:00:00Z", "selected_ocean_depth_m": 0.5},
            "trajectory": [{"net_transport_velocity_m_s": {"vx": 0.1, "vy": 0.1}, "latitude": 30.0, "longitude": 125.0, "timestamp": "2018-01-20T09:00:00Z"}],
        }, f)

    (ais_dir / "sanchi_ais_candidates.geojson").touch()
    (ais_dir / "sanchi_vessel_tracks.geojson").touch()
    with open(ais_dir / "sanchi_attribution.json", "w") as f:
        json.dump({
            "candidates": [
                {
                    "rank": 1,
                    "vessel_name": "MOCK_VESSEL",
                    "mmsi": "123456789",
                    "score": 0.85,
                    "spatial_score": 0.9,
                    "temporal_score": 0.8,
                    "trajectory_score": 0.85,
                    "heading_score": 0.85,
                    "closest_distance_km": 12.0,
                    "closest_timestamp": "2018-01-14T09:00:00Z",
                    "inside_source_zone": True,
                    "record_count": 5,
                    "evidence": ["Closest approach is 12.0 km from the estimated source centroid."],
                }
            ]
        }, f)

    registry = IncidentRegistry(data_root=inc_root)
    return registry, inc_dir


def test_historical_service_cached_reuse_and_result(mock_incident_environment):
    """Test that existing valid cached outputs are reused and InvestigationResult is assembled correctly."""
    registry, _ = mock_incident_environment
    service = HistoricalInvestigationService(registry)

    result = service.run_investigation("test_mock_incident", force_recompute=False)

    assert result.incident_id == "test_mock_incident"
    assert result.status == "completed"
    assert result.detection.detected is True
    assert result.geometry.area_m2 == 500000.0
    assert result.source_zone.estimated_origin == (125.1, 30.2)
    assert len(result.candidates) == 1
    assert result.candidates[0].vessel_id == "MOCK_VESSEL"
    assert result.candidates[0].overall_score == 0.85

    # Check cached reuses tracked in provenance
    cached = result.provenance.get("cached_outputs_reused", [])
    assert "DETECTION" in cached
    assert "GEOMETRY" in cached
    assert "DRIFT" in cached
    assert "ATTRIBUTION" in cached


def test_historical_service_invalid_incident_raises_404(mock_incident_environment):
    """Test that requesting an invalid incident ID raises HTTPException 404."""
    registry, _ = mock_incident_environment
    service = HistoricalInvestigationService(registry)

    with pytest.raises(HTTPException) as exc:
        service.run_investigation("non_existent_id_404")
    assert exc.value.status_code == 404


def test_historical_service_missing_input_raises_400(mock_incident_environment):
    """Test that missing required input dataset raises validation error."""
    registry, inc_dir = mock_incident_environment
    # Remove required wind file
    (inc_dir / "wind_mock.nc").unlink()

    service = HistoricalInvestigationService(registry)
    with pytest.raises(HTTPException) as exc:
        service.run_investigation("test_mock_incident")
    assert exc.value.status_code == 400
    assert "VALIDATING" in str(exc.value.detail)
