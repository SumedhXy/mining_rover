from __future__ import annotations

from typing import Any, Dict
from fastapi import APIRouter, HTTPException

from backend.schemas.observation import ObservationResponse
from backend.services.backend_service import BackendService

router = APIRouter(prefix="/api/observations", tags=["observations"])
service: BackendService | None = None


@router.get("/latest", response_model=ObservationResponse, summary="Get latest reconstructed observation")
def latest_observation() -> Dict[str, Any]:
    """Provide a reconstructed observation correlating telemetry, vision, decision, location, and mission."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    observation = service.get_latest_observation()
    if not observation:
        raise HTTPException(status_code=404, detail="No observation available to reconstruct")
    return observation
