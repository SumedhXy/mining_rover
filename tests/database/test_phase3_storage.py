from __future__ import annotations

import json
import sqlite3
import pytest
from datetime import datetime, timezone, timedelta

from database.database import SQLiteDatabase
from database.migrations import run_migrations


# 1. Database initialization
def test_database_initialization(tmp_path):
    db_file = str(tmp_path / "init_test.db")
    db = SQLiteDatabase(path=db_file)
    db.initialize()

    conn = db.connect()
    try:
        cursor = conn.execute("PRAGMA journal_mode;")
        mode = cursor.fetchone()[0].lower()
        assert mode == "wal"
    finally:
        conn.close()


# 2. Table creation
def test_table_creation(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "tables_test.db"))
    db.initialize()

    conn = db.connect()
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "sensor_readings" in tables
        assert "vision_detections" in tables
        assert "hazard_events" in tables
        assert "missions" in tables
        assert "locations" in tables
        assert "mission_logs" in tables
        assert "system_status" in tables
        assert "schema_migrations" in tables
    finally:
        conn.close()


# 3. Sensor insertion
def test_sensor_insertion(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "sensor_test.db"))
    db.initialize()

    row_id = db.insert_sensor_reading(
        timestamp="2026-09-28T11:30:20Z",
        device_id="sensor_01",
        temperature_c=34.5,
        humidity_percent=67.0,
        pressure_hpa=998.2,
        mq4=0.42,
        mq135=0.31,
        source="esp32",
    )
    assert row_id is not None
    assert row_id > 0


# 4. Sensor retrieval
def test_sensor_retrieval(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "sensor_ret.db"))
    db.initialize()

    db.insert_sensor_reading(
        timestamp="2026-09-28T11:30:20Z",
        device_id="sensor_01",
        temperature_c=34.5,
        humidity_percent=67.0,
        pressure_hpa=998.2,
        mq4=0.42,
        mq135=0.31,
    )
    readings = db.get_latest_sensor_readings(limit=1)
    assert len(readings) == 1
    assert readings[0]["temperature_c"] == 34.5
    assert readings[0]["humidity_percent"] == 67.0
    assert readings[0]["pressure_hpa"] == 998.2
    assert readings[0]["mq4"] == 0.42
    assert readings[0]["mq135"] == 0.31


# 5. Vision insertion
def test_vision_insertion(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "vision_test.db"))
    db.initialize()

    vid = db.insert_vision_detection(
        timestamp="2026-09-28T11:30:21Z",
        class_name="fire",
        confidence=0.88,
        bbox_x1=100.0,
        bbox_y1=120.0,
        bbox_x2=300.0,
        bbox_y2=400.0,
        image_path="data/missions/mission_001/images/img_001.jpg",
    )
    assert vid is not None and vid > 0


# 6. Vision retrieval
def test_vision_retrieval(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "vision_ret.db"))
    db.initialize()

    db.insert_vision_detection(
        timestamp="2026-09-28T11:30:21Z",
        class_name="smoke",
        confidence=0.75,
        bbox_x1=50.0,
        bbox_y1=60.0,
        bbox_x2=200.0,
        bbox_y2=250.0,
        image_path="data/missions/mission_001/images/smoke.jpg",
    )
    detections = db.get_latest_detections(limit=1)
    assert len(detections) == 1
    assert detections[0]["class_name"] == "smoke"
    assert detections[0]["confidence"] == 0.75
    assert detections[0]["image_path"] == "data/missions/mission_001/images/smoke.jpg"


# 7. Hazard insertion
def test_hazard_insertion(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "hazard_test.db"))
    db.initialize()

    hid = db.insert_hazard_event(
        timestamp="2026-09-28T11:30:22Z",
        hazard_type="fire",
        severity="HIGH",
        confidence=0.87,
        decision_id="dec_001",
        reasons_json=json.dumps(["Visual fire detected", "High temperature"]),
    )
    assert hid is not None and hid > 0


# 8. Hazard retrieval
def test_hazard_retrieval(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "hazard_ret.db"))
    db.initialize()

    db.insert_hazard_event(
        timestamp="2026-09-28T11:30:22Z",
        hazard_type="gas",
        severity="CRITICAL",
        confidence=0.92,
        decision_id="dec_002",
        reasons_json=json.dumps(["MQ-4 methane sensor index critical"]),
    )
    hazard = db.get_latest_hazard()
    assert hazard is not None
    assert hazard["hazard_type"] == "gas"
    assert hazard["severity"] == "CRITICAL"
    assert hazard["confidence"] == 0.92
    assert "MQ-4 methane sensor" in hazard["reasons_json"]


# 9. Mission creation
def test_mission_creation(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "mission_create.db"))
    db.initialize()

    mid = db.create_mission(
        mission_code="EXP-2026-01",
        status="PLANNED",
        notes="Mine Sector A reconnaissance",
    )
    assert mid is not None and mid > 0
    mission = db.get_mission(mission_id=mid)
    assert mission["mission_code"] == "EXP-2026-01"
    assert mission["status"] == "PLANNED"


# 10. Active mission retrieval
def test_active_mission_retrieval(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "mission_active.db"))
    db.initialize()

    db.create_mission(mission_code="EXP-2026-02", status="PLANNED")
    db.start_mission("EXP-2026-02")

    active = db.get_active_mission()
    assert active is not None
    assert active["mission_code"] == "EXP-2026-02"
    assert active["status"] == "ACTIVE"


# 11. Mission completion
def test_mission_completion(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "mission_end.db"))
    db.initialize()

    db.create_mission(mission_code="EXP-2026-03", status="ACTIVE")
    ended = db.end_mission("EXP-2026-03", status="COMPLETED")
    assert ended is True

    m = db.get_mission(mission_code="EXP-2026-03")
    assert m["status"] == "COMPLETED"
    assert m["ended_at"] is not None


# 12. Mission logs
def test_mission_logs(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "mission_logs.db"))
    db.initialize()

    mid = db.create_mission(mission_code="EXP-2026-04", status="ACTIVE")
    db.insert_mission_log(
        mission_id=mid,
        level="INFO",
        event_type="MISSION_STARTED",
        message="Mission started at entrance portal",
    )
    db.insert_mission_log(
        mission_id=mid,
        level="HAZARD",
        event_type="GAS_DETECTED",
        message="MQ4 index exceeded warning threshold",
    )

    logs = db.get_mission_logs(mission_id=mid)
    assert len(logs) == 2
    assert logs[0]["event_type"] == "GAS_DETECTED"
    assert logs[1]["event_type"] == "MISSION_STARTED"


# 13. Location records
def test_location_records(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "locations.db"))
    db.initialize()

    loc_id = db.create_location(
        location_type="MINE_MARKER",
        x=12.5,
        y=45.0,
        z=-120.0,
        label="MINE-SECTOR-A-POINT-04",
    )
    assert loc_id is not None and loc_id > 0

    loc = db.get_location(loc_id)
    assert loc["location_type"] == "MINE_MARKER"
    assert loc["x"] == 12.5
    assert loc["z"] == -120.0
    assert loc["label"] == "MINE-SECTOR-A-POINT-04"


# 14. Image path association
def test_image_path_association(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "img_assoc.db"))
    db.initialize()

    img_rel_path = "data/missions/mission_001/images/img_000031.jpg"
    db.insert_vision_detection(
        timestamp="2026-09-28T11:35:10Z",
        class_name="fire",
        confidence=0.85,
        image_path=img_rel_path,
    )
    db.insert_hazard_event(
        timestamp="2026-09-28T11:35:10Z",
        decision_id="dec_img_01",
        hazard_type="fire",
        severity="HIGH",
        confidence=0.85,
    )

    obs = db.get_reconstructed_observation(decision_id="dec_img_01")
    assert obs is not None
    assert obs["image_path"] == img_rel_path
    assert obs["hazard_event"]["hazard_type"] == "fire"


# 15. System status
def test_system_status(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "sys_status.db"))
    db.initialize()

    db.update_system_status(
        timestamp="2026-09-28T11:40:00Z",
        rover_status="RUNNING",
        camera_status="OK",
        sensor_status="OK",
        database_status="OK",
        storage_available_mb=14500.0,
        cpu_temperature_c=48.2,
    )

    status = db.get_latest_system_status()
    assert status is not None
    assert status["rover_status"] == "RUNNING"
    assert status["storage_available_mb"] == 14500.0
    assert status["cpu_temperature_c"] == 48.2


# 16. Sync status
def test_sync_status(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "sync_stat.db"))
    db.initialize()

    db.insert_sensor_reading(
        timestamp="2026-09-28T11:00:00Z",
        temperature_c=30.0,
        humidity_percent=50.0,
        sync_status="pending",
    )
    stats = db.get_sync_statistics()
    assert stats["pending_count"] >= 1

    unsynced = db.get_unsynced_records()
    assert len(unsynced) >= 1
    db.mark_record_synced("sensor_readings", unsynced[0]["id"])

    stats_after = db.get_sync_statistics()
    assert stats_after["synced_count"] >= 1


# 17. Duplicate protection
def test_duplicate_protection(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "dup_test.db"))
    db.initialize()

    db.create_mission(mission_code="EXP-UNIQUE-01", status="PLANNED")
    # Inserting same mission_code raises IntegrityError
    with pytest.raises(sqlite3.IntegrityError):
        db.create_mission(mission_code="EXP-UNIQUE-01", status="PLANNED")


# 18. Restart persistence
def test_restart_persistence(tmp_path):
    db_file = str(tmp_path / "restart.db")
    db1 = SQLiteDatabase(path=db_file)
    db1.initialize()
    db1.insert_sensor_reading(timestamp="2026-09-28T12:00:00Z", temperature_c=33.3)
    db1.create_mission(mission_code="EXP-RESTART-01", status="ACTIVE")

    # Re-instantiate on new connection to simulate process restart
    db2 = SQLiteDatabase(path=db_file)
    db2.initialize()
    latest = db2.get_latest_sensor_readings(limit=1)
    assert len(latest) == 1
    assert latest[0]["temperature_c"] == 33.3
    mission = db2.get_mission(mission_code="EXP-RESTART-01")
    assert mission is not None


# 19. Offline operation
def test_offline_operation(tmp_path):
    # Runs in completely disconnected sandbox
    db = SQLiteDatabase(path=str(tmp_path / "offline.db"))
    db.initialize()

    s_id = db.insert_sensor_reading(timestamp="2026-09-28T12:10:00Z", temperature_c=28.0)
    v_id = db.insert_vision_detection(timestamp="2026-09-28T12:10:00Z", class_name="fire", confidence=0.8)
    h_id = db.insert_hazard_event(timestamp="2026-09-28T12:10:00Z", hazard_type="fire", severity="HIGH", confidence=0.8)

    assert s_id > 0 and v_id > 0 and h_id > 0


# 20. Transaction rollback
def test_transaction_rollback(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "rollback.db"))
    db.initialize()

    # Simulate failure in atomic transaction
    with pytest.raises(ValueError):
        with db.connection.transaction() as conn:
            conn.execute(
                "INSERT INTO missions (mission_code, status, started_at) VALUES ('FAIL_MISSION', 'PLANNED', 'now')"
            )
            # Intentional error to trigger rollback
            raise ValueError("Forced error mid-transaction")

    # Verify FAIL_MISSION was rolled back and does not exist
    mission = db.get_mission(mission_code="FAIL_MISSION")
    assert mission is None


# 21. Timestamp queries
def test_timestamp_queries(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "ts_queries.db"))
    db.initialize()

    db.insert_sensor_reading(timestamp="2026-09-28T10:00:00Z", temperature_c=20.0)
    db.insert_sensor_reading(timestamp="2026-09-28T11:00:00Z", temperature_c=25.0)
    db.insert_sensor_reading(timestamp="2026-09-28T12:00:00Z", temperature_c=30.0)

    results = db.get_sensor_history(
        start_time="2026-09-28T10:30:00Z", end_time="2026-09-28T11:30:00Z"
    )
    assert len(results) == 1
    assert results[0]["temperature_c"] == 25.0


# 22. Latest-value queries
def test_latest_value_queries(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "latest_queries.db"))
    db.initialize()

    db.insert_sensor_reading(timestamp="2026-09-28T09:00:00Z", temperature_c=22.0)
    db.insert_sensor_reading(timestamp="2026-09-28T10:00:00Z", temperature_c=35.0)

    latest = db.get_latest_sensor_readings(limit=1)
    assert len(latest) == 1
    assert latest[0]["temperature_c"] == 35.0


# 23. Historical queries
def test_historical_queries(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "history_queries.db"))
    db.initialize()

    for i in range(15):
        db.insert_sensor_reading(timestamp=f"2026-09-28T10:{i:02d}:00Z", temperature_c=20.0 + i)

    history = db.get_sensor_history(limit=5)
    assert len(history) == 5


# 24. Migration safety
def test_migration_safety(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "migration_safety.db"))
    # Multiple sequential initialization runs must not throw errors
    db.initialize()
    db.initialize()
    db.initialize()

    conn = db.connect()
    try:
        rows = conn.execute("SELECT * FROM schema_migrations").fetchall()
        assert len(rows) >= 1
    finally:
        conn.close()
