from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from backend.schemas.system import HealthResponse, SystemStatusResponse
from backend.services.backend_service import BackendService

router = APIRouter(tags=["system"])
service: BackendService | None = None


@router.get("/api/health", response_model=HealthResponse, summary="Rover backend health check")
@router.get("/health", response_model=HealthResponse, summary="Rover backend health check (alias)")
def health_check() -> Dict[str, Any]:
    """Offline health verification endpoint confirming SQLite and service availability."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    return service.get_health()


@router.get("/api/system/status", response_model=SystemStatusResponse, summary="Rover system status")
def system_status() -> Dict[str, Any]:
    """Return software and hardware status indicators for dashboard."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    return service.get_system_status()
