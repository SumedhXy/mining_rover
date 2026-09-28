from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MissionResponse(BaseModel):
    id: Optional[Any] = None
    mission_code: str
    status: str = "PLANNED"
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    notes: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    start_location: Optional[Dict[str, Any]] = None
    end_location: Optional[Dict[str, Any]] = None
    # UI dashboard helper fields
    title: Optional[str] = None
    durationMinutes: Optional[int] = None
    hazardsEncountered: Optional[int] = None
    startTime: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None


class CurrentMissionResponse(BaseModel):
    mission: Optional[MissionResponse] = None
    # Direct fields when mission is active
    mission_code: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[str] = None
    location: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None
    title: Optional[str] = None
    durationMinutes: Optional[int] = None
    hazardsEncountered: Optional[int] = None
    startTime: Optional[str] = None
    sector: Optional[str] = None
    description: Optional[str] = None


class MissionListResponse(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class CreateMissionPayload(BaseModel):
    mission_code: str
    status: str = "PLANNED"
    started_at: Optional[str] = None
    notes: Optional[str] = None
    start_location: Optional[Dict[str, Any]] = None
    end_location: Optional[Dict[str, Any]] = None
