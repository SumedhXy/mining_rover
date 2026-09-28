from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LocationResponse(BaseModel):
    id: int
    label: Optional[str] = None
    location_type: str = "LOCAL_POSITION"
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    mission_id: Optional[int] = None
    observations: List[Dict[str, Any]] = Field(default_factory=list)


class LocationListResponse(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class CreateLocationPayload(BaseModel):
    label: Optional[str] = None
    location_type: str = "MINE_MARKER"
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    mission_id: Optional[int] = None
