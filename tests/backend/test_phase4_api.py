from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.api import (
    decisions as decisions_module,
    locations as locations_module,
    logs as logs_module,
    missions as missions_module,
    observations as observations_module,
    sensors as sensors_module,
    sync as sync_module,
    system as system_module,
    telemetry as telemetry_module,
    vision as vision_module,
)
from backend.services.backend_service import BackendService
from backend.services.decision_service import DecisionAPIService
from backend.services.sensor_service import SensorAPIService
from backend.services.telemetry_service import TelemetryService
from backend.services.vision_service import VisionAPIService
from database.database import SQLiteDatabase
from sync.sync_service import SyncService

from backend.schemas.decision import DecisionLatestResponse, DecisionHistoryResponse
from backend.schemas.location import LocationListResponse, LocationResponse
from backend.schemas.log import MissionLogListResponse
from backend.schemas.mission import CurrentMissionResponse, MissionListResponse
from backend.schemas.observation import ObservationResponse
from backend.schemas.sensor import SensorLatestResponse, SensorHistoryResponse
from backend.schemas.sync import SyncStatusResponse, SyncTriggerResponse
from backend.schemas.system import HealthResponse, SystemStatusResponse
from backend.schemas.vision import VisionLatestResponse, VisionHistoryResponse

client = TestClient(app)
_test_db = None


@pytest.fixture(autouse=True, scope="module")
def setup_test_environment(tmp_path_factory):
    global _test_db
    test_db_path = str(tmp_path_factory.mktemp("test_db") / "test_rover.db")
    _test_db = SQLiteDatabase(path=test_db_path)
    _test_db.initialize()

    sensor_svc = SensorAPIService(_test_db)
    vision_svc = VisionAPIService(_test_db)
    decision_svc = DecisionAPIService(_test_db)
    telemetry_svc = TelemetryService(_test_db)
    backend_svc = BackendService(_test_db)
    sync_svc = SyncService(_test_db, server_url="http://127.0.0.1:8000/api/sync/receive")

    sensors_module.service = sensor_svc
    vision_module.service = vision_svc
    decisions_module.service = decision_svc
    telemetry_module.service = telemetry_svc
    missions_module.service = backend_svc
    logs_module.service = backend_svc
    locations_module.service = backend_svc
    observations_module.service = backend_svc
    system_module.service = backend_svc
    sync_module.service = sync_svc

    yield _test_db


# 1. Health endpoint
def test_1_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ok", "degraded"]
    assert data["database"] == "ok"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data
    # Validate Pydantic schema
    HealthResponse(**data)


# 2. Latest sensor endpoint
def test_2_latest_sensor_endpoint():
    from datetime import datetime, timezone
    now_ts = datetime.now(timezone.utc).isoformat()
    sensor_payload = {
        "timestamp": now_ts,
        "temperature_c": 34.5,
        "humidity_percent": 67.0,
        "pressure_hpa": 998.2,
        "mq4": 0.42,
        "mq135": 0.31,
        "source": "esp32_sensor_01",
        "device_id": "mining_rover_01",
    }
    post_res = client.post("/api/sensors", json=sensor_payload)
    assert post_res.status_code == 200

    latest_res = client.get("/api/sensors/latest")
    assert latest_res.status_code == 200
    data = latest_res.json()
    assert data["temperature_c"] == 34.5
    assert data["humidity_percent"] == 67.0
    assert data["pressure_hpa"] == 998.2
    assert data["mq4"] == 0.42
    assert data["mq135"] == 0.31
    assert data["source"] == "esp32_sensor_01"
    # Schema validation
    SensorLatestResponse(**data)


# 3. Sensor history
def test_3_sensor_history():
    res = client.get("/api/sensors/history?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "count" in data
    assert isinstance(data["items"], list)
    assert data["count"] == len(data["items"])
    SensorHistoryResponse(**data)


# 4. Latest vision endpoint
def test_4_latest_vision_endpoint():
    from datetime import datetime, timezone
    now_ts = datetime.now(timezone.utc).isoformat()
    vision_payload = {
        "timestamp": now_ts,
        "detections": [
            {
                "class_name": "fire",
                "confidence": 0.86,
                "bbox": [100.0, 120.0, 300.0, 400.0],
                "image_path": "/data/images/fire_01.jpg",
                "source": "yolo",
            }
        ],
    }
    post_res = client.post("/api/vision", json=vision_payload)
    assert post_res.status_code == 200

    latest_res = client.get("/api/vision/latest")
    assert latest_res.status_code == 200
    data = latest_res.json()
    assert len(data["detections"]) >= 1
    det = data["detections"][0]
    assert det["class_name"] == "fire"
    assert det["confidence"] == 0.86
    assert det["image_path"] == "/data/images/fire_01.jpg"
    VisionLatestResponse(**data)


# 5. Vision history
def test_5_vision_history():
    res = client.get("/api/vision/history?limit=5")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "count" in data
    assert isinstance(data["items"], list)
    VisionHistoryResponse(**data)


# 6. Latest decision endpoint
def test_6_latest_decision_endpoint():
    from datetime import datetime, timezone
    now_ts = datetime.now(timezone.utc).isoformat()
    decision_payload = {
        "timestamp": now_ts,
        "hazard_type": "gas",
        "severity": "HIGH",
        "confidence": 0.82,
        "reasons": ["MQ-4 level elevated"],
        "sensor_evidence": [{"sensor": "mq4", "value": 0.42}],
        "vision_evidence": [],
    }
    post_res = client.post("/api/decisions", json=decision_payload)
    assert post_res.status_code == 200

    latest_res = client.get("/api/decisions/latest")
    assert latest_res.status_code == 200
    data = latest_res.json()
    assert data["hazard_type"] == "gas"
    assert data["severity"] == "HIGH"
    assert data["confidence"] == 0.82
    assert "MQ-4 level elevated" in data["reasons"]
    DecisionLatestResponse(**data)


# 7. Decision history
def test_7_decision_history():
    res = client.get("/api/decisions/history?severity=HIGH&limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "count" in data
    assert isinstance(data["items"], list)
    for item in data["items"]:
        assert item["severity"] == "HIGH"
    DecisionHistoryResponse(**data)


# 8. Current mission
def test_8_current_mission():
    # End active missions first to verify mission: null
    with _test_db.connection.transaction() as conn:
        conn.execute("UPDATE missions SET status = 'COMPLETED' WHERE status = 'ACTIVE'")
    
    empty_res = client.get("/api/mission/current")
    assert empty_res.status_code == 200
    assert empty_res.json()["mission"] is None

    # Create active mission
    create_res = client.post(
        "/api/missions",
        json={
            "mission_code": "EXP-2026-001",
            "status": "ACTIVE",
            "started_at": "2026-09-28T10:00:00+00:00",
            "notes": "Exploration Sector 4B",
            "start_location": {"label": "SECTOR-A-POINT-04"},
        },
    )
    assert create_res.status_code in [200, 201]

    active_res = client.get("/api/mission/current")
    assert active_res.status_code == 200
    data = active_res.json()
    assert data["mission_code"] == "EXP-2026-001"
    assert data["status"] == "ACTIVE"
    CurrentMissionResponse(**data)


# 9. Mission history
def test_9_mission_history():
    res = client.get("/api/missions?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "count" in data
    assert isinstance(data["items"], list)
    MissionListResponse(**data)


# 10. Logs
def test_10_logs():
    log_payload = {
        "timestamp": "2026-09-28T12:31:20+00:00",
        "level": "INFO",
        "event_type": "MISSION_STARTED",
        "message": "Mission started",
        "metadata": {"sector": "4B"},
    }
    create_res = client.post("/api/logs", json=log_payload)
    assert create_res.status_code == 200

    logs_res = client.get("/api/logs?level=INFO&limit=10")
    assert logs_res.status_code == 200
    data = logs_res.json()
    assert "items" in data
    assert "count" in data
    assert any(log["event_type"] == "MISSION_STARTED" for log in data["items"])
    MissionLogListResponse(**data)


# 11. Locations
def test_11_locations():
    loc_payload = {
        "label": "SECTOR-A-POINT-04",
        "location_type": "MINE_MARKER",
        "x": 12.5,
        "y": 45.0,
        "z": -120.0,
    }
    create_res = client.post("/api/locations", json=loc_payload)
    assert create_res.status_code == 200
    loc_id = create_res.json()["id"]

    all_res = client.get("/api/locations")
    assert all_res.status_code == 200
    LocationListResponse(**all_res.json())

    single_res = client.get(f"/api/locations/{loc_id}")
    assert single_res.status_code == 200
    single_data = single_res.json()
    assert single_data["label"] == "SECTOR-A-POINT-04"
    assert single_data["x"] == 12.5
    assert "observations" in single_data
    LocationResponse(**single_data)


# 12. Observation reconstruction
def test_12_observation_reconstruction():
    res = client.get("/api/observations/latest")
    assert res.status_code == 200
    data = res.json()
    assert "timestamp" in data
    assert "sensors" in data
    assert "decision" in data
    ObservationResponse(**data)


# 13. System status
def test_13_system_status():
    res = client.get("/api/system/status")
    assert res.status_code == 200
    data = res.json()
    assert data["rover_status"] == "RUNNING"
    assert data["camera_status"] == "OK"
    assert data["sensor_status"] == "OK"
    assert data["database_status"] == "OK"
    assert "storage_available_mb" in data
    assert "cpu_temperature_c" in data
    assert "timestamp" in data
    SystemStatusResponse(**data)


# 14. Sync status
def test_14_sync_status():
    res = client.get("/api/sync/status")
    assert res.status_code == 200
    data = res.json()
    assert "network_available" in data
    assert "sync_enabled" in data
    assert "pending_records" in data
    SyncStatusResponse(**data)


# 15. Sync trigger
def test_15_sync_trigger():
    res = client.post("/api/sync/trigger")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "started"
    SyncTriggerResponse(**data)


# 16. Camera unavailable handling
def test_16_camera_unavailable_handling(monkeypatch):
    def fail_camera():
        raise RuntimeError("Could not open camera device 0")

    monkeypatch.setattr(vision_module.camera_stream_service, "open_camera", fail_camera)
    res = client.get("/api/vision/camera/stream")
    assert res.status_code == 503
    err_json = res.json()
    assert "Could not open camera device 0" in (err_json.get("detail") or str(err_json))

    # Verify other subsystems remain healthy and isolated
    sensor_res = client.get("/api/sensors/latest")
    assert sensor_res.status_code == 200


# 17. Database unavailable handling
def test_17_database_unavailable_handling(monkeypatch):
    from backend.api import system as sys_mod

    def fail_db():
        raise RuntimeError("SQLite disk I/O failure")

    monkeypatch.setattr(sys_mod.service.database, "connect", fail_db)
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["database"] == "error"
    assert data["status"] == "degraded"


# 18. Invalid query handling
def test_18_invalid_query_handling():
    res = client.get("/api/sensors/history?limit=-10")
    assert res.status_code == 422
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "VALIDATION_ERROR"


# 19. Offline operation
def test_19_offline_operation():
    """Verify all core endpoints function locally without requiring any network connectivity."""
    offline_endpoints = [
        "/api/sensors/latest",
        "/api/vision/latest",
        "/api/decisions/latest",
        "/api/mission/current",
        "/api/missions",
        "/api/logs",
        "/api/locations",
        "/api/system/status",
        "/api/sync/status",
    ]
    for endpoint in offline_endpoints:
        res = client.get(endpoint)
        assert res.status_code == 200, f"Endpoint {endpoint} failed in offline mode with {res.status_code}"


# 20. API response schema validation
def test_20_api_response_schema_validation():
    # Health
    HealthResponse(**client.get("/api/health").json())
    # Sensors
    SensorLatestResponse(**client.get("/api/sensors/latest").json())
    SensorHistoryResponse(**client.get("/api/sensors/history").json())
    # Vision
    VisionLatestResponse(**client.get("/api/vision/latest").json())
    VisionHistoryResponse(**client.get("/api/vision/history").json())
    # Decision
    DecisionLatestResponse(**client.get("/api/decisions/latest").json())
    DecisionHistoryResponse(**client.get("/api/decisions/history").json())
    # Missions
    CurrentMissionResponse(**client.get("/api/mission/current").json())
    MissionListResponse(**client.get("/api/missions").json())
    # Logs
    MissionLogListResponse(**client.get("/api/logs").json())
    # Locations
    LocationListResponse(**client.get("/api/locations").json())
    # System Status
    SystemStatusResponse(**client.get("/api/system/status").json())
    # Sync Status
    SyncStatusResponse(**client.get("/api/sync/status").json())
