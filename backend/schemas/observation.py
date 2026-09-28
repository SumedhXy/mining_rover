from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ObservationResponse(BaseModel):
    timestamp: Optional[str] = None
    decision_id: Optional[str] = None
    mission: Optional[Dict[str, Any]] = None
    location: Optional[Dict[str, Any]] = None
    sensors: Optional[Dict[str, Any]] = None
    vision: List[Dict[str, Any]] = Field(default_factory=list)
    decision: Optional[Dict[str, Any]] = None
    image_path: Optional[str] = None
    logs: List[Dict[str, Any]] = Field(default_factory=list)
