from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from backend.schemas.location import (
    CreateLocationPayload,
    LocationListResponse,
    LocationResponse,
)
from backend.services.backend_service import BackendService

router = APIRouter(prefix="/api/locations", tags=["locations"])
service: BackendService | None = None


@router.get("", response_model=LocationListResponse, summary="Get stored mine locations")
def get_locations(
    limit: int = Query(default=100, ge=1, le=1000, description="Max locations to return")
) -> Dict[str, Any]:
    """Return stored mine locations and hazard markers from SQLite."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    items = service.get_locations(limit=limit)
    return {"items": items, "count": len(items)}


@router.get("/{location_id}", response_model=LocationResponse, summary="Get location details and observations")
def get_location(location_id: int) -> Dict[str, Any]:
    """Return a specific location marker and associated rover observations."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    loc = service.get_location_by_id(location_id)
    if not loc:
        raise HTTPException(status_code=404, detail="Location not found")
    return loc


@router.post("", summary="Create mine location marker")
def create_location(payload: CreateLocationPayload) -> Dict[str, Any]:
    """Store a new coordinate or RFID location marker into SQLite."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    loc_id = service.create_location(
        label=payload.label,
        location_type=payload.location_type,
        x=payload.x,
        y=payload.y,
        z=payload.z,
        mission_id=payload.mission_id,
    )
    return {"status": "created", "id": loc_id}
