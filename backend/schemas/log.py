from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MissionLogResponse(BaseModel):
    id: Optional[int] = None
    mission_id: Optional[int] = None
    timestamp: str
    level: str = "INFO"
    event_type: str = "SYSTEM"
    message: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # UI dashboard helpers
    time: Optional[str] = None
    type: Optional[str] = None
    event: Optional[str] = None
    severity: Optional[str] = None


class MissionLogListResponse(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class CreateMissionLogPayload(BaseModel):
    level: str = "INFO"
    event_type: str = "SYSTEM"
    message: str
    mission_id: Optional[int] = None
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
