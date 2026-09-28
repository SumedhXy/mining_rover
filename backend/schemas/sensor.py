from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SensorReadingItem(BaseModel):
    sensor_type: str
    value: float
    unit: str = ""
    valid: bool = True
    source: str = "simulator"
    device_id: str = "mining_rover_01"


class SensorLatestResponse(BaseModel):
    timestamp: Optional[str] = None
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    pressure_hpa: Optional[float] = None
    mq4: Optional[float] = None
    mq135: Optional[float] = None
    source: str = "esp32_sensor_01"
    readings: List[Dict[str, Any]] = Field(default_factory=list)


# Alias for spec consistency
SensorResponse = SensorLatestResponse


class SensorHistoryItem(BaseModel):
    id: Optional[int] = None
    timestamp: str
    sensor_type: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    temperature_c: Optional[float] = None
    humidity_percent: Optional[float] = None
    pressure_hpa: Optional[float] = None
    mq4: Optional[float] = None
    mq135: Optional[float] = None
    valid: bool = True
    source: str = "simulator"
    device_id: str = "mining_rover_01"


class SensorHistoryResponse(BaseModel):
    items: List[Dict[str, Any]] = Field(default_factory=list)
    count: int = 0


class SensorPayload(BaseModel):
    temperature: Optional[float] = Field(default=None)
    humidity: Optional[float] = Field(default=None)
    gas: Optional[float] = Field(default=None)
    smoke: Optional[float] = Field(default=None)
    temperature_c: Optional[float] = Field(default=None)
    humidity_percent: Optional[float] = Field(default=None)
    pressure_hpa: Optional[float] = Field(default=None)
    mq4: Optional[float] = Field(default=None)
    mq135: Optional[float] = Field(default=None)
    battery: Optional[float] = Field(default=None)
    vibration: Optional[float] = Field(default=None)
    timestamp: Optional[str] = Field(default=None)
    source: Optional[str] = Field(default="simulator")
    device_id: Optional[str] = Field(default="mining_rover_01")
