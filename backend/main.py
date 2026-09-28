from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import logging
import math
import os
from pathlib import Path
import sys
from typing import Any, Dict

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import decisions as decisions_module
from backend.api import locations as locations_module
from backend.api import logs as logs_module
from backend.api import missions as missions_module
from backend.api import observations as observations_module
from backend.api import sensors as sensors_module
from backend.api import sync as sync_module
from backend.api import system as system_module
from backend.api import telemetry as telemetry_module
from backend.api import vision as vision_module
from backend.api.decisions import alias_router as decisions_alias_router, router as decisions_router
from backend.api.locations import router as locations_router
from backend.api.logs import router as logs_router
from backend.api.missions import router as missions_router
from backend.api.observations import router as observations_router
from backend.api.sensors import router as sensors_router
from backend.api.sync import router as sync_router
from backend.api.system import router as system_router
from backend.api.telemetry import router as telemetry_router
from backend.api.vision import router as vision_router
from backend.dependencies import get_db, get_sync_service
from backend.services.backend_service import BackendService
from backend.services.decision_service import DecisionAPIService
from backend.services.sensor_service import SensorAPIService
from backend.services.telemetry_service import TelemetryService
from backend.services.vision_service import VisionAPIService
from decision_engine.engine import evaluate as evaluate_hazard
from sensors.sources.simulator_source import SimulatorSource

logger = logging.getLogger("backend.main")

# Initialize database and services
db = get_db()

sensor_service = SensorAPIService(db)
vision_service = VisionAPIService(db)
decision_service = DecisionAPIService(db)
telemetry_service = TelemetryService(db)
backend_service = BackendService(db)
sync_service = get_sync_service()

# Wire modules
sensors_module.service = sensor_service
vision_module.service = vision_service
decisions_module.service = decision_service
telemetry_module.service = telemetry_service
missions_module.service = backend_service
logs_module.service = backend_service
locations_module.service = backend_service
observations_module.service = backend_service
system_module.service = backend_service
sync_module.service = sync_service

_simulator_source = SimulatorSource()
_simulator_tick = 0


async def background_telemetry_loop():
    """Background simulator to feed telemetry when hardware ESP32 is absent."""
    global _simulator_tick
    while True:
        try:
            _simulator_tick += 1
            reading = _simulator_source.read()
            now_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

            vibration = round(0.12 + 0.05 * math.sin(_simulator_tick / 5.0) + 0.02 * math.cos(_simulator_tick / 2.0), 3)
            battery = max(15.0, round(98.5 - (_simulator_tick / 2400.0) * 1.0, 1))

            sensor_payload = {
                "timestamp": now_iso,
                "temperature": round(reading.temperature, 1),
                "humidity": round(reading.humidity, 1),
                "gas": round(reading.gas, 2),
                "smoke": round(reading.smoke, 2),
                "temperature_c": round(reading.temperature, 1),
                "humidity_percent": round(reading.humidity, 1),
                "pressure_hpa": round(reading.pressure, 1) if getattr(reading, "pressure", None) else 1013.25,
                "mq4": round(reading.gas, 2),
                "mq135": round(reading.smoke, 2),
                "battery": battery,
                "vibration": vibration,
                "source": "simulator",
                "device_id": "mining_rover_01",
            }
            sensor_service.add_reading(sensor_payload)

            latest_vision = vision_service.latest()
            assessment = evaluate_hazard(
                latest_vision,
                {
                    "temperature": reading.temperature,
                    "humidity": reading.humidity,
                    "gas": reading.gas,
                    "smoke": reading.smoke,
                    "vibration": vibration,
                },
            )

            decision_service.add_decision(
                {
                    "timestamp": now_iso,
                    "device_id": "mining_rover_01",
                    "hazard_type": assessment.hazard_type.upper(),
                    "severity": assessment.severity,
                    "confidence": assessment.confidence,
                    "reasons": assessment.reasons,
                    "sources": ["sensor", "vision"] if latest_vision.get("detections") else ["sensor"],
                    "message": "; ".join(assessment.reasons) if assessment.reasons else "Telemetry nominal",
                    "recommended_action": "STOP_AND_INSPECT" if assessment.severity in ["HIGH", "CRITICAL"] else "PROCEED",
                }
            )
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Simulator loop iteration note: {e}")

        await asyncio.sleep(1.5)


@asynccontextmanager
async def lifespan(app: FastAPI):
    telemetry_task = None
    if not os.getenv("PYTEST_CURRENT_TEST") and os.getenv("TESTING") != "1":
        telemetry_task = asyncio.create_task(background_telemetry_loop())
    yield
    if telemetry_task:
        telemetry_task.cancel()
        try:
            await telemetry_task
        except asyncio.CancelledError:
            pass


app = FastAPI(
    title="Mining Rover API",
    description="Offline-First Local API Gateway between Mining Rover hardware/modules and Dashboard.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
allowed_origins_env = os.getenv("ROVER_ALLOWED_ORIGINS", "*")
allowed_origins = [orig.strip() for orig in allowed_origins_env.split(",") if orig.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins if allowed_origins else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers (Section 20 & 23)
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "RESOURCE_NOT_FOUND",
        422: "UNPROCESSABLE_ENTITY",
        500: "INTERNAL_SERVER_ERROR",
        503: "SERVICE_UNAVAILABLE",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    msg = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "error": {
                "code": code,
                "message": msg,
            },
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": exc.errors(),
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request parameters or payload",
                "details": exc.errors(),
            },
        },
    )


# Register all routers
app.include_router(system_router)
app.include_router(sensors_router)
app.include_router(vision_router)
app.include_router(decisions_router)
app.include_router(decisions_alias_router)
app.include_router(missions_router)
app.include_router(logs_router)
app.include_router(locations_router)
app.include_router(observations_router)
app.include_router(sync_router)
app.include_router(telemetry_router)


@app.get("/", summary="Root API Status")
def root() -> Dict[str, Any]:
    """Root endpoint exposing API service identity, offline-first status, and backward compatibility."""
    return {
        "service": "Mining Rover API",
        "status": "online",
        "mode": "offline_first",
        "message": "Mining Rover API is running in offline mode",
        "version": "1.0.0",
    }


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("ROVER_BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("ROVER_BACKEND_PORT", "8000"))
    uvicorn.run("backend.main:app", host=host, port=port, reload=False)
