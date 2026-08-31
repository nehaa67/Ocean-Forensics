from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.incidents import IncidentRegistry

client = TestClient(app)


def test_incident_registry_discovers_sanchi():
    registry = IncidentRegistry()
    incidents = registry.list_incidents()
    assert len(incidents) >= 1
    sanchi = next((inc for inc in incidents if inc.incident_id == "sanchi_20180120"), None)
    assert sanchi is not None
    assert sanchi.name == "Sanchi"
    assert sanchi.observation_time == "2018-01-20T09:28:53Z"


def test_incident_registry_get_sanchi_details():
    registry = IncidentRegistry()
    detail = registry.get_incident("sanchi_20180120")
    assert detail is not None
    assert detail.incident_id == "sanchi_20180120"
    assert "East China Sea" in detail.location.get("region", "")
    assert "sentinel" in detail.expected_files
    assert detail.expected_files["sentinel"].endswith(".SAFE")
    assert "wind" in detail.expected_files
    assert "current" in detail.expected_files
    assert "ais" in detail.expected_files
    assert detail.model_available is True
    assert detail.pipeline_readiness == "ready"


def test_api_list_incidents():
    response = client.get("/api/v1/incidents")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(item["incident_id"] == "sanchi_20180120" for item in data)


def test_api_get_incident_detail():
    response = client.get("/api/v1/incidents/sanchi_20180120")
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "sanchi_20180120"
    assert data["name"] == "Sanchi"
    assert "location" in data
    assert "outputs_available" in data
    assert data["pipeline_readiness"] == "ready"


def test_api_get_nonexistent_incident():
    response = client.get("/api/v1/incidents/non_existent_999")
    assert response.status_code == 404


def test_api_run_predefined_incident():
    payload = {"incident_id": "sanchi_20180120", "mode": "investigation"}
    response = client.post("/api/v1/incidents/sanchi_20180120/run", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["incident_id"] == "sanchi_20180120"
    assert data["status"] == "completed"
    assert data["detection"]["detected"] is True
    assert data["geometry"]["area_m2"] > 0
    assert data["source_zone"]["estimated_origin"] is not None
    assert len(data["candidates"]) >= 1
    assert any("sparse historical AIS coverage" in w for w in data["quality_warnings"])
