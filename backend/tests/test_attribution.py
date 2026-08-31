from datetime import datetime, timezone
from shapely.geometry import Point
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.attribution import score_candidates

client = TestClient(app)


def test_score_candidates():
    vessel_summaries = [
        {
            "vessel_id": "V1",
            "distance_m": 100.0,
            "first_timestamp": "2022-01-01T00:10:00",
            "heading_variance_deg": 1.0,
        },
        {
            "vessel_id": "V2",
            "distance_m": 500.0,
            "first_timestamp": "2022-01-01T00:30:00",
            "heading_variance_deg": 10.0,
        }
    ]
    spill_origin = Point(0, 0)
    spill_time = datetime.fromisoformat("2022-01-01T00:00:00")
    
    scores = score_candidates(vessel_summaries, spill_origin, spill_time)
    assert len(scores) == 2
    assert scores[0]["vessel_id"] == "V1"
    assert scores[0]["overall_score"] > scores[1]["overall_score"]


def test_attribution_endpoint():
    payload = {
        "vessel_summaries": [
            {
                "vessel_id": "V1",
                "distance_m": 100.0,
                "first_timestamp": "2022-01-01T00:10:00",
                "heading_variance_deg": 1.0,
            },
            {
                "vessel_id": "V2",
                "distance_m": 500.0,
                "first_timestamp": "2022-01-01T00:30:00",
                "heading_variance_deg": 10.0,
            }
        ],
        "spill_origin": [0.0, 0.0],
        "spill_time": "2022-01-01T00:00:00",
        "weights": [0.35, 0.30, 0.20, 0.15]
    }
    response = client.post("/api/v1/attribution", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["vessel_id"] == "V1"


def test_attribution_endpoint_missing_first_timestamp_regression():
    """Regression test: vessel summaries without first_timestamp or with None must not raise 500."""
    payload = {
        "vessel_summaries": [
            {
                "vessel_id": "VESSEL_WITHOUT_TIMESTAMP",
                "distance_m": 250.0,
                "first_timestamp": None,
                "heading_variance_deg": 2.0,
            },
            {
                "vessel_id": "VESSEL_WITH_TIMESTAMP_UTC",
                "distance_m": 300.0,
                "timestamp_utc": "2026-08-29T10:05:00Z",
                "heading_variance_deg": 4.0,
            },
        ],
        "spill_origin": [125.0, 30.0],
        "spill_time": "2026-08-29T10:00:00Z",
        "weights": [0.35, 0.30, 0.20, 0.15]
    }
    response = client.post("/api/v1/attribution", json=payload)
    assert response.status_code == 200, f"Failed with: {response.text}"
    data = response.json()
    assert len(data) == 2
    for candidate in data:
        assert "overall_score" in candidate
        assert "explanations" in candidate


def test_attribution_sanchi_structure_with_iso_z():
    """Verify historical Sanchi vessel-summary structure with first_timestamp, last_timestamp, time_delta_s."""
    vessel_summaries = [
        {
            "vessel_id": "412345678",
            "vessel_name": "CF CRYSTAL",
            "first_timestamp": "2018-01-14T08:00:00Z",
            "last_timestamp": "2018-01-14T12:00:00Z",
            "distance_m": 1200.0,
            "time_delta_s": 14400.0,
            "average_speed_m_s": 6.2,
            "heading_variance_deg": 1.5,
        },
        {
            "vessel_id": "987654321",
            "vessel_name": "DISTANT VESSEL",
            "first_timestamp": "2018-01-14T02:00:00Z",
            "last_timestamp": "2018-01-14T04:00:00Z",
            "distance_m": 25000.0,
            "time_delta_s": 7200.0,
            "average_speed_m_s": 4.0,
            "heading_variance_deg": 8.5,
        }
    ]
    spill_origin = Point(125.5, 31.0)
    spill_time = datetime(2018, 1, 14, 8, 30, 0, tzinfo=timezone.utc)
    scores = score_candidates(vessel_summaries, spill_origin, spill_time, weights=(0.35, 0.30, 0.20, 0.15))

    assert len(scores) == 2
    assert scores[0]["vessel_id"] == "412345678"
    assert scores[0]["overall_score"] > scores[1]["overall_score"]
    assert scores[0]["spatial_proximity"] >= scores[1]["spatial_proximity"]
    assert scores[0]["temporal_proximity"] >= scores[1]["temporal_proximity"]
