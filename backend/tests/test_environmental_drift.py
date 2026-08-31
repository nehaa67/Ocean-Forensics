"""Unit tests for real environmental backward drift / hindcast module."""

import json
from pathlib import Path
import numpy as np
import pytest
import xarray as xr

from backend.app.environmental_drift import (
    EnvironmentalField,
    run_backward_drift_hindcast,
)


@pytest.fixture
def synthetic_nc_environment(tmp_path: Path):
    """Creates synthetic wind and ocean NetCDF datasets for testing."""
    lats = np.array([28.0, 29.0, 30.0, 31.0], dtype=np.float64)
    lons = np.array([125.0, 126.0, 127.0, 128.0], dtype=np.float64)
    times = np.array(["2018-01-20T00:00:00"], dtype="datetime64[ns]")

    # 1. Wind Dataset (pure eastward wind 10.0 m/s, northward 0.0)
    u_wind = np.full((1, len(lats), len(lons)), 10.0, dtype=np.float32)
    v_wind = np.full((1, len(lats), len(lons)), 0.0, dtype=np.float32)
    # Add a single NaN to test missing data handling
    u_wind[0, 0, 0] = np.nan

    ds_wind = xr.Dataset(
        data_vars={
            "eastward_wind": (["time", "latitude", "longitude"], u_wind),
            "northward_wind": (["time", "latitude", "longitude"], v_wind),
        },
        coords={"time": times, "latitude": lats, "longitude": lons},
    )
    wind_file = tmp_path / "synthetic_wind.nc"
    ds_wind.to_netcdf(wind_file)

    # 2. Ocean Dataset (pure northward current 0.5 m/s, eastward 0.0)
    u_ocean = np.full((1, 1, len(lats), len(lons)), 0.0, dtype=np.float32)
    v_ocean = np.full((1, 1, len(lats), len(lons)), 0.5, dtype=np.float32)

    ds_ocean = xr.Dataset(
        data_vars={
            "uo": (["time", "depth", "latitude", "longitude"], u_ocean),
            "vo": (["time", "depth", "latitude", "longitude"], v_ocean),
        },
        coords={"time": times, "depth": [0.5], "latitude": lats, "longitude": lons},
    )
    ocean_file = tmp_path / "synthetic_ocean.nc"
    ds_ocean.to_netcdf(ocean_file)

    # 3. Geometry JSON fixture
    geom_file = tmp_path / "mock_geometry.json"
    geom_data = {
        "spill": {
            "centroid": {"latitude": 29.5, "longitude": 126.5},
        }
    }
    with open(geom_file, "w") as f:
        json.dump(geom_data, f)

    out_dir = tmp_path / "outputs" / "drift"
    return wind_file, ocean_file, geom_file, out_dir


def test_environmental_field_interpolation_and_missing_data(synthetic_nc_environment):
    """Test 2D bilinear interpolation and NaN handling in EnvironmentalField."""
    wind_file, ocean_file, _, _ = synthetic_nc_environment
    env = EnvironmentalField(wind_file, ocean_file)

    # Interpolate at center point (29.5, 126.5)
    (u_o, v_o), (u_w, v_w) = env.get_forcing_vectors(29.5, 126.5)

    assert pytest.approx(v_o, 0.01) == 0.5
    assert pytest.approx(u_o, 0.01) == 0.0
    assert pytest.approx(u_w, 0.01) == 10.0
    assert pytest.approx(v_w, 0.01) == 0.0


def test_backward_drift_trajectory_and_hindcast(synthetic_nc_environment):
    """Test kinematic backward displacement, uncertainty growth, and GeoJSON outputs."""
    wind_file, ocean_file, geom_file, out_dir = synthetic_nc_environment

    result = run_backward_drift_hindcast(
        wind_nc_path=wind_file,
        ocean_nc_path=ocean_file,
        geometry_json_path=geom_file,
        output_dir=out_dir,
        incident_id="test_incident",
        observation_time_iso="2018-01-20T09:00:00Z",
        hindcast_hours=10.0,
        timestep_seconds=3600.0,
        windage_coefficient=0.03,  # 10 m/s * 0.03 = 0.3 m/s eastward
    )

    assert result["mode"] == "backward_hindcast"
    assert len(result["trajectory"]) == 11  # 0 to 10 steps

    start_pt = result["trajectory"][0]
    end_pt = result["trajectory"][-1]

    # In backward drift, positive eastward windage (vx > 0) should displace longitude WESTWARD (dx < 0)
    assert end_pt["longitude"] < start_pt["longitude"]
    # Positive northward current (vy > 0) should displace latitude SOUTHWARD (dy < 0)
    assert end_pt["latitude"] < start_pt["latitude"]

    # Uncertainty should grow over time
    assert end_pt["uncertainty_radius_m"] > start_pt["uncertainty_radius_m"]

    # Verify generated files
    assert (out_dir / "sanchi_backward_trajectory.geojson").is_file()
    assert (out_dir / "sanchi_source_zone.geojson").is_file()
    assert (out_dir / "sanchi_drift.json").is_file()
    assert (out_dir / "sanchi_drift_preview.png").is_file()

    with open(out_dir / "sanchi_source_zone.geojson") as f:
        geojson = json.load(f)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 1
    assert geojson["features"][0]["geometry"]["type"] == "Polygon"
