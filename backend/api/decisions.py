from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from backend.schemas.decision import (
    DecisionHistoryResponse,
    DecisionLatestResponse,
    DecisionPayload,
)
from backend.services.decision_service import DecisionAPIService

router = APIRouter(prefix="/api/decisions", tags=["decisions"])
alias_router = APIRouter(prefix="/api/decision", tags=["decisions"])
service: DecisionAPIService | None = None


@router.get("/latest", response_model=DecisionLatestResponse, summary="Get latest decision assessment")
@alias_router.get("/latest", response_model=DecisionLatestResponse, summary="Get latest decision assessment (alias)")
def latest_decision() -> Dict[str, Any]:
    """Return the latest Decision Engine assessment from SQLite without recalculation."""
    if service is None:
        raise HTTPException(status_code=503, detail="Decision service unavailable")
    return service.latest()


@router.get("/history", response_model=DecisionHistoryResponse, summary="Get decision history")
@alias_router.get("/history", response_model=DecisionHistoryResponse, summary="Get decision history (alias)")
def decision_history(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum decisions to return"),
    start_time: Optional[str] = Query(default=None, description="ISO timestamp start filter"),
    end_time: Optional[str] = Query(default=None, description="ISO timestamp end filter"),
    severity: Optional[str] = Query(default=None, description="Filter by severity level (e.g. HIGH, CRITICAL)"),
    hazard_type: Optional[str] = Query(default=None, description="Filter by hazard type (e.g. gas, fire)"),
) -> Dict[str, Any]:
    """Return historical decision assessments from SQLite filtered by severity and hazard type."""
    if service is None:
        raise HTTPException(status_code=503, detail="Decision service unavailable")
    items = service.history(
        limit=limit,
        start_time=start_time,
        end_time=end_time,
        severity=severity,
        hazard_type=hazard_type,
    )
    return {"items": items, "count": len(items)}


@router.post("", summary="Submit decision assessment")
@alias_router.post("", summary="Submit decision assessment (alias)")
def submit_decision(payload: DecisionPayload) -> Dict[str, Any]:
    """Store evaluated hazard decision into SQLite."""
    if service is None:
        raise HTTPException(status_code=503, detail="Decision service unavailable")
    return service.add_decision(payload.model_dump(exclude_none=True))
