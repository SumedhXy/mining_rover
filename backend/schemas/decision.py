from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DecisionResponse(BaseModel):
    timestamp: Optional[str] = None
    decision_id: Optional[str] = None
    hazard_type: str = "none"
    hazard: Optional[str] = None  # Backward compatibility alias
    severity: str = "LOW"
    confidence: float = 0.0
    reasons: List[str] = Field(default_factory=list)
    reason: Optional[str] = None  # Backward compatibility alias
    sensor_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    vision_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    all_hazards: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_action: Optional[str] = "MONITOR"
    sources: List[str] = Field(default_factory=list)


class DecisionLatestResponse(DecisionResponse):
    pass


class DecisionHistoryResponse(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class DecisionPayload(BaseModel):
    timestamp: Optional[str] = None
    hazard_type: str = "none"
    severity: str = "LOW"
    confidence: float = 0.0
    reasons: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    recommended_action: Optional[str] = "MONITOR"
    device_id: Optional[str] = "mining_rover_01"
    sensor_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    vision_evidence: List[Dict[str, Any]] = Field(default_factory=list)
