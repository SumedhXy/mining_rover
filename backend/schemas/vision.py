from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VisionDetectionResponse(BaseModel):
    class_name: str
    confidence: float
    bbox: List[float] = Field(default_factory=list)
    image_path: Optional[str] = None
    source: str = "yolo"
    device_id: str = "mining_rover_01"
    timestamp: Optional[str] = None


class VisionLatestResponse(BaseModel):
    timestamp: Optional[str] = None
    detections: List[Dict[str, Any]] = Field(default_factory=list)


class VisionHistoryResponse(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class VisionDetectionPayload(BaseModel):
    class_name: str
    confidence: float
    bbox: Optional[List[float]] = None
    image_path: Optional[str] = None
    timestamp: Optional[str] = None
    source: Optional[str] = "yolo"
    device_id: Optional[str] = "mining_rover_01"


class VisionPayload(BaseModel):
    timestamp: Optional[str] = None
    detections: List[VisionDetectionPayload] = Field(default_factory=list)
