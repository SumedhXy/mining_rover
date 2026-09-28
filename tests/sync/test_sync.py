from __future__ import annotations

import json
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from backend.main import app
from database.database import SQLiteDatabase
from sync.network_monitor import NetworkMonitor
from sync.queue_manager import QueueManager
from sync.retry_manager import RetryManager
from sync.sync_service import SyncService


def test_scenario_1_normal_online_sync(tmp_path):
    """
    Scenario 1: Normal online operation.
    Records collected locally in SQLite are batched and uploaded to the receiver,
    then atomically marked SYNCED.
    """
    db_path = str(tmp_path / "rover_test1.db")
    db = SQLiteDatabase(path=db_path)
    db.initialize()

    # Insert mock sensor and hazard records
    db.insert_sensor_reading(
        timestamp="2026-09-28T10:00:00Z",
        device_id="mining_rover_01",
        sensor_type="gas",
        value=0.45,
        unit="index",
        valid=True,
        source="simulator",
    )
    db.insert_hazard_event(
        timestamp="2026-09-28T10:00:01Z",
        device_id="mining_rover_01",
        hazard="GAS_LEAK",
        severity="MEDIUM",
        confidence=0.88,
        sources="sensor",
        message="Elevated gas index",
        recommended_action="VENTILATE",
    )

    stats_before = db.get_sync_statistics()
    assert stats_before["pending_count"] == 2

    # Set up sync service with mocked receiver client
    client = TestClient(app)

    net_monitor = NetworkMonitor()
    net_monitor.set_override(True)

    # Custom sync service targeting TestClient endpoint
    class TestClientSyncService(SyncService):
        def sync_cycle(self):
            batch = self.queue_manager.get_pending_batch(batch_size=50)
            if not batch:
                return {"status": "idle", "synced_count": 0}

            payload = {
                "rover_id": self.rover_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "batch_size": len(batch),
                "records": batch,
            }
            res = client.post("/api/sync/receive", json=payload)
            if res.status_code == 200:
                synced_count = self.queue_manager.mark_batch_synced(batch)
                return {"status": "success", "synced_count": synced_count}
            return {"status": "failed"}

    sync_svc = TestClientSyncService(database=db, network_monitor=net_monitor)
    outcome = sync_svc.sync_cycle()

    assert outcome["status"] == "success"
    assert outcome["synced_count"] == 2

    stats_after = db.get_sync_statistics()
    assert stats_after["pending_count"] == 0
    assert stats_after["synced_count"] == 2


def test_scenario_2_network_disconnect_offline_resilience(tmp_path):
    """
    Scenario 2: Network failure / disconnection.
    Local rover operations, sensor collection, and SQLite storage continue unaffected.
    Sync pauses gracefully without throwing exceptions or losing data.
    """
    db = SQLiteDatabase(path=str(tmp_path / "rover_test2.db"))
    db.initialize()

    net_monitor = NetworkMonitor()
    net_monitor.set_override(False)  # Disconnect network

    sync_svc = SyncService(database=db, network_monitor=net_monitor)

    # Insert data while disconnected
    db.insert_sensor_reading(
        timestamp="2026-09-28T10:05:00Z",
        device_id="mining_rover_01",
        sensor_type="temperature",
        value=36.2,
        unit="C",
        valid=True,
        source="simulator",
    )
    db.insert_vision_detection(
        timestamp="2026-09-28T10:05:02Z",
        device_id="mining_rover_01",
        class_name="smoke",
        confidence=0.85,
        x_center=50,
        y_center=50,
        width=20,
        height=20,
        source="yolo",
    )

    # Run sync attempt while offline
    outcome = sync_svc.sync_cycle()
    assert outcome["status"] == "paused"
    assert outcome["reason"] == "network_offline"

    # Local data must be 100% intact and pending
    stats = db.get_sync_statistics()
    assert stats["pending_count"] == 2
    assert stats["synced_count"] == 0
    assert sync_svc.get_status()["network"] == "offline"


def test_scenario_3_network_restoration_and_duplicate_protection(tmp_path):
    """
    Scenario 3: Network returns.
    Accumulated offline records synchronize, and the remote endpoint provides idempotency.
    """
    db = SQLiteDatabase(path=str(tmp_path / "rover_test3.db"))
    db.initialize()

    client = TestClient(app)

    db.insert_sensor_reading(
        timestamp="2026-09-28T10:10:00Z",
        device_id="mining_rover_01",
        sensor_type="gas",
        value=0.15,
        unit="",
        valid=True,
        source="simulator",
    )

    net_monitor = NetworkMonitor()
    net_monitor.set_override(True)

    # Use queue manager
    qm = QueueManager(db)
    batch = qm.get_pending_batch(batch_size=10)
    assert len(batch) == 1

    payload = {
        "rover_id": "mining_rover_01",
        "timestamp": "2026-09-28T10:10:00Z",
        "batch_size": len(batch),
        "records": batch,
    }

    # First send -> Accepted
    res1 = client.post("/api/sync/receive", json=payload)
    assert res1.status_code == 200
    assert res1.json()["accepted_count"] == 1
    assert res1.json()["ignored_duplicate_count"] == 0

    # Second send of identical payload -> Duplicate detected & ignored cleanly
    res2 = client.post("/api/sync/receive", json=payload)
    assert res2.status_code == 200
    assert res2.json()["accepted_count"] == 0
    assert res2.json()["ignored_duplicate_count"] == 1


def test_scenario_4_remote_failure_and_exponential_backoff():
    """
    Scenario 4: Remote server failure engages exponential backoff.
    """
    retry_mgr = RetryManager(base_delay=1.0, max_delay=10.0, backoff_multiplier=2.0)
    key = "sensor_42_test"

    assert retry_mgr.can_retry(key, now=100.0) is True

    # 1st failure -> delay ~ 1.0s
    d1 = retry_mgr.record_failure(key, error="HTTP 503", now=100.0)
    assert 0.8 <= d1 <= 1.2
    assert retry_mgr.can_retry(key, now=100.5) is False
    assert retry_mgr.can_retry(key, now=101.5) is True

    # 2nd failure -> delay ~ 2.0s
    d2 = retry_mgr.record_failure(key, error="HTTP 503", now=102.0)
    assert 1.6 <= d2 <= 2.4

    # 3rd failure -> delay ~ 4.0s
    d3 = retry_mgr.record_failure(key, error="HTTP 503", now=105.0)
    assert 3.2 <= d3 <= 4.8

    # Success resets retry history
    retry_mgr.record_success(key)
    assert retry_mgr.get_retry_count(key) == 0


def test_scenario_5_api_endpoints_and_status():
    """
    Scenario 5: FastAPI sync endpoints are responsive and report healthy offline/online status.
    """
    client = TestClient(app)

    status_resp = client.get("/api/sync/status")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert "network" in data
    assert "pending_count" in data
    assert "local_database" in data
    assert data["local_database"] == "healthy"

    # Trigger endpoint works
    trigger_resp = client.post("/api/sync/trigger")
    assert trigger_resp.status_code == 200
    assert "status" in trigger_resp.json()
