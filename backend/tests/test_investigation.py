import json
import numpy as np
from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)

def load_synthetic():
    mask = np.load('data/sample/mask.npy')
    mask_list = mask.tolist()
    with open('data/sample/metadata.json') as f:
        meta = json.load(f)
    with open('data/sample/environment.json') as f:
        env = json.load(f)
    with open('data/sample/ais.json') as f:
        ais = json.load(f)
    return mask_list, meta, env, ais

def test_investigation_pipeline():
    mask, meta, env, ais = load_synthetic()
    payload = {
        "mask": mask,
        "transform": tuple(meta["transform"]),
        "crs_epsg": meta["crs_epsg"],
        "wind": tuple(env["wind"]),
        "current": tuple(env["current"]),
        "windage": env.get("windage", 0.03),
        "duration_hours": 1.0,
        "timestep_seconds": 600.0,
        "ais_records": ais,
        "time_window": ("2022-01-01T00:00:00", "2022-01-01T02:00:00"),
        "weights": (0.25, 0.25, 0.25, 0.25)
    }
    resp = client.post("/api/v1/investigation", json=payload)
    assert resp.status_code == 200, f"Status {resp.status_code}: {resp.text}"
    data = resp.json()
    # Verify geometry detection
    assert data["geometry"]["has_oil"] is True
    # Verify that candidate V1 is ranked highest (closest to origin)
    candidates = data["candidates"]
    assert candidates, "No candidates returned"
    top = candidates[0]
    assert top["vessel_id"] == "V1", f"Top candidate {top['vessel_id']} not expected"
