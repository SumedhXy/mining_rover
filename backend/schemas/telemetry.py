from __future__ import annotations

from pydantic import BaseModel, Field


class TelemetryStatus(BaseModel):
    backend: str = Field(default="running")
    database: str = Field(default="connected")
    network: str = Field(default="offline")
    mode: str = Field(default="offline")
    rover: str = Field(default="Running")
    battery_pct: float = Field(default=86.0)
    internal_temp_c: float = Field(default=38.2)
    firmware_version: str = Field(default="v2.4.1")
    active_sector: str = Field(default="Sector 4B")
    ip_address: str = Field(default="127.0.0.1")
    uptime_seconds: int = Field(default=7920)
