import io
import zipfile
from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.investigation_service import InvestigationService
from backend.app.schemas.investigation_session import InvestigationCreateRequest, InvestigationMode

client = TestClient(app)


def test_create_uploaded_investigation(tmp_path):
    service = InvestigationService(storage_root=tmp_path)
    req = InvestigationCreateRequest(mode=InvestigationMode.INVESTIGATION, title="Test Case")
    res = service.create_investigation(req)

    assert res.analysis_id.startswith("INV-")
    assert res.status.value == "created"
    assert res.mode == InvestigationMode.INVESTIGATION

    # Check directory structure was created
    inv_dir = tmp_path / res.analysis_id
    assert inv_dir.is_dir()
    assert (inv_dir / "raw" / "sentinel").is_dir()
    assert (inv_dir / "raw" / "wind").is_dir()
    assert (inv_dir / "raw" / "currents").is_dir()
    assert (inv_dir / "raw" / "ais").is_dir()
    assert (inv_dir / "session.json").exists()


def test_file_isolation_between_investigations(tmp_path):
    service = InvestigationService(storage_root=tmp_path)
    res1 = service.create_investigation(InvestigationCreateRequest())
    res2 = service.create_investigation(InvestigationCreateRequest())

    assert res1.analysis_id != res2.analysis_id

    dir1 = tmp_path / res1.analysis_id
    dir2 = tmp_path / res2.analysis_id

    assert dir1.exists() and dir2.exists()
    assert dir1 != dir2


def test_api_create_and_status_investigation():
    create_resp = client.post("/api/v1/investigations", json={"mode": "investigation", "title": "API Test"})
    assert create_resp.status_code == 200
    create_data = create_resp.json()
    analysis_id = create_data["analysis_id"]

    status_resp = client.get(f"/api/v1/investigations/{analysis_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["analysis_id"] == analysis_id
    assert status_data["status"] == "created"
    assert status_data["files"]["sentinel"]["uploaded"] is False


def test_api_upload_sentinel_geotiff():
    create_resp = client.post("/api/v1/investigations", json={"mode": "investigation"})
    analysis_id = create_resp.json()["analysis_id"]

    dummy_tiff = b"II*\x00\x08\x00\x00\x00" + b"\x00" * 100
    files = {"file": ("test_vv.tif", io.BytesIO(dummy_tiff), "image/tiff")}

    upload_resp = client.post(f"/api/v1/investigations/{analysis_id}/files/sentinel", files=files)
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["uploaded"] is True
    assert upload_data["valid"] is True
    assert upload_data["format"] == "GeoTIFF"
    assert upload_data["size_bytes"] == len(dummy_tiff)


def test_api_upload_sentinel_safe_zip_safe_extraction():
    create_resp = client.post("/api/v1/investigations", json={"mode": "investigation"})
    analysis_id = create_resp.json()["analysis_id"]

    # Create dummy in-memory zip archive
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("S1_TEST.SAFE/manifest.safe", "<xml>manifest</xml>")
        zf.writestr("S1_TEST.SAFE/measurement/vv.tiff", b"TIFF_DATA")
    zip_buffer.seek(0)

    files = {"file": ("S1_TEST.SAFE.zip", zip_buffer, "application/zip")}
    upload_resp = client.post(f"/api/v1/investigations/{analysis_id}/files/sentinel", files=files)
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["uploaded"] is True
    assert upload_data["valid"] is True
    assert upload_data["format"] == "SAFE_ARCHIVE"


def test_api_upload_large_stream_simulation():
    # Simulate a 3MB multi-chunk file upload streamed to disk
    create_resp = client.post("/api/v1/investigations", json={"mode": "investigation"})
    analysis_id = create_resp.json()["analysis_id"]

    payload_size = 3 * 1024 * 1024  # 3 MB
    large_payload = b"X" * payload_size
    files = {"file": ("large_sentinel_vv.tif", io.BytesIO(large_payload), "image/tiff")}

    upload_resp = client.post(f"/api/v1/investigations/{analysis_id}/files/sentinel", files=files)
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["uploaded"] is True
    assert upload_data["valid"] is True
    assert upload_data["size_bytes"] == payload_size


def test_api_upload_invalid_file_rejection():
    create_resp = client.post("/api/v1/investigations", json={"mode": "investigation"})
    analysis_id = create_resp.json()["analysis_id"]

    files = {"file": ("malicious.exe", io.BytesIO(b"MZ\x00\x00"), "application/x-msdownload")}
    upload_resp = client.post(f"/api/v1/investigations/{analysis_id}/files/sentinel", files=files)
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["uploaded"] is True
    assert upload_data["valid"] is False
    assert "Unsupported file format" in upload_data["error"]


def test_path_traversal_zip_slip_rejection():
    create_resp = client.post("/api/v1/investigations", json={"mode": "investigation"})
    analysis_id = create_resp.json()["analysis_id"]

    # Create malicious zip with ../ traversal
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("../../evil.txt", "escaped content")
    zip_buffer.seek(0)

    files = {"file": ("evil.zip", zip_buffer, "application/zip")}
    upload_resp = client.post(f"/api/v1/investigations/{analysis_id}/files/sentinel", files=files)
    assert upload_resp.status_code == 200
    upload_data = upload_resp.json()
    assert upload_data["valid"] is False
    assert "ZIP extraction failed" in upload_data["error"]


def test_mode_validation_and_missing_data_detection():
    create_resp = client.post("/api/v1/investigations", json={"mode": "investigation"})
    analysis_id = create_resp.json()["analysis_id"]

    # 1. Without Sentinel, validation fails
    val_resp = client.post(f"/api/v1/investigations/{analysis_id}/validate")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["is_valid"] is False
    assert any("Sentinel-1 SAR dataset is required" in err for err in val_data["errors"])

    # 2. Upload valid Sentinel GeoTIFF
    dummy_tiff = b"TIFF_HEADER"
    client.post(
        f"/api/v1/investigations/{analysis_id}/files/sentinel",
        files={"file": ("test.tif", io.BytesIO(dummy_tiff), "image/tiff")},
    )

    # 3. Validation should now pass with warnings about missing optional AIS/wind/current
    val_resp2 = client.post(f"/api/v1/investigations/{analysis_id}/validate")
    assert val_resp2.status_code == 200
    val_data2 = val_resp2.json()
    assert val_data2["is_valid"] is True
    assert len(val_data2["warnings"]) > 0

    # 4. Status should now be ready
    status_resp = client.get(f"/api/v1/investigations/{analysis_id}/status")
    assert status_resp.json()["status"] == "ready"


def test_prevention_mode_validation():
    create_resp = client.post("/api/v1/investigations", json={"mode": "prevention"})
    analysis_id = create_resp.json()["analysis_id"]

    # Upload valid Sentinel
    client.post(
        f"/api/v1/investigations/{analysis_id}/files/sentinel",
        files={"file": ("test.tif", io.BytesIO(b"TIFF"), "image/tiff")},
    )

    val_resp = client.post(f"/api/v1/investigations/{analysis_id}/validate?mode=prevention")
    assert val_resp.status_code == 200
    val_data = val_resp.json()
    assert val_data["is_valid"] is True
    assert val_data["mode"] == "prevention"
    assert any("forecast" in w for w in val_data["warnings"])


def test_run_investigation_readiness_enforcement():
    # Attempting to run unready investigation should return 400
    create_resp = client.post("/api/v1/investigations", json={"mode": "investigation"})
    analysis_id = create_resp.json()["analysis_id"]

    run_resp = client.post(f"/api/v1/investigations/{analysis_id}/run", json={})
    assert run_resp.status_code == 400

    # Once Sentinel is uploaded, running succeeds
    client.post(
        f"/api/v1/investigations/{analysis_id}/files/sentinel",
        files={"file": ("test.tif", io.BytesIO(b"TIFF"), "image/tiff")},
    )

    run_resp2 = client.post(f"/api/v1/investigations/{analysis_id}/run", json={})
    assert run_resp2.status_code == 200
    assert run_resp2.json()["status"] == "ready_for_processing"
