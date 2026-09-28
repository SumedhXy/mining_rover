from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from backend.schemas.mission import (
    CreateMissionPayload,
    CurrentMissionResponse,
    MissionListResponse,
    MissionResponse,
)
from backend.services.backend_service import BackendService

router = APIRouter(tags=["missions"])
service: BackendService | None = None


@router.get("/api/mission/current", response_model=CurrentMissionResponse, summary="Get active mission")
@router.get("/api/missions/current", response_model=CurrentMissionResponse, summary="Get active mission (alias)")
def get_current_mission() -> Dict[str, Any]:
    """Return the active mission from SQLite. If no mission is active, returns mission: null."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    active = service.get_current_mission()
    if not active:
        return {"mission": None}

    # Return structured active mission
    m_code = active.get("mission_code") or str(active.get("id"))
    return {
        "mission": active,
        "id": m_code,
        "mission_code": active.get("mission_code"),
        "status": active.get("status"),
        "started_at": active.get("started_at"),
        "location": active.get("location"),
        "title": active.get("title"),
        "durationMinutes": active.get("durationMinutes", 1),
        "hazardsEncountered": active.get("hazardsEncountered", 0),
        "startTime": active.get("started_at"),
        "sector": active.get("sector"),
        "description": active.get("description"),
    }


@router.get("/api/missions", response_model=MissionListResponse, summary="Get missions history")
def get_missions(
    status: Optional[str] = Query(default=None, description="Filter by mission status (e.g. COMPLETED, ACTIVE)"),
    limit: int = Query(default=50, ge=1, le=500, description="Max missions to return"),
    start_time: Optional[str] = Query(default=None, description="ISO timestamp start filter"),
    end_time: Optional[str] = Query(default=None, description="ISO timestamp end filter"),
) -> Dict[str, Any]:
    """Return historical missions from SQLite with status and time filtering."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    items = service.get_missions(status=status, limit=limit, start_time=start_time, end_time=end_time)
    return {"items": items, "count": len(items)}


@router.get("/api/missions/{mission_id}", summary="Get mission details by ID or code")
def get_mission_by_id(mission_id: str) -> Dict[str, Any]:
    """Retrieve detailed information for a specific mission by integer ID or code."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    mission = service.get_mission_by_id(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    return mission


@router.post("/api/missions", summary="Create a new mission")
def create_mission(payload: CreateMissionPayload) -> Dict[str, Any]:
    """Register a new exploration mission in SQLite."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    try:
        mission_id = service.create_mission(
            mission_code=payload.mission_code,
            status=payload.status,
            started_at=payload.started_at,
            notes=payload.notes,
            start_location=payload.start_location,
            end_location=payload.end_location,
        )
        return {"status": "created", "id": mission_id, "mission_code": payload.mission_code}
    except Exception as e:
        if "UNIQUE" in str(e).upper():
            existing = service.get_mission_by_id(payload.mission_code)
            if existing:
                if payload.status == "ACTIVE":
                    service.database.repo.start_mission(existing["id"])
                return {"status": "exists", "id": existing["id"], "mission_code": payload.mission_code}
            raise HTTPException(status_code=409, detail=f"Mission code '{payload.mission_code}' already exists")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/missions/{mission_id}/start", summary="Start an existing mission")
def start_mission(mission_id: str) -> Dict[str, Any]:
    """Mark an existing mission as ACTIVE."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    ok = service.database.repo.start_mission(mission_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Mission not found or could not be started")
    return {"status": "started", "mission_id": mission_id}


@router.post("/api/missions/{mission_id}/end", summary="End an active mission")
def end_mission(mission_id: str, status: str = "COMPLETED") -> Dict[str, Any]:
    """Mark an active mission as COMPLETED or ABORTED."""
    if service is None:
        raise HTTPException(status_code=503, detail="Backend service unavailable")
    ok = service.database.repo.end_mission(mission_id, status=status)
    if not ok:
        raise HTTPException(status_code=404, detail="Mission not found or could not be ended")
    return {"status": "ended", "mission_id": mission_id}
