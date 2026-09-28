from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query

from backend.schemas.sensor import (
    SensorHistoryResponse,
    SensorLatestResponse,
    SensorPayload,
)
from backend.services.sensor_service import SensorAPIService

router = APIRouter(prefix="/api/sensors", tags=["sensors"])
service: SensorAPIService | None = None


@router.get("/latest", response_model=SensorLatestResponse, summary="Get latest sensor telemetry")
def latest_sensors() -> Dict[str, Any]:
    """Return the latest reading for each environmental sensor from SQLite."""
    if service is None:
        raise HTTPException(status_code=503, detail="Sensor service unavailable")
    return service.latest()


@router.get("/history", response_model=SensorHistoryResponse, summary="Get sensor telemetry history")
def sensor_history(
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum records to return"),
    start_time: Optional[str] = Query(default=None, description="ISO timestamp start filter"),
    end_time: Optional[str] = Query(default=None, description="ISO timestamp end filter"),
) -> Dict[str, Any]:
    """Return historical sensor readings from SQLite with pagination and time filters."""
    if service is None:
        raise HTTPException(status_code=503, detail="Sensor service unavailable")
    items = service.history(limit=limit, start_time=start_time, end_time=end_time)
    return {"items": items, "count": len(items)}


@router.post("", summary="Submit sensor reading")
def submit_sensors(payload: SensorPayload) -> Dict[str, Any]:
    """Ingest sensor data from ESP32 or simulator into local SQLite."""
    if service is None:
        raise HTTPException(status_code=503, detail="Sensor service unavailable")
    return service.add_reading(payload.model_dump(exclude_none=True))
