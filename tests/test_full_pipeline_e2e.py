from __future__ import annotations

import os
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from database.database import SQLiteDatabase
from decision_engine.engine import evaluate
from sensors.sensor_schema import StandardSensorReading
from sensors.sensor_service import SensorService
from sensors.sources.simulator_source import SimulatorSource
from sync.network_monitor import NetworkMonitor
from sync.queue_manager import QueueManager
from sync.sync_service import SyncService
from vision.inference.yolo_service import YOLOInferenceService


def test_complete_mining_rover_end_to_end_pipeline(tmp_path):
    print("\n--- STEP 1: INITIALIZE LOCAL SQLITE DATABASE ---")
    db_path = str(tmp_path / "e2e_rover.db")
    db = SQLiteDatabase(path=db_path)
    db.initialize()
    assert os.path.exists(db_path)

    print("--- STEP 2: RUN SENSOR SERVICE (CAN BUS / SIMULATOR) ---")
    sensor_svc = SensorService(source=SimulatorSource())
    sensor_reading = sensor_svc.read()
    assert sensor_reading is not None
    assert isinstance(sensor_reading, StandardSensorReading)
    assert sensor_reading.temperature > 0
    assert 0.0 <= sensor_reading.gas <= 1.0

    print("--- STEP 3: RUN YOLO VISION INFERENCE ON REAL WEIGHTS ---")
    yolo_svc = YOLOInferenceService()
    test_img = "Fire_test_73_jpg.rf.910fbbeafbcf998232542b7823b15a4d.jpg"
    with open(test_img, "rb") as f:
        detections = yolo_svc.detect(f.read())
    assert len(detections) > 0
    assert detections[0]["class_name"] == "fire"
    assert detections[0]["confidence"] > 0.50

    print("--- STEP 4: RUN DECISION ENGINE FUSION ---")
    hazard = evaluate(
        vision_data={"detections": detections},
        sensor_data={
            "temperature": 55.0,
            "humidity": 60.0,
            "gas": 0.40,
            "smoke": 0.75,
        },
    )
    assert hazard.hazard_type == "fire"
    assert hazard.severity in ("HIGH", "CRITICAL")
    assert hazard.confidence >= 0.70
    assert len(hazard.reasons) > 0

    print("--- STEP 5: STORE ALL METRICS IN LOCAL SQLITE ---")
    s_id = db.insert_sensor_reading(
        timestamp=sensor_reading.timestamp,
        device_id="mining_rover_01",
        sensor_type="gas",
        value=sensor_reading.gas,
        unit="normalized",
        valid=True,
        source=sensor_reading.source or "simulator",
    )
    v_id = db.insert_vision_detection(
        timestamp=datetime.now(timezone.utc).isoformat(),
        device_id="mining_rover_01",
        class_name=detections[0]["class_name"],
        confidence=detections[0]["confidence"],
        x_center=detections[0]["bbox"][0],
        y_center=detections[0]["bbox"][1],
        width=detections[0]["bbox"][2],
        height=detections[0]["bbox"][3],
        source="yolo",
    )
    h_id = db.insert_hazard_event(
        timestamp=hazard.timestamp,
        device_id="mining_rover_01",
        hazard=hazard.hazard_type,
        severity=hazard.severity,
        confidence=hazard.confidence,
        sources="vision,sensor",
        message="; ".join(hazard.reasons),
        recommended_action="EVACUATE_TUNNEL",
    )
    assert s_id is not None and v_id is not None and h_id is not None

    print("--- STEP 6: VERIFY FASTAPI LOCAL ENDPOINTS CONSUMPTION ---")
    client = TestClient(app)
    resp_sensors = client.get("/api/sensors/latest")
    assert resp_sensors.status_code == 200

    resp_decisions = client.get("/api/decisions/latest")
    assert resp_decisions.status_code == 200

    resp_missions = client.get("/api/missions")
    assert resp_missions.status_code == 200
    assert len(resp_missions.json()) >= 1

    resp_logs = client.get("/api/logs")
    assert resp_logs.status_code == 200

    print("--- STEP 7: SIMULATE NETWORK DISCONNECT (OFFLINE-FIRST) ---")
    net_monitor = NetworkMonitor()
    net_monitor.set_override(False)
    assert net_monitor.is_online() is False

    # Insert new data while offline
    db.insert_sensor_reading(
        timestamp=datetime.now(timezone.utc).isoformat(),
        device_id="mining_rover_01",
        sensor_type="temperature",
        value=37.5,
        unit="C",
        valid=True,
        source="simulator",
    )
    stats_offline = db.get_sync_statistics()
    assert stats_offline["pending_count"] == 4  # 3 initial + 1 new

    print("--- STEP 8: RECONNECT NETWORK & SYNCHRONIZE WITH DEDUPLICATION ---")
    net_monitor.set_override(True)
    assert net_monitor.is_online() is True

    qm = QueueManager(db)
    batch = qm.get_pending_batch(batch_size=50)
    assert len(batch) == 4

    payload = {
        "rover_id": "mining_rover_01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "batch_size": len(batch),
        "records": batch,
    }
    # Upload to backend receive endpoint
    recv_resp = client.post("/api/sync/receive", json=payload)
    assert recv_resp.status_code == 200
    assert recv_resp.json()["accepted_count"] == 4

    # Mark synced locally
    qm.mark_batch_synced(batch)
    stats_synced = db.get_sync_statistics()
    assert stats_synced["pending_count"] == 0
    assert stats_synced["synced_count"] == 4

    # Duplicate transmission test (idempotency)
    dupe_resp = client.post("/api/sync/receive", json=payload)
    assert dupe_resp.status_code == 200
    assert dupe_resp.json()["accepted_count"] == 0
    assert dupe_resp.json()["ignored_duplicate_count"] == 4

    print("--- STEP 9: VERIFY MISSION COMPLETION & LOG PERSISTENCE ---")
    active_m = client.get("/api/mission/current").json()
    logs_resp = client.get("/api/logs").json()
    log_items = logs_resp if isinstance(logs_resp, list) else logs_resp.get("items", [])
    assert len(log_items) >= 5

    print("\n>>> FULL END-TO-END PIPELINE VALIDATED SUCCESSFULLY <<<")
