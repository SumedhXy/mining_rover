from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    database: str = "ok"
    timestamp: str
    version: str = "1.0.0"


class SystemStatusResponse(BaseModel):
    rover_status: str = "RUNNING"
    camera_status: str = "OK"
    sensor_status: str = "OK"
    database_status: str = "OK"
    storage_available_mb: Optional[float] = None
    cpu_temperature_c: Optional[float] = None
    timestamp: str
    # Dashboard telemetry compatibility fields
    rover: Optional[str] = "Running"
    backend: Optional[str] = "running"
    database: Optional[str] = "connected"
    network: Optional[str] = "offline"
    mode: Optional[str] = "offline"
    battery_pct: Optional[float] = 86.0
    internal_temp_c: Optional[float] = 38.2
    firmware_version: Optional[str] = "v2.4.1"
    active_sector: Optional[str] = "Sector 4B"
    ip_address: Optional[str] = "127.0.0.1"
    uptime_seconds: Optional[int] = 0
