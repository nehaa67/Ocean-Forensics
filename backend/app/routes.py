from fastapi import APIRouter, Body, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
import json
import os
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from pydantic import BaseModel
from rasterio.transform import Affine
from rasterio.crs import CRS
from rasterio.io import MemoryFile
from shapely.geometry import Point, shape

from backend.app.schemas.detection import DetectionResult
from backend.app.schemas.incident import (
    PredefinedIncidentSummary,
    PredefinedIncidentDetail,
    PredefinedIncidentRunRequest,
)
from backend.app.schemas.investigation_session import (
    InvestigationCreateRequest,
    InvestigationCreateResponse,
    InvestigationStatusResponse,
    InvestigationValidationResult,
    InvestigationRunRequest,
    InvestigationMode,
    FileStatus,
)
from backend.app.schemas.investigation import InvestigationResult
from backend.app.schemas.prevention import PreventionResult, PredictionRequest, RiskRequest
from backend.app.detection import detect_from_mask
from backend.app.geometry import calculate_geometry
from backend.app.drift import simulate_drift, _to_metric, _to_wgs84
from backend.app.ais import filter_ais, group_tracks, summarize_vessel
from backend.app.attribution import score_candidates
from backend.app.risk import calculate_forward_drift_and_risk
from backend.app.incidents import IncidentRegistry
from backend.app.services import InvestigationService, HistoricalInvestigationService
from backend.app.report_generator import generate_report

router = APIRouter()
incident_registry = IncidentRegistry()
investigation_service = InvestigationService()
historical_investigation_service = HistoricalInvestigationService(incident_registry)

DEMO_MAPPING = {
    "1.oil_spill_image.tif": {"mask_path": "data/demo/1.oil_spill_mask.tif", "case": "oil_spill"},
    "2.no_oil_image.tif": {"mask_path": "data/demo/2.no_oil_mask.tif", "case": "no_oil_spill"},
    "3.lookalike_image.tif": {"mask_path": "data/demo/3.lookalike_mask.tif", "case": "lookalike"},
}

# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------
@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ocean-forensics",
        "pipeline_status": "operational",
        "dependencies": {
            "torch": True,
            "rasterio": True,
            "xarray": True,
            "pyproj": True,
        },
    }


@router.post("/analyze-image")
async def analyze_demo_image(file: UploadFile = File(...)):
    """Legacy deterministic GeoTIFF demo retained for frontend demonstrations."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file has no filename.")
    filename = os.path.basename(file.filename)
    case_info = next((value for name, value in DEMO_MAPPING.items() if name.lower() == filename.lower()), None)
    if case_info is None:
        raise HTTPException(
            status_code=400,
            detail="Unsupported demo image. Use 1.oil_spill_image.tif, 2.no_oil_image.tif, or 3.lookalike_image.tif.",
        )

    try:
        with MemoryFile(await file.read()) as memfile:
            with memfile.open() as source:
                crs, transform = source.crs, source.transform
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse GeoTIFF metadata: {exc}") from exc
    if crs is None:
        raise HTTPException(status_code=400, detail="Uploaded GeoTIFF has no CRS metadata.")

    try:
        import rasterio
        with rasterio.open(case_info["mask_path"]) as source:
            mask = source.read(1)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read demo mask: {exc}") from exc

    geometry = calculate_geometry((mask > 0).astype(np.uint8), transform, crs)
    if not geometry["has_oil"]:
        return {
            "detected": False,
            "case": case_info["case"],
            "message": "No oil spill detected" if case_info["case"] == "no_oil_spill" else "Oil-like lookalike rejected",
        }

    centroid_lon, centroid_lat = geometry["centroid"]
    drift = simulate_drift(
        start_point=(centroid_lon, centroid_lat), duration_hours=3.0,
        timestep_seconds=900.0, current=(-0.1, -0.05), wind=(-5.0, -2.5),
        windage=0.03, direction="backward", crs=crs,
    )
    endpoint = drift["end_point"]
    origin = Point(endpoint["lon"], endpoint["lat"])
    search_area = _to_wgs84(_to_metric(origin, crs).buffer(5000), crs)
    try:
        with open("data/demo/ais.json", encoding="utf-8") as source:
            ais_records = json.load(source)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to read demo AIS records: {exc}") from exc

    start = datetime.fromisoformat("2022-01-01T00:00:00")
    end = datetime.fromisoformat("2022-01-01T02:00:00")
    tracks = group_tracks(filter_ais(ais_records, search_area, (start, end), crs))
    summaries = [summarize_vessel(track, origin, crs) for track in tracks.values()]
    candidates = score_candidates(summaries, origin, start, (0.25, 0.25, 0.25, 0.25))
    return {
        "detected": True,
        "case": case_info["case"],
        "geometry": {**geometry, "crs": crs.to_string()},
        "drift": drift,
        "environment": {
            "wind_m_s": {"u": -5.0, "v": -2.5},
            "current_m_s": {"u": -0.1, "v": -0.05},
            "windage": 0.03,
            "source": "deterministic_demo_input",
        },
        "candidates": candidates,
    }


@router.post("/report/generate")
def generate_investigation_report():
    """Generate and download the Ocean Forensics PDF investigation report."""
    pdf_path = generate_report()
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=pdf_path.name,
    )

# ---------------------------------------------------------------------------
# Predefined Historical Incidents API
# ---------------------------------------------------------------------------
@router.get("/incidents", response_model=List[PredefinedIncidentSummary])
def list_incidents():
    """List all available predefined historical incidents (e.g. Sanchi 2018)."""
    return incident_registry.list_incidents()

@router.get("/incidents/{incident_id}", response_model=PredefinedIncidentDetail)
def get_incident(incident_id: str):
    """Get metadata and dataset presence status for a predefined incident."""
    incident = incident_registry.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Incident '{incident_id}' not found")
    return incident

@router.post("/incidents/{incident_id}/run", response_model=InvestigationResult)
def run_predefined_incident(
    incident_id: str,
    req: Optional[PredefinedIncidentRunRequest] = Body(default_factory=PredefinedIncidentRunRequest),
):
    """Trigger end-to-end forensic investigation run on a predefined historical incident."""
    force_recompute = req.force_recompute if req else False
    config = req.configuration if req else {}
    return historical_investigation_service.run_investigation(
        incident_id=incident_id,
        force_recompute=force_recompute,
        config=config,
    )

# ---------------------------------------------------------------------------
# New Uploaded Investigation API
# ---------------------------------------------------------------------------
@router.post("/investigations", response_model=InvestigationCreateResponse)
def create_investigation(req: InvestigationCreateRequest = Body(default_factory=InvestigationCreateRequest)):
    """Create a new isolated investigation workspace."""
    return investigation_service.create_investigation(req)

@router.post("/investigations/{analysis_id}/files/sentinel", response_model=FileStatus)
async def upload_sentinel_file(analysis_id: str, file: UploadFile = File(...)):
    """Upload Sentinel-1 SAR dataset (SAFE zip archive, GeoTIFF, etc.) with disk-backed streaming."""
    return await investigation_service.save_file_stream(analysis_id, "sentinel", file)

@router.post("/investigations/{analysis_id}/files/wind", response_model=FileStatus)
async def upload_wind_file(analysis_id: str, file: UploadFile = File(...)):
    """Upload wind dataset (NetCDF, CSV, or JSON)."""
    return await investigation_service.save_file_stream(analysis_id, "wind", file)

@router.post("/investigations/{analysis_id}/files/current", response_model=FileStatus)
async def upload_current_file(analysis_id: str, file: UploadFile = File(...)):
    """Upload ocean current dataset (NetCDF, CSV, or JSON)."""
    return await investigation_service.save_file_stream(analysis_id, "current", file)

@router.post("/investigations/{analysis_id}/files/ais", response_model=FileStatus)
async def upload_ais_file(analysis_id: str, file: UploadFile = File(...)):
    """Upload AIS vessel tracking records (CSV or JSON)."""
    return await investigation_service.save_file_stream(analysis_id, "ais", file)

@router.post("/investigations/{analysis_id}/validate", response_model=InvestigationValidationResult)
def validate_investigation_endpoint(
    analysis_id: str,
    mode: Optional[InvestigationMode] = Query(default=None),
):
    """Validate whether the uploaded investigation has sufficient data for the target mode."""
    return investigation_service.validate_investigation(analysis_id, mode)

@router.get("/investigations/{analysis_id}/status", response_model=InvestigationStatusResponse)
def get_investigation_status_endpoint(analysis_id: str):
    """Get the current file status and validation readiness of an investigation."""
    return investigation_service.get_status(analysis_id)

@router.post("/investigations/{analysis_id}/run")
def run_uploaded_investigation(
    analysis_id: str,
    req: InvestigationRunRequest = Body(default_factory=InvestigationRunRequest),
):
    """Trigger backend forensic analysis on an uploaded investigation."""
    return investigation_service.run_investigation(analysis_id, req)

# ---------------------------------------------------------------------------
# Prevention & Early-Warning Risk Assessment API
# ---------------------------------------------------------------------------
@router.post("/prediction", response_model=PreventionResult)
def run_prediction_endpoint(req: PredictionRequest = Body(default_factory=PredictionRequest)):
    """Run forward drift trajectory forecasting, predicted impact zone, and AIS risk assessment."""
    out_dir = None
    spill_pt = req.spill_centroid or (125.2, 29.5)
    spill_area = req.spill_area_km2 or 5.0
    wind = req.wind_vector or (3.0, -4.0)
    current = req.current_vector or (0.2, 0.4)
    ais_recs = req.ais_records or []
    obs_time = datetime.now(timezone.utc).isoformat()
    analysis_id = req.analysis_id or "PREV-LIVE"

    if req.analysis_id:
        try:
            inv_dir = investigation_service.storage_root / req.analysis_id
            if inv_dir.is_dir():
                out_dir = inv_dir / "outputs"
        except Exception:
            pass

    return calculate_forward_drift_and_risk(
        spill_centroid=spill_pt,
        spill_area_km2=spill_area,
        observation_time_iso=obs_time,
        wind_vector=wind,
        current_vector=current,
        ais_records=ais_recs,
        output_dir=out_dir,
        analysis_id=analysis_id,
        forecast_hours=req.forecast_hours,
        timestep_seconds=req.timestep_seconds,
        windage=req.windage,
        warning_distance_km=req.warning_distance_km,
        high_risk_distance_km=req.high_risk_distance_km,
    )

@router.post("/risk", response_model=PreventionResult)
def run_risk_endpoint(req: RiskRequest = Body(default_factory=RiskRequest)):
    """Evaluate at-risk vessels within the forward forecast warning corridor."""
    pred_req = PredictionRequest(
        analysis_id=req.analysis_id,
        forecast_hours=req.forecast_hours,
        warning_distance_km=req.warning_distance_km,
    )
    return run_prediction_endpoint(pred_req)

# ---------------------------------------------------------------------------
# Prototype Detection & Processing Endpoints (Preserved)
# ---------------------------------------------------------------------------
@router.post("/detection", response_model=DetectionResult)
def run_detection(mask_id: str):
    """Prototype detection endpoint."""
    return detect_from_mask(mask_id=mask_id)

# Request models (Preserved for compatibility)
class GeometryRequest(BaseModel):
    mask: List[List[int]]
    transform: Tuple[float, float, float, float, float, float]
    crs_epsg: int

class DriftRequest(BaseModel):
    start_lon: float
    start_lat: float
    duration_hours: float
    timestep_seconds: float
    current: Tuple[float, float]
    wind: Tuple[float, float]
    windage: float = 0.03
    direction: str = "forward"
    crs_epsg: int = 4326

class AISRequest(BaseModel):
    records: List[Dict[str, Any]]
    area_geojson: Dict[str, Any]
    time_window: Tuple[str, str]
    crs_epsg: int = 4326

class AttributionRequest(BaseModel):
    vessel_summaries: List[Dict[str, Any]]
    spill_origin: Tuple[float, float]
    spill_time: str
    weights: Tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25)

class InvestigationRequest(BaseModel):
    mask: List[List[int]]
    transform: Tuple[float, float, float, float, float, float]
    crs_epsg: int
    wind: Tuple[float, float]
    current: Tuple[float, float]
    windage: float = 0.03
    duration_hours: float = 1.0
    timestep_seconds: float = 600.0
    ais_records: List[Dict[str, Any]]
    time_window: Tuple[str, str]
    weights: Tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25)

# Endpoints
@router.post("/geometry")
def geometry_endpoint(req: GeometryRequest):
    mask = np.array(req.mask, dtype=np.uint8)
    affine = Affine(*req.transform)
    crs = CRS.from_epsg(req.crs_epsg)
    return calculate_geometry(mask, affine, crs)

@router.post("/drift")
def drift_endpoint(req: DriftRequest):
    start = (req.start_lon, req.start_lat)
    crs = CRS.from_epsg(req.crs_epsg)
    return simulate_drift(start, req.duration_hours, req.timestep_seconds, req.current, req.wind, req.windage, req.direction, crs)

@router.post("/ais")
def ais_endpoint(req: AISRequest):
    crs = CRS.from_epsg(req.crs_epsg)
    area = shape(req.area_geojson)
    start_str, end_str = req.time_window
    start_dt = datetime.fromisoformat(start_str)
    end_dt = datetime.fromisoformat(end_str)
    filtered = filter_ais(req.records, area, (start_dt, end_dt), crs)
    tracks = group_tracks(filtered)
    summaries = []
    for vid, track in tracks.items():
        summaries.append(summarize_vessel(track, area.centroid, crs))
    return summaries

@router.post("/attribution")
def attribution_endpoint(req: AttributionRequest):
    origin = Point(req.spill_origin[0], req.spill_origin[1])
    raw_time = req.spill_time.strip()
    if raw_time.endswith("Z"):
        raw_time = raw_time[:-1] + "+00:00"
    spill_time = datetime.fromisoformat(raw_time)
    return score_candidates(req.vessel_summaries, origin, spill_time, req.weights)

@router.post("/investigation")
def investigation_endpoint(req: InvestigationRequest):
    # Geometry
    mask = np.array(req.mask, dtype=np.uint8)
    affine = Affine(*req.transform)
    crs = CRS.from_epsg(req.crs_epsg)
    geom = calculate_geometry(mask, affine, crs)
    if not geom["has_oil"]:
        return {"error": "No oil detected"}
    # Centroid
    centroid_lon, centroid_lat = geom["centroid"]
    # Drift hindcast to estimate origin point
    drift = simulate_drift((centroid_lon, centroid_lat), req.duration_hours, req.timestep_seconds, req.current, req.wind, req.windage, direction="backward", crs=crs)
    origin_pt = drift["end_point"]
    origin_point = Point(origin_pt["lon"], origin_pt["lat"])
    # Buffer 5000m around origin (metric CRS)
    metric_origin = _to_metric(origin_point, crs)
    buffer_metric = metric_origin.buffer(5000)
    search_area = _to_wgs84(buffer_metric, crs)
    # AIS filtering
    start_str, end_str = req.time_window
    start_dt = datetime.fromisoformat(start_str)
    end_dt = datetime.fromisoformat(end_str)
    filtered = filter_ais(req.ais_records, search_area, (start_dt, end_dt), crs)
    tracks = group_tracks(filtered)
    vessel_summaries = [summarize_vessel(tracks[vid], origin_point, crs) for vid in tracks]
    # Attribution
    spill_time = start_dt
    candidates = score_candidates(vessel_summaries, origin_point, spill_time, req.weights)
    return {"geometry": geom, "drift": drift, "candidates": candidates}
