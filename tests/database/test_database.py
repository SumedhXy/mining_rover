from datetime import datetime, timezone

from database.database import SQLiteDatabase


def test_database_initializes_and_inserts_sensor_reading(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "test.db"))
    db.initialize()

    inserted = db.insert_sensor_reading(
        timestamp=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        device_id="mining_rover_01",
        sensor_type="temperature",
        value=42.6,
        unit="C",
        valid=True,
        source="simulator",
    )

    assert inserted is not None
    assert db.get_latest_sensor_readings(limit=1)[0]["sensor_type"] == "temperature"


def test_database_stores_vision_and_hazard_records(tmp_path):
    db = SQLiteDatabase(path=str(tmp_path / "test.db"))
    db.initialize()

    db.insert_vision_detection(
        timestamp=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        device_id="mining_rover_01",
        class_name="rock",
        confidence=0.92,
        x_center=0.52,
        y_center=0.48,
        width=0.31,
        height=0.42,
        source="yolo",
    )

    db.insert_hazard_event(
        timestamp=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        device_id="mining_rover_01",
        hazard="ROCKFALL",
        severity="HIGH",
        confidence=0.91,
        sources="vision,vibration",
        message="Rock detected with elevated vibration",
        recommended_action="STOP_AND_INSPECT",
    )

    assert db.get_recent_hazards(limit=1)[0]["hazard"] == "ROCKFALL"
    assert db.get_recent_detections(limit=1)[0]["class_name"] == "rock"


def test_database_tracks_sync_state_and_survives_restart(tmp_path):
    db_path = tmp_path / "state.db"
    db = SQLiteDatabase(path=str(db_path))
    db.initialize()
    db.insert_sensor_reading(
        timestamp="2026-09-27T10:30:15+05:30",
        device_id="mining_rover_01",
        sensor_type="gas",
        value=320,
        unit="ppm",
        valid=True,
        source="simulator",
    )

    rows = db.get_unsynced_records()
    assert len(rows) >= 1

    db.mark_record_synced("sensor_readings", rows[0]["id"])
    assert db.get_unsynced_records() == [] or db.get_unsynced_records()[0]["id"] != rows[0]["id"]

    db2 = SQLiteDatabase(path=str(db_path))
    db2.initialize()
    assert len(db2.get_latest_sensor_readings(limit=10)) >= 1
