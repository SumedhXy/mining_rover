"""
sync/sync_manager.py — High-level sync orchestration façade for Phase 6.

``SyncManager`` wraps ``SyncService`` and adds:
* Crash-recovery on startup (resets stale in-flight records)
* Configurable start/stop lifecycle tied to the rover's main process
* Aggregated status reporting for the dashboard and system monitor
* Convenience ``trigger_now()`` for manual / on-demand sync from the API

It intentionally does **not** replace ``SyncService`` – it delegates to it.
"""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from database.database import SQLiteDatabase
from sync.network_monitor import NetworkMonitor
from sync.queue import SyncQueue
from sync.queue_manager import QueueManager
from sync.retry_manager import RetryManager
from sync.sync_service import SyncService

logger = logging.getLogger("sync.manager")


class SyncManager:
    """
    Phase 6 sync manager – lifecycle owner of the background sync worker.

    Usage::

        manager = SyncManager(database=db, config=cfg.sync)
        manager.start()          # launches background thread
        manager.trigger_now()    # optional manual kick
        manager.stop()           # graceful shutdown
        status = manager.status()
    """

    def __init__(
        self,
        database: SQLiteDatabase,
        server_url: str = "http://127.0.0.1:8000/api/sync/receive",
        enabled: bool = True,
        check_interval: float = 5.0,
        batch_size: int = 50,
        timeout_seconds: float = 4.0,
        rover_id: str = "mining_rover_01",
    ) -> None:
        self.database = database
        self.enabled = enabled
        self._server_url = server_url

        # Sub-components
        self._retry_manager = RetryManager(base_delay=2.0, max_delay=60.0, backoff_multiplier=2.0)
        self._queue = SyncQueue(database)
        self._queue_manager = QueueManager(database, retry_manager=self._retry_manager)
        self._network_monitor = NetworkMonitor(endpoint_url=server_url, check_timeout=timeout_seconds)

        self._service = SyncService(
            database=database,
            server_url=server_url,
            network_monitor=self._network_monitor,
            queue_manager=self._queue_manager,
            retry_manager=self._retry_manager,
            check_interval=check_interval,
            batch_size=batch_size,
            timeout_seconds=timeout_seconds,
            rover_id=rover_id,
            enabled=enabled,
        )

        self._started_at: Optional[str] = None
        self._trigger_count: int = 0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the background sync worker; recover stale records first."""
        if not self.enabled:
            logger.info("SyncManager: sync disabled by configuration.")
            return

        # Crash recovery: reset any records left in a transient state
        recovered = self._queue.reset_all_failed()
        if recovered:
            logger.info("SyncManager: recovered %d stale records → 'pending'", recovered)

        self._service.start()
        self._started_at = datetime.now(timezone.utc).isoformat()
        logger.info("SyncManager: background sync worker started.")

    def stop(self) -> None:
        """Gracefully stop the background sync worker."""
        self._service.stop()
        logger.info("SyncManager: background sync worker stopped.")

    # ------------------------------------------------------------------
    # On-Demand / Manual Sync
    # ------------------------------------------------------------------

    def trigger_now(self) -> Dict[str, Any]:
        """
        Run one synchronization cycle immediately in a daemon thread.

        Safe to call from any thread or HTTP handler.  Returns immediately;
        the actual sync happens asynchronously.
        """
        if not self.enabled:
            return {"status": "disabled", "message": "Sync service is disabled"}

        with self._lock:
            self._trigger_count += 1

        t = threading.Thread(target=self._service.sync_cycle, daemon=True, name="ManualSyncTrigger")
        t.start()
        logger.info("SyncManager: manual sync triggered (trigger #%d)", self._trigger_count)
        return {
            "status": "triggered",
            "trigger_count": self._trigger_count,
            "message": "Synchronization cycle initiated",
        }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """
        Aggregated status for the dashboard, health endpoint, and logs.

        Merges SyncService runtime state with queue depth and uptime.
        """
        svc_status = self._service.get_status()
        queue_stats = self._queue.statistics()

        return {
            **svc_status,
            "queue_depth": queue_stats.get("pending_count", 0),
            "total_synced_ever": queue_stats.get("synced_count", 0),
            "manager_started_at": self._started_at,
            "manual_trigger_count": self._trigger_count,
            "sync_enabled": self.enabled,
        }

    # ------------------------------------------------------------------
    # Convenience accessors (for testing / advanced consumers)
    # ------------------------------------------------------------------

    @property
    def service(self) -> SyncService:
        """Direct access to the underlying SyncService (e.g. for tests)."""
        return self._service

    @property
    def queue(self) -> SyncQueue:
        """Direct access to the durable SyncQueue."""
        return self._queue

    @property
    def network_monitor(self) -> NetworkMonitor:
        """Direct access to the NetworkMonitor (e.g. override in tests)."""
        return self._network_monitor


__all__ = ["SyncManager"]
