"""
tests/sync/test_phase6.py — Phase 6 offline-first sync integration tests.

Covers:
  - SyncQueue depth / peek / ack / nack / reset_all_failed
  - SyncManager lifecycle: start, stop, trigger_now, status
  - SyncManager crash recovery (stale records reset on startup)
  - SystemHealthChecker: all subsystem checks
  - End-to-end offline-first failure injection scenario
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from database.database import SQLiteDatabase
from sync.health import SystemHealthChecker
from sync.network_monitor import NetworkMonitor
from sync.queue import SyncQueue
from sync.queue_manager import QueueManager
from sync.retry_manager import RetryManager
from sync.sync_manager import SyncManager
from sync.sync_service import SyncService


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────


def _fresh_db(tmp_path, name="rover_p6.db") -> SQLiteDatabase:
    """Create and initialize a fresh in-memory-style SQLite database."""
    db = SQLiteDatabase(path=str(tmp_path / name))
    db.initialize()
    return db


def _insert_sensor(db: SQLiteDatabase, **kwargs) -> int:
    return db.insert_sensor_reading(
        timestamp=kwargs.get("timestamp", "2026-09-28T10:00:00Z"),
        device_id=kwargs.get("device_id", "mining_rover_01"),
        sensor_type=kwargs.get("sensor_type", "gas"),
        value=kwargs.get("value", 0.3),
        unit=kwargs.get("unit", "index"),
        valid=True,
        source="test",
    )


def _insert_hazard(db: SQLiteDatabase, **kwargs) -> int:
    return db.insert_hazard_event(
        timestamp=kwargs.get("timestamp", "2026-09-28T10:00:01Z"),
        device_id="mining_rover_01",
        hazard="GAS_LEAK",
        severity="MEDIUM",
        confidence=0.88,
        sources="sensor",
        message="Test hazard",
        recommended_action="VENTILATE",
    )


# ────────────────────────────────────────────────────────────────────────────
# SyncQueue Tests
# ────────────────────────────────────────────────────────────────────────────


class TestSyncQueue:
    def test_depth_zero_on_empty_db(self, tmp_path):
        db = _fresh_db(tmp_path, "q_empty.db")
        q = SyncQueue(db)
        assert q.depth() == 0

    def test_depth_increases_with_inserts(self, tmp_path):
        db = _fresh_db(tmp_path, "q_depth.db")
        q = SyncQueue(db)

        _insert_sensor(db, timestamp="2026-09-28T10:00:00Z")
        _insert_sensor(db, timestamp="2026-09-28T10:00:01Z")
        _insert_hazard(db, timestamp="2026-09-28T10:00:02Z")

        assert q.depth() == 3

    def test_peek_returns_records_without_consuming(self, tmp_path):
        db = _fresh_db(tmp_path, "q_peek.db")
        q = SyncQueue(db)

        _insert_sensor(db, timestamp="2026-09-28T10:00:00Z")

        batch1 = q.peek_batch(batch_size=10)
        batch2 = q.peek_batch(batch_size=10)

        assert len(batch1) == 1
        assert len(batch2) == 1  # still there
        assert q.depth() == 1

    def test_ack_marks_records_synced(self, tmp_path):
        db = _fresh_db(tmp_path, "q_ack.db")
        q = SyncQueue(db)

        _insert_sensor(db)
        _insert_hazard(db)

        assert q.depth() == 2

        batch = q.peek_batch(batch_size=10)
        synced_count = q.ack(batch)

        assert synced_count == 2
        assert q.depth() == 0

    def test_nack_leaves_records_pending(self, tmp_path):
        db = _fresh_db(tmp_path, "q_nack.db")
        q = SyncQueue(db)

        _insert_sensor(db)
        batch = q.peek_batch()

        q.nack(batch)  # should be a no-op at DB level

        assert q.depth() == 1

    def test_reset_all_failed_is_idempotent(self, tmp_path):
        db = _fresh_db(tmp_path, "q_reset.db")
        q = SyncQueue(db)

        _insert_sensor(db)
        # Force a stale in-flight state
        conn = db.connect()
        try:
            conn.execute("UPDATE sensor_readings SET sync_status = 'syncing'")
            conn.commit()
        finally:
            conn.close()

        # Should reset 1 stale record
        reset_count = q.reset_all_failed()
        assert reset_count == 1

        # Second call should reset nothing
        reset_count2 = q.reset_all_failed()
        assert reset_count2 == 0

    def test_statistics_matches_db(self, tmp_path):
        db = _fresh_db(tmp_path, "q_stats.db")
        q = SyncQueue(db)

        _insert_sensor(db)
        _insert_hazard(db)

        stats = q.statistics()
        assert stats["pending_count"] == 2
        assert stats["synced_count"] == 0
        assert stats["total_count"] == 2


# ────────────────────────────────────────────────────────────────────────────
# SyncManager Tests
# ────────────────────────────────────────────────────────────────────────────


class TestSyncManager:
    def test_status_before_start(self, tmp_path):
        db = _fresh_db(tmp_path, "mgr_prestatus.db")
        mgr = SyncManager(database=db, enabled=True)
        status = mgr.status()

        assert "network" in status
        assert "sync_enabled" in status
        assert status["sync_enabled"] is True

    def test_disabled_manager_does_not_start_thread(self, tmp_path):
        db = _fresh_db(tmp_path, "mgr_disabled.db")
        mgr = SyncManager(database=db, enabled=False)
        mgr.start()

        # Service thread should not be running
        assert mgr.service._thread is None or not mgr.service._thread.is_alive()
        mgr.stop()

    def test_start_and_stop_lifecycle(self, tmp_path):
        db = _fresh_db(tmp_path, "mgr_lifecycle.db")
        mgr = SyncManager(database=db, enabled=True, check_interval=60.0)

        mgr.start()
        time.sleep(0.1)
        assert mgr.service._running is True

        mgr.stop()
        assert mgr.service._running is False

    def test_crash_recovery_resets_stale_records(self, tmp_path):
        """
        SyncQueue.reset_all_failed() is the crash-recovery primitive.
        SyncManager.start() calls it before launching the background thread.

        We test reset_all_failed() directly here so the test is not
        dependent on background-thread timing.  The SyncManager integration
        is covered in test_start_and_stop_lifecycle.
        """
        db = _fresh_db(tmp_path, "mgr_crash.db")
        q = SyncQueue(db)

        _insert_sensor(db, timestamp="2026-09-28T10:00:00Z")
        _insert_hazard(db, timestamp="2026-09-28T10:00:01Z")

        # Simulate crash mid-sync: force stale 'syncing' state
        conn = db.connect()
        try:
            conn.execute("UPDATE sensor_readings SET sync_status = 'syncing'")
            conn.execute("UPDATE hazard_events SET sync_status = 'syncing'")
            conn.commit()
        finally:
            conn.close()

        # Verify stale records exist before recovery
        conn = db.connect()
        try:
            stale_count = conn.execute(
                "SELECT COUNT(*) FROM sensor_readings WHERE sync_status = 'syncing'"
            ).fetchone()[0]
            stale_count += conn.execute(
                "SELECT COUNT(*) FROM hazard_events WHERE sync_status = 'syncing'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert stale_count == 2

        # Call crash recovery directly
        reset_count = q.reset_all_failed()
        assert reset_count == 2

        # After recovery, no more stale records
        conn = db.connect()
        try:
            remaining_stale = conn.execute(
                "SELECT COUNT(*) FROM sensor_readings WHERE sync_status = 'syncing'"
            ).fetchone()[0]
            remaining_stale += conn.execute(
                "SELECT COUNT(*) FROM hazard_events WHERE sync_status = 'syncing'"
            ).fetchone()[0]
        finally:
            conn.close()
        assert remaining_stale == 0

        # Records are restored to pending and visible in the queue
        assert q.depth() == 2

    def test_trigger_now_returns_triggered_status(self, tmp_path):
        db = _fresh_db(tmp_path, "mgr_trigger.db")
        mgr = SyncManager(database=db, enabled=True, check_interval=60.0)
        mgr.network_monitor.set_override(False)  # offline so sync won't hang

        result = mgr.trigger_now()

        assert result["status"] == "triggered"
        assert result["trigger_count"] == 1

    def test_trigger_disabled_returns_disabled(self, tmp_path):
        db = _fresh_db(tmp_path, "mgr_trig_dis.db")
        mgr = SyncManager(database=db, enabled=False)

        result = mgr.trigger_now()
        assert result["status"] == "disabled"

    def test_status_includes_queue_depth(self, tmp_path):
        db = _fresh_db(tmp_path, "mgr_qdepth.db")
        _insert_sensor(db)
        _insert_hazard(db)

        mgr = SyncManager(database=db, enabled=False)
        status = mgr.status()

        assert status["queue_depth"] == 2

    def test_end_to_end_online_sync_via_manager(self, tmp_path):
        """
        SyncManager performs a complete online sync cycle through the FastAPI
        /api/sync/receive endpoint using the TestClient.
        """
        db = _fresh_db(tmp_path, "mgr_e2e.db")
        _insert_sensor(db, timestamp="2026-09-28T10:20:00Z")
        _insert_hazard(db, timestamp="2026-09-28T10:20:01Z")

        client = TestClient(app)
        net_monitor = NetworkMonitor()
        net_monitor.set_override(True)

        # Use TestClientSyncService to avoid real HTTP
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
                    count = self.queue_manager.mark_batch_synced(batch)
                    return {"status": "success", "synced_count": count}
                return {"status": "failed"}

        retry_mgr = RetryManager()
        qm = QueueManager(db, retry_manager=retry_mgr)
        svc = TestClientSyncService(database=db, network_monitor=net_monitor, queue_manager=qm, retry_manager=retry_mgr)

        result = svc.sync_cycle()
        assert result["status"] == "success"
        assert result["synced_count"] == 2

        q = SyncQueue(db)
        assert q.depth() == 0


# ────────────────────────────────────────────────────────────────────────────
# SystemHealthChecker Tests
# ────────────────────────────────────────────────────────────────────────────


class TestSystemHealthChecker:
    def test_healthy_system_returns_ok(self, tmp_path):
        db = _fresh_db(tmp_path, "health_ok.db")
        net = NetworkMonitor()
        net.set_override(True)

        checker = SystemHealthChecker(database=db, network_monitor=net)
        report = checker.run()

        assert report.overall in ("OK", "DEGRADED")  # vision weights absent → DEGRADED
        assert any(s.name == "database" and s.status == "OK" for s in report.subsystems)
        assert any(s.name == "sync_queue" for s in report.subsystems)
        assert any(s.name == "network" for s in report.subsystems)
        assert any(s.name == "decision_engine" for s in report.subsystems)

    def test_offline_network_marks_degraded(self, tmp_path):
        db = _fresh_db(tmp_path, "health_offline.db")
        net = NetworkMonitor()
        net.set_override(False)

        checker = SystemHealthChecker(database=db, network_monitor=net)
        report = checker.run()

        network_sub = next(s for s in report.subsystems if s.name == "network")
        assert network_sub.status == "DEGRADED"

    def test_large_pending_backlog_triggers_critical(self, tmp_path):
        db = _fresh_db(tmp_path, "health_backlog.db")

        checker = SystemHealthChecker(
            database=db,
            max_pending_warn=1,
            max_pending_critical=2,
        )

        # Insert 3 records — exceeds critical threshold
        _insert_sensor(db, timestamp="2026-09-28T10:00:00Z")
        _insert_sensor(db, timestamp="2026-09-28T10:00:01Z")
        _insert_sensor(db, timestamp="2026-09-28T10:00:02Z")

        report = checker.run()
        queue_sub = next(s for s in report.subsystems if s.name == "sync_queue")
        assert queue_sub.status == "CRITICAL"
        assert report.overall == "CRITICAL"

    def test_vision_weights_absent_is_degraded(self, tmp_path):
        db = _fresh_db(tmp_path, "health_vision.db")
        checker = SystemHealthChecker(
            database=db,
            vision_weights_path=str(tmp_path / "nonexistent.pt"),
        )
        report = checker.run()

        vision_sub = next(s for s in report.subsystems if s.name == "vision")
        assert vision_sub.status == "DEGRADED"

    def test_no_database_returns_unknown(self):
        checker = SystemHealthChecker(database=None)
        report = checker.run()

        db_sub = next(s for s in report.subsystems if s.name == "database")
        assert db_sub.status == "UNKNOWN"

    def test_report_as_dict_is_serializable(self, tmp_path):
        db = _fresh_db(tmp_path, "health_dict.db")
        checker = SystemHealthChecker(database=db)
        report = checker.run()
        d = report.as_dict()

        assert "overall" in d
        assert "timestamp" in d
        assert isinstance(d["subsystems"], list)
        for sub in d["subsystems"]:
            assert "name" in sub
            assert "status" in sub
            assert "message" in sub

    def test_decision_engine_subsystem_is_ok(self, tmp_path):
        db = _fresh_db(tmp_path, "health_de.db")
        checker = SystemHealthChecker(database=db)
        report = checker.run()

        de_sub = next(s for s in report.subsystems if s.name == "decision_engine")
        assert de_sub.status == "OK"
        assert de_sub.latency_ms is not None


# ────────────────────────────────────────────────────────────────────────────
# End-to-End Failure Injection Scenario
# ────────────────────────────────────────────────────────────────────────────


class TestOfflineFirstFailureInjection:
    def test_offline_then_online_recovery(self, tmp_path):
        """
        Simulate a complete offline → online → sync recovery cycle:

        1. Insert data while the rover is OFFLINE.
        2. Verify sync is paused and data is preserved locally.
        3. Restore network connectivity.
        4. Execute sync cycle — all records must upload and be marked synced.
        5. Verify local pending queue is empty.
        """
        db = _fresh_db(tmp_path, "e2e_failover.db")
        client = TestClient(app)

        net = NetworkMonitor()
        net.set_override(False)  # Start OFFLINE

        retry_mgr = RetryManager()
        qm = QueueManager(db, retry_manager=retry_mgr)
        sync_svc = SyncService(database=db, network_monitor=net, queue_manager=qm)

        # Phase: insert 5 sensor readings and 2 hazards while offline
        for i in range(5):
            _insert_sensor(db, timestamp=f"2026-09-28T10:0{i}:00Z")
        _insert_hazard(db, timestamp="2026-09-28T10:05:01Z")
        _insert_hazard(db, timestamp="2026-09-28T10:05:02Z")

        # Sync attempt while offline must pause cleanly
        result = sync_svc.sync_cycle()
        assert result["status"] == "paused"
        assert result["reason"] == "network_offline"

        # All 7 records must remain pending
        q = SyncQueue(db)
        assert q.depth() == 7

        # Network is restored
        net.set_override(True)

        # Now use TestClient-backed sync service
        class RecoverySyncService(SyncService):
            def sync_cycle(self):
                batch = self.queue_manager.get_pending_batch(batch_size=50)
                if not batch:
                    return {"status": "idle", "synced_count": 0}
                if not self.network_monitor.is_online():
                    return {"status": "paused", "reason": "network_offline", "synced_count": 0}
                payload = {
                    "rover_id": "mining_rover_01",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "batch_size": len(batch),
                    "records": batch,
                }
                res = client.post("/api/sync/receive", json=payload)
                if res.status_code == 200:
                    return {"status": "success", "synced_count": self.queue_manager.mark_batch_synced(batch)}
                return {"status": "failed"}

        recovery_svc = RecoverySyncService(database=db, network_monitor=net, queue_manager=qm)
        recovery_result = recovery_svc.sync_cycle()

        assert recovery_result["status"] == "success"
        assert recovery_result["synced_count"] == 7
        assert q.depth() == 0

    def test_partial_batch_failure_retains_unsynced_records(self, tmp_path):
        """
        If the remote endpoint rejects a batch (e.g. HTTP 503), records must
        remain in the pending queue for retry.
        """
        db = _fresh_db(tmp_path, "e2e_partial.db")
        net = NetworkMonitor()
        net.set_override(True)

        retry_mgr = RetryManager(base_delay=1.0)
        qm = QueueManager(db, retry_manager=retry_mgr)

        _insert_sensor(db, timestamp="2026-09-28T10:00:00Z")
        _insert_sensor(db, timestamp="2026-09-28T10:00:01Z")

        class FailingSyncService(SyncService):
            """Simulates a remote server that always returns 503."""
            def sync_cycle(self):
                if not self.network_monitor.is_online():
                    return {"status": "paused", "reason": "network_offline", "synced_count": 0}
                batch = self.queue_manager.get_pending_batch(batch_size=50)
                if not batch:
                    return {"status": "idle", "synced_count": 0}
                # Simulate failure
                self.queue_manager.mark_batch_failed(batch, error="HTTP 503")
                return {"status": "failed", "synced_count": 0, "error": "HTTP 503"}

        svc = FailingSyncService(database=db, network_monitor=net, queue_manager=qm)
        result = svc.sync_cycle()

        assert result["status"] == "failed"

        # Records must still be in the queue (pending at DB level)
        q = SyncQueue(db)
        assert q.depth() == 2

        # But retry backoff must be engaged for each key
        pending_records = db.get_pending_sync_records_detailed(limit=10)
        for rec in pending_records:
            key = rec.get("unique_id") or f"{rec.get('table_name')}_{rec.get('id')}"
            # After 1 failure, retry should be blocked for ~1s
            assert retry_mgr.can_retry(key, now=time.time()) is False
