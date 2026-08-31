import json
from shapely.geometry import Point
# pyrefly: ignore [missing-import]
from rasterio.crs import CRS
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.ais import summarize_vessel

client = TestClient(app)

def test_summarize_vessel_synthetic_fallback():
    # Synthetic/projected style data but using geographic CRS
    track = [
        {
            "vessel_id": "V1",
            "latitude": 1998.0,
            "longitude": -1010.0,
            "timestamp": "2022-01-01T00:10:00",
            "speed": 5.0,
            "heading": 90
        },
        {
            "vessel_id": "V1",
            "latitude": 1998.0,
            "longitude": -1005.0,
            "timestamp": "2022-01-01T00:20:00",
            "speed": 5.0,
            "heading": 90
        }
    ]
    crs = CRS.from_epsg(4326) # Geographic CRS
    origin = Point(0.0, 2000.0) # Centroid of area
    
    # Run the function
    summary = summarize_vessel(track, origin, crs)
    
    # Assertions
    assert summary["vessel_id"] == "V1"
    assert summary["distance_m"] > 0
    # Make sure distance is finite (not NaN or Inf)
    import math
    assert math.isfinite(summary["distance_m"])
    # Expected distance from Point(-1010, 1998) to Point(0, 2000) is Euclidean:
    # sqrt( (-1010 - 0)^2 + (1998 - 2000)^2 ) = sqrt(1020100 + 4) = 1010.00198...
    assert abs(summary["distance_m"] - 1010.00198) < 1e-4

def test_ais_endpoint_synthetic_payload():
    payload = {
        "records": [
            {
                "vessel_id": "V1",
                "latitude": 1998.0,
                "longitude": -1010.0,
                "timestamp": "2022-01-01T00:10:00",
                "speed": 5.0,
                "heading": 90
            },
            {
                "vessel_id": "V2",
                "latitude": 2100.0,
                "longitude": 1100.0,
                "timestamp": "2022-01-01T00:15:00",
                "speed": 5.0,
                "heading": 90
            }
        ],
        "area_geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-2000, 1000],
                    [2000, 1000],
                    [2000, 3000],
                    [-2000, 3000],
                    [-2000, 1000]
                ]
            ]
        },
        "time_window": [
            "2022-01-01T00:00:00",
            "2022-01-01T01:00:00"
        ],
        "crs_epsg": 4326
    }
    
    # Send request to endpoint
    resp = client.post("/api/v1/ais", json=payload)
    assert resp.status_code == 200, f"Failed with: {resp.text}"
    
    data = resp.json()
    assert len(data) == 2
    
    # Verify both summaries have finite float values
    import math
    for summary in data:
        assert math.isfinite(summary["distance_m"])
        assert summary["distance_m"] > 0


def test_ais_endpoint_with_timestamp_utc_and_timezone_support():
    """Regression test: verify POST /api/v1/ais with timestamp_utc and ISO-8601 UTC Z timestamps."""
    payload = {
        "records": [
            {
                "vessel_id": "VESSEL_A",
                "vessel_name": "Explorer",
                "latitude": 30.05,
                "longitude": 125.10,
                "timestamp_utc": "2026-08-29T10:15:00Z",
                "speed": 12.0,
                "heading": 45.0,
            },
            {
                "vessel_id": "VESSEL_B",
                "vessel_name": "Navigator",
                "latitude": 30.08,
                "longitude": 125.12,
                "timestamp_utc": "2026-08-29T10:25:00Z",
                "speed": 10.5,
                "heading": 180.0,
            },
            {
                "vessel_id": "VESSEL_INVALID_TIME",
                "latitude": 30.08,
                "longitude": 125.12,
                # Missing both timestamp and timestamp_utc -> safely ignored
            },
        ],
        "area_geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [125.0, 30.0],
                    [125.3, 30.0],
                    [125.3, 30.2],
                    [125.0, 30.2],
                    [125.0, 30.0],
                ]
            ],
        },
        "time_window": [
            "2026-08-29T10:00:00Z",
            "2026-08-29T11:00:00Z",
        ],
        "crs_epsg": 4326,
    }

    resp = client.post("/api/v1/ais", json=payload)
    assert resp.status_code == 200, f"Failed with: {resp.text}"

    data = resp.json()
    assert len(data) == 2
    vids = {s["vessel_id"] for s in data}
    assert "VESSEL_A" in vids
    assert "VESSEL_B" in vids

