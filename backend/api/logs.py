from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from backend.schemas.log import (
    CreateMissionLogPayload,
    MissionLogListResponse,
    MissionLogResponse,
)
from backend.services.backend_service import BackendService

router = APIRouter(prefix="/api/logs", tags=["logs"])
service: BackendService | None = None


@router.get("", response_model=MissionLogListResponse, summary="Get mission activity logs")
def get_mission_logs(
    limit: int = Query(default=100, ge=1, le=1000, description="Max logs to return"),
    start_time: Optional[str] = Query(default=None, description="ISO timestamp start filter"),
    end_time: Optional[str] = Query(default=None, description="ISO timestamp end filter"),
    level: Optional[str] = Query(default=None, description="Log level filter (INFO, WARN, ERROR, CRITICAL)"),
    event_type: Optional[str] = Query(default=None, description="Event type filter (e.g. MISSION_STARTED, HAZARD)"),
    type_filter: Optional[str] = Query(default=None, description="Dashboard UI alias for event type"),
) -> Dict[str, Any]:
    """Retrieve mission activity and telemetry logs from SQLite."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")

    effective_event_type = event_type
    if not effective_event_type and type_filter and type_filter != "All":
        effective_event_type = type_filter

    items = service.get_logs(
        limit=limit,
        start_time=start_time,
        end_time=end_time,
        level=level,
        event_type=effective_event_type,
    )
    return {"items": items, "count": len(items)}


@router.post("", summary="Record mission log event")
def create_mission_log(payload: CreateMissionLogPayload) -> Dict[str, Any]:
    """Persist a new log event into SQLite."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    log_id = service.insert_log(
        level=payload.level,
        event_type=payload.event_type,
        message=payload.message,
        mission_id=payload.mission_id,
        timestamp=payload.timestamp,
        metadata=payload.metadata,
    )
    return {"status": "created", "id": log_id}
