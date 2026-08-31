from __future__ import annotations

import json
import os
import re
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from fastapi import UploadFile, HTTPException

from backend.app.schemas.investigation_session import (
    InvestigationSourceType,
    InvestigationMode,
    InvestigationStatus,
    FileStatus,
    InvestigationFilesStatus,
    InvestigationCreateRequest,
    InvestigationCreateResponse,
    InvestigationValidationResult,
    InvestigationStatusResponse,
    InvestigationRunRequest,
)


CHUNK_SIZE = 1024 * 1024  # 1 MB disk-backed stream buffer


class InvestigationService:
    """Service managing uploaded investigations, file storage isolation, and data validation."""

    def __init__(self, storage_root: Optional[Path] = None) -> None:
        if storage_root is not None:
            self._storage_root = Path(storage_root)
        else:
            env_root = os.environ.get("INVESTIGATION_STORAGE_ROOT")
            if env_root:
                self._storage_root = Path(env_root)
            else:
                base_candidates = [
                    Path(__file__).resolve().parents[3] / "data" / "investigations",
                    Path("data/investigations").resolve(),
                ]
                self._storage_root = next((c for c in base_candidates if c.exists()), base_candidates[0])
        self._storage_root.mkdir(parents=True, exist_ok=True)

    @property
    def storage_root(self) -> Path:
        return self._storage_root

    def _get_investigation_dir(self, analysis_id: str) -> Path:
        # Enforce strict alphanumeric + hyphen analysis_id format to prevent directory traversal
        if not re.match(r"^[A-Za-z0-9_-]+$", analysis_id):
            raise HTTPException(status_code=400, detail="Invalid analysis_id format")
        inv_dir = self._storage_root / analysis_id
        if not inv_dir.is_dir():
            raise HTTPException(status_code=404, detail=f"Investigation '{analysis_id}' not found")
        return inv_dir

    def _get_session_file(self, analysis_id: str) -> Path:
        return self._get_investigation_dir(analysis_id) / "session.json"

    def _read_session(self, analysis_id: str) -> Dict[str, Any]:
        session_file = self._get_session_file(analysis_id)
        if not session_file.exists():
            raise HTTPException(status_code=404, detail="Investigation session metadata missing")
        with session_file.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _write_session(self, analysis_id: str, session: Dict[str, Any]) -> None:
        session_file = self._get_session_file(analysis_id)
        with session_file.open("w", encoding="utf-8") as f:
            json.dump(session, f, indent=2)

    def create_investigation(self, req: InvestigationCreateRequest) -> InvestigationCreateResponse:
        """Create a new isolated investigation workspace and directory structure."""
        unique_token = uuid.uuid4().hex[:8].upper()
        analysis_id = f"INV-{unique_token}"
        inv_dir = self._storage_root / analysis_id

        # Isolated directory tree
        (inv_dir / "raw" / "sentinel").mkdir(parents=True, exist_ok=True)
        (inv_dir / "raw" / "wind").mkdir(parents=True, exist_ok=True)
        (inv_dir / "raw" / "currents").mkdir(parents=True, exist_ok=True)
        (inv_dir / "raw" / "ais").mkdir(parents=True, exist_ok=True)
        (inv_dir / "processed").mkdir(parents=True, exist_ok=True)
        (inv_dir / "outputs").mkdir(parents=True, exist_ok=True)

        now_iso = datetime.now(timezone.utc).isoformat()
        session_data: Dict[str, Any] = {
            "analysis_id": analysis_id,
            "status": InvestigationStatus.CREATED.value,
            "source_type": InvestigationSourceType.UPLOADED_DATASET.value,
            "mode": req.mode.value,
            "title": req.title,
            "description": req.description,
            "created_at": now_iso,
            "updated_at": now_iso,
            "files": {
                "sentinel": {"uploaded": False, "valid": False, "filename": None, "size_bytes": 0},
                "wind": {"uploaded": False, "valid": False, "filename": None, "size_bytes": 0},
                "current": {"uploaded": False, "valid": False, "filename": None, "size_bytes": 0},
                "ais": {"uploaded": False, "valid": False, "filename": None, "size_bytes": 0},
            },
            "warnings": [],
            "errors": [],
        }

        with (inv_dir / "session.json").open("w", encoding="utf-8") as f:
            json.dump(session_data, f, indent=2)

        return InvestigationCreateResponse(
            analysis_id=analysis_id,
            status=InvestigationStatus.CREATED,
            created_at=now_iso,
            mode=req.mode,
        )

    async def save_file_stream(
        self,
        analysis_id: str,
        category: str,
        upload_file: UploadFile,
    ) -> FileStatus:
        """Stream upload directly to disk in chunks to prevent loading large files into RAM."""
        inv_dir = self._get_investigation_dir(analysis_id)
        raw_category_dir = inv_dir / "raw" / (category if category != "current" else "currents")
        raw_category_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename against path traversal
        raw_filename = upload_file.filename or f"upload_{category}"
        clean_filename = Path(raw_filename).name
        if not clean_filename or clean_filename.startswith(".") or ".." in clean_filename:
            clean_filename = f"dataset_{category}"

        dest_path = raw_category_dir / clean_filename

        total_bytes = 0
        with dest_path.open("wb") as dest_file:
            while True:
                chunk = await upload_file.read(CHUNK_SIZE)
                if not chunk:
                    break
                dest_file.write(chunk)
                total_bytes += len(chunk)

        # Handle zip archives for Sentinel-1 SAFE products safely
        detected_format = self._detect_format(clean_filename)
        validation_error = None
        is_valid = True

        if clean_filename.lower().endswith(".zip") and category == "sentinel":
            try:
                self._safe_extract_zip(dest_path, raw_category_dir)
                detected_format = "SAFE_ARCHIVE"
            except Exception as e:
                is_valid = False
                validation_error = f"ZIP extraction failed: {str(e)}"
        elif not self._validate_category_format(category, clean_filename):
            is_valid = False
            validation_error = f"Unsupported file format for {category}: '{clean_filename}'"

        file_status = FileStatus(
            uploaded=True,
            valid=is_valid,
            filename=clean_filename,
            size_bytes=total_bytes,
            format=detected_format,
            error=validation_error,
        )

        # Update session
        session = self._read_session(analysis_id)
        session["files"][category] = file_status.model_dump()
        session["status"] = InvestigationStatus.UPLOADING.value
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_session(analysis_id, session)

        return file_status

    def _safe_extract_zip(self, zip_path: Path, target_dir: Path) -> None:
        """Safely extract ZIP archives guarding against Zip Slip path traversal vulnerabilities."""
        target_dir_resolved = target_dir.resolve()
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                member_path = Path(member.filename)
                # Reject absolute paths or paths with '..'
                if member_path.is_absolute() or ".." in member.filename.split("/"):
                    raise ValueError(f"Malicious zip entry detected: {member.filename}")
                destination = (target_dir / member.filename).resolve()
                if not str(destination).startswith(str(target_dir_resolved)):
                    raise ValueError(f"Zip extraction path escape detected: {member.filename}")
            zf.extractall(target_dir)

    def _detect_format(self, filename: str) -> str:
        lower = filename.lower()
        if lower.endswith(".safe.zip") or lower.endswith(".zip"):
            return "ZIP"
        if lower.endswith(".tif") or lower.endswith(".tiff"):
            return "GeoTIFF"
        if lower.endswith(".nc") or lower.endswith(".nc4"):
            return "NetCDF"
        if lower.endswith(".csv"):
            return "CSV"
        if lower.endswith(".json"):
            return "JSON"
        return "UNKNOWN"

    def _validate_category_format(self, category: str, filename: str) -> bool:
        lower = filename.lower()
        if category == "sentinel":
            return any(lower.endswith(ext) for ext in [".zip", ".tif", ".tiff", ".safe", ".tar.gz", ".tar"])
        if category in {"wind", "current"}:
            return any(lower.endswith(ext) for ext in [".nc", ".nc4", ".csv", ".json"])
        if category == "ais":
            return any(lower.endswith(ext) for ext in [".csv", ".json"])
        return False

    def validate_investigation(
        self,
        analysis_id: str,
        mode: Optional[InvestigationMode] = None,
    ) -> InvestigationValidationResult:
        """Validate whether the investigation meets minimum data requirements for execution."""
        session = self._read_session(analysis_id)
        effective_mode = mode or InvestigationMode(session.get("mode", InvestigationMode.INVESTIGATION.value))

        files_data = session.get("files", {})
        sentinel_info = files_data.get("sentinel", {})
        wind_info = files_data.get("wind", {})
        current_info = files_data.get("current", {})
        ais_info = files_data.get("ais", {})

        warnings: List[str] = []
        errors: List[str] = []

        # 1. Sentinel-1 is strictly REQUIRED
        if not sentinel_info.get("uploaded"):
            errors.append("Sentinel-1 SAR dataset is required but has not been uploaded.")
        elif not sentinel_info.get("valid"):
            errors.append(f"Uploaded Sentinel-1 dataset is invalid: {sentinel_info.get('error', 'unknown error')}")

        # 2. Mode specific validations
        if effective_mode == InvestigationMode.INVESTIGATION:
            if not wind_info.get("uploaded"):
                warnings.append("No wind data uploaded: backward drift hindcast will assume calm conditions.")
            if not current_info.get("uploaded"):
                warnings.append("No ocean current data uploaded: hydrodynamic drift will assume zero velocity.")
            if not ais_info.get("uploaded"):
                warnings.append("No AIS traffic uploaded: vessel attribution scoring cannot be performed.")
        elif effective_mode == InvestigationMode.PREVENTION:
            if not wind_info.get("uploaded"):
                warnings.append("No forecast wind data uploaded: forward trajectory forecasting will be limited.")
            if not current_info.get("uploaded"):
                warnings.append("No forecast current data uploaded: forward drift will assume zero current.")
            if not ais_info.get("uploaded"):
                warnings.append("No real-time AIS traffic uploaded: vessel collision/spill risk analysis unavailable.")

        is_valid = len(errors) == 0

        # Update session status
        if is_valid:
            session["status"] = InvestigationStatus.READY.value
        else:
            session["status"] = InvestigationStatus.CREATED.value
        session["warnings"] = warnings
        session["errors"] = errors
        session["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._write_session(analysis_id, session)

        return InvestigationValidationResult(
            analysis_id=analysis_id,
            is_valid=is_valid,
            mode=effective_mode,
            warnings=warnings,
            errors=errors,
        )

    def get_status(self, analysis_id: str) -> InvestigationStatusResponse:
        """Get the full status report of an investigation session."""
        session = self._read_session(analysis_id)
        mode = InvestigationMode(session.get("mode", InvestigationMode.INVESTIGATION.value))

        val_result = self.validate_investigation(analysis_id, mode)

        files_dict = session.get("files", {})
        files_status = InvestigationFilesStatus(
            sentinel=FileStatus(**files_dict.get("sentinel", {})),
            wind=FileStatus(**files_dict.get("wind", {})),
            current=FileStatus(**files_dict.get("current", {})),
            ais=FileStatus(**files_dict.get("ais", {})),
        )

        return InvestigationStatusResponse(
            analysis_id=analysis_id,
            status=InvestigationStatus(session.get("status", InvestigationStatus.CREATED.value)),
            source_type=InvestigationSourceType(session.get("source_type", InvestigationSourceType.UPLOADED_DATASET.value)),
            mode=mode,
            created_at=session.get("created_at", datetime.now(timezone.utc).isoformat()),
            files=files_status,
            validation=val_result,
            warnings=val_result.warnings,
            errors=val_result.errors,
        )

    def run_investigation(
        self,
        analysis_id: str,
        req: InvestigationRunRequest,
    ) -> Dict[str, Any]:
        """Trigger investigation processing pipeline stage."""
        val = self.validate_investigation(analysis_id, req.mode)
        if not val.is_valid:
            raise HTTPException(
                status_code=400,
                detail={"message": "Investigation data is not ready for processing", "errors": val.errors},
            )

        session = self._read_session(analysis_id)
        session["status"] = InvestigationStatus.READY.value
        session["configuration"] = req.configuration
        self._write_session(analysis_id, session)

        return {
            "analysis_id": analysis_id,
            "status": "ready_for_processing",
            "mode": val.mode.value,
            "message": "Investigation validated and staged for backend forensic processing pipeline.",
            "warnings": val.warnings,
        }
