import json
from pathlib import Path

from backend.app.providers import (
    SatelliteProvider,
    MockSatelliteProvider,
    SatelliteMetadata,
    WeatherProvider,
    MockWeatherProvider,
    WindData,
    CurrentsProvider,
    MockCurrentsProvider,
    CurrentData,
    AISProvider,
    MockAISProvider,
    AISRecord,
)

def test_mock_satellite_provider_returns_fixed_metadata():
    provider = MockSatelliteProvider()
    meta = provider.get_scene_metadata("any_scene")
    assert isinstance(meta, SatelliteMetadata)
    # Verify it matches the synthetic metadata file
    metadata_path = Path(__file__).resolve().parents[2] / "data" / "sample" / "metadata.json"
    with metadata_path.open() as f:
        data = json.load(f)
    assert meta.scene_id == "synthetic_scene"
    assert meta.timestamp == "2023-01-01T00:00:00Z"
    assert meta.transform == tuple(data["transform"])
    assert meta.crs_epsg == data["crs_epsg"]

def test_mock_weather_provider_returns_fixed_wind():
    provider = MockWeatherProvider()
    wind = provider.get_wind("any_scene")
    assert isinstance(wind, WindData)
    env_path = Path(__file__).resolve().parents[2] / "data" / "sample" / "environment.json"
    with env_path.open() as f:
        env = json.load(f)
    assert wind.u == env["wind"][0]
    assert wind.v == env["wind"][1]

def test_mock_currents_provider_returns_fixed_current():
    provider = MockCurrentsProvider()
    cur = provider.get_current("any_scene")
    assert isinstance(cur, CurrentData)
    env_path = Path(__file__).resolve().parents[2] / "data" / "sample" / "environment.json"
    with env_path.open() as f:
        env = json.load(f)
    assert cur.u == env["current"][0]
    assert cur.v == env["current"][1]

def test_mock_ais_provider_returns_records():
    provider = MockAISProvider()
    recs = provider.get_records("any_scene")
    assert isinstance(recs, list)
    assert len(recs) > 0
    for rec in recs:
        assert isinstance(rec, AISRecord)
        # Basic field checks
        assert isinstance(rec.vessel_id, str)
        assert isinstance(rec.latitude, float)
        assert isinstance(rec.longitude, float)
        assert isinstance(rec.timestamp, str)
        assert isinstance(rec.speed, float)
        assert isinstance(rec.heading, float)

# Verify that the provider classes conform to their Protocols (runtime check)
def test_provider_protocols():
    sat: SatelliteProvider = MockSatelliteProvider()
    weather: WeatherProvider = MockWeatherProvider()
    currents: CurrentsProvider = MockCurrentsProvider()
    ais: AISProvider = MockAISProvider()
    # No exceptions means they satisfy the protocol signatures.
    assert sat.get_scene_metadata("x") is not None
    assert weather.get_wind("x") is not None
    assert currents.get_current("x") is not None
    assert ais.get_records("x") is not None
