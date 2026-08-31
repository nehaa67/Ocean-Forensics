from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def test_detection_endpoint():
    response = client.post("/api/v1/detection?mask_id=sample-oil-spill")
    assert response.status_code == 200
    data = response.json()
    assert data["detected"] is True
    assert data["confidence"] == 1.0
    assert data["mask_id"] == "sample-oil-spill"
    assert data["detection_mode"] == "prototype"
