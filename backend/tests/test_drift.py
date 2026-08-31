import pytest
from backend.app.drift import simulate_drift
from rasterio.crs import CRS

def test_simulate_drift_forward():
    # metric coordinates (EPSG:3857)
    start = (1000.0, 2000.0)
    duration = 1.0  # hour
    timestep = 3600.0  # one step
    current = (0.5, 0.0)  # m/s east
    wind = (2.0, 0.0)    # m/s east
    crs = CRS.from_epsg(3857)
    result = simulate_drift(start, duration, timestep, current, wind, windage=0.03, direction="forward", crs=crs)
    # effective velocity = 0.5 + 2*0.03 = 0.56 m/s
    expected_dx = 0.56 * 3600
    assert abs(result["end_point"]["lon"] - (start[0] + expected_dx)) < 1e-3
    assert result["direction"] == "forward"
