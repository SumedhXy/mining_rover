from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from backend.services.telemetry_service import TelemetryService


router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])
service: TelemetryService | None = None


@router.get("/latest")
def latest_telemetry() -> Dict[str, Any]:
    if service is None:
        raise HTTPException(status_code=503, detail="Telemetry service unavailable")
    return service.latest()


@router.get("/history")
def telemetry_history(limit: int = 100) -> Dict[str, Any]:
    if service is None:
        raise HTTPException(status_code=503, detail="Telemetry service unavailable")
    return service.history(limit=limit)
