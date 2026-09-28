from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def default_utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


@dataclass
class SensorReading:
    timestamp: str
    device_id: str = "mining_rover_01"
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    pressure_hpa: Optional[float] = None
    mq4: Optional[float] = None
    mq135: Optional[float] = None
    sequence_number: Optional[int] = None
    source: str = "simulator"
    sync_status: str = "pending"
    id: Optional[int] = None
    created_at: str = field(default_factory=default_utc_now)
    # Legacy fields
    sensor_type: str = "temperature"
    value: float = 0.0
    unit: str = ""
    valid: bool = True
    synced: bool = False


@dataclass
class VisionDetection:
    timestamp: str
    class_name: str
    confidence: float
    bbox_x1: Optional[float] = None
    bbox_y1: Optional[float] = None
    bbox_x2: Optional[float] = None
    bbox_y2: Optional[float] = None
    image_path: Optional[str] = None
    source: str = "yolo"
    mission_id: Optional[int] = None
    location_id: Optional[int] = None
    sync_status: str = "pending"
    id: Optional[int] = None
    device_id: str = "mining_rover_01"
    created_at: str = field(default_factory=default_utc_now)
    # Legacy fields
    x_center: Optional[float] = None
    y_center: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    synced: bool = False


@dataclass
class HazardEvent:
    timestamp: str
    hazard_type: str
    severity: str
    confidence: float
    decision_id: Optional[str] = None
    mission_id: Optional[int] = None
    location_id: Optional[int] = None
    reasons_json: Optional[str] = None
    sensor_evidence_json: Optional[str] = None
    vision_evidence_json: Optional[str] = None
    source: str = "sensor_vision_fusion"
    sync_status: str = "pending"
    id: Optional[int] = None
    device_id: str = "mining_rover_01"
    created_at: str = field(default_factory=default_utc_now)
    # Legacy fields
    hazard: str = "none"
    sources: str = ""
    message: str = ""
    recommended_action: str = "MONITOR"
    synced: bool = False


@dataclass
class Mission:
    mission_code: str
    status: str = "PLANNED"  # PLANNED, ACTIVE, PAUSED, COMPLETED, ABORTED
    started_at: str = field(default_factory=default_utc_now)
    ended_at: Optional[str] = None
    start_location_json: Optional[str] = None
    end_location_json: Optional[str] = None
    notes: Optional[str] = None
    sync_status: str = "pending"
    id: Optional[int] = None
    created_at: str = field(default_factory=default_utc_now)


@dataclass
class Location:
    mission_id: Optional[int] = None
    location_type: str = "LOCAL_POSITION"  # LOCAL_POSITION, MINE_MARKER, RFID_TAG, WAYPOINT, UNKNOWN
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    label: Optional[str] = None
    id: Optional[int] = None
    created_at: str = field(default_factory=default_utc_now)


@dataclass
class MissionLog:
    timestamp: str
    level: str  # INFO, WARNING, HAZARD, ERROR, CRITICAL
    event_type: str  # MISSION_STARTED, GAS_DETECTED, FIRE_DETECTED, etc.
    message: str
    mission_id: Optional[int] = None
    metadata_json: Optional[str] = None
    id: Optional[int] = None


@dataclass
class SystemStatus:
    timestamp: str
    rover_status: str = "RUNNING"
    camera_status: str = "OK"
    sensor_status: str = "OK"
    database_status: str = "OK"
    network_status: str = "OFFLINE"
    sync_status: str = "pending"
    storage_available_mb: Optional[float] = None
    cpu_temperature_c: Optional[float] = None
    id: Optional[int] = None
    device_id: str = "mining_rover_01"
    created_at: str = field(default_factory=default_utc_now)
    # Legacy fields
    battery_level: Optional[float] = None
    system_status: str = "RUNNING"
    last_sensor_update: Optional[str] = None
    last_vision_update: Optional[str] = None
    last_decision_update: Optional[str] = None


__all__ = [
    "SensorReading",
    "VisionDetection",
    "HazardEvent",
    "Mission",
    "Location",
    "MissionLog",
    "SystemStatus",
]
