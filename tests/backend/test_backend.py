from fastapi.testclient import TestClient

from backend.api import vision as vision_module
from backend.main import app


client = TestClient(app)


def test_root_endpoint_works():
    response = client.get("/")
    assert response.status_code == 200
    assert "Mining Rover API" in response.json()["message"]


def test_sensor_endpoint_accepts_data_and_returns_latest():
    payload = {
        "temperature": 35.4,
        "humidity": 55.0,
        "gas": 0.72,
        "smoke": 0.08,
        "timestamp": "2026-09-27T10:30:15+05:30",
        "source": "simulator",
        "device_id": "mining_rover_01",
    }

    created = client.post("/api/sensors", json=payload)
    assert created.status_code == 200

    latest = client.get("/api/sensors/latest")
    assert latest.status_code == 200
    assert "readings" in latest.json()


def test_vision_endpoint_accepts_and_returns_latest():
    payload = {
        "timestamp": "2026-09-27T10:30:16+05:30",
        "detections": [
            {"class_name": "rock", "confidence": 0.92, "bbox": [120, 80, 350, 300], "source": "yolo"}
        ],
    }

    created = client.post("/api/vision", json=payload)
    assert created.status_code == 200

    latest = client.get("/api/vision/latest")
    assert latest.status_code == 200
    assert latest.json()["detections"]


def test_vision_detect_endpoint_runs_model_and_saves_detections(monkeypatch):
    detections = [
        {
            "class_name": "rock",
            "confidence": 0.92,
            "bbox": [235.0, 190.0, 230.0, 220.0],
            "source": "yolo",
        }
    ]
    monkeypatch.setattr(vision_module.inference_service, "detect", lambda image: detections)

    response = client.post(
        "/api/vision/detect",
        files={"file": ("frame.jpg", b"image-bytes", "image/jpeg")},
    )

    assert response.status_code == 200
    assert response.json()["detections"] == detections


def test_camera_page_is_available():
    response = client.get("/api/vision/camera")

    assert response.status_code == 200
    assert "Live camera" in response.text


def test_camera_stream_reports_unavailable_device(monkeypatch):
    def fail_to_open():
        raise RuntimeError("Could not open camera 0")

    monkeypatch.setattr(vision_module.inference_service, "ensure_model_loaded", lambda: None)
    monkeypatch.setattr(vision_module.camera_stream_service, "open_camera", fail_to_open)

    response = client.get("/api/vision/camera/stream")

    assert response.status_code == 503
    assert "Could not open camera 0" in response.json()["detail"]


def test_decision_and_telemetry_endpoints_work():
    decision_payload = {
        "timestamp": "2026-09-27T10:30:17+05:30",
        "hazard_type": "ROCKFALL",
        "severity": "HIGH",
        "confidence": 0.91,
        "reasons": ["Rock detected", "Vibration elevated"],
        "sources": ["vision", "sensor"],
        "message": "Rock detected with elevated vibration",
        "recommended_action": "STOP_AND_INSPECT",
    }

    decision_response = client.post("/api/decisions", json=decision_payload)
    assert decision_response.status_code == 200

    decision_result = client.get("/api/decisions/latest")
    assert decision_result.status_code == 200
    assert decision_result.json()["hazard"] == "ROCKFALL"

    telemetry = client.get("/api/telemetry/latest")
    assert telemetry.status_code == 200
    assert "sensors" in telemetry.json()


def test_system_status_is_offline_mode():
    response = client.get("/api/system/status")
    assert response.status_code == 200
    assert response.json()["mode"] == "offline"
    assert response.json()["backend"] == "running"
    assert "battery_pct" in response.json()


def test_missions_and_logs_endpoints():
    client.post("/api/missions", json={"mission_code": "Mission #001", "status": "ACTIVE"})
    current_mission = client.get("/api/mission/current")
    assert current_mission.status_code == 200
    m_data = current_mission.json()
    assert "Mission #001" == m_data.get("mission_code") or "Mission #001" in str(m_data)

    all_missions = client.get("/api/missions")
    assert all_missions.status_code == 200
    m_items = all_missions.json() if isinstance(all_missions.json(), list) else all_missions.json()["items"]
    assert len(m_items) >= 1

    logs = client.get("/api/logs")
    assert logs.status_code == 200
    l_items = logs.json() if isinstance(logs.json(), list) else logs.json()["items"]
    assert isinstance(l_items, list)


def test_sensor_history_and_decision_alias():
    history = client.get("/api/sensors/history?limit=10")
    assert history.status_code == 200
    data = history.json()
    items = data if isinstance(data, list) else data.get("items", [])
    assert isinstance(items, list)

    alias_decision = client.get("/api/decision/latest")
    assert alias_decision.status_code == 200
