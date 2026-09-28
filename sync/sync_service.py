from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.database import SQLiteDatabase
from sync.network_monitor import NetworkMonitor
from sync.queue_manager import QueueManager
from sync.retry_manager import RetryManager

logger = logging.getLogger("sync.service")


class SyncService:
    """
    High-level synchronization orchestrator for the Mining Rover.
    Follows an offline-first philosophy:
    - Never blocks core sensor collection, YOLO inference, or decision pipelines.
    - Only attempts synchronization when the network monitor verifies online status.
    - Batches pending records from SQLite with unique identifiers for duplicate protection.
    - Updates local sync state atomically upon verified remote upload.
    - Employs exponential backoff on network failures.
    """

    def __init__(
        self,
        database: SQLiteDatabase,
        server_url: str = "http://127.0.0.1:8000/api/sync/receive",
        network_monitor: Optional[NetworkMonitor] = None,
        queue_manager: Optional[QueueManager] = None,
        retry_manager: Optional[RetryManager] = None,
        check_interval: float = 5.0,
        batch_size: int = 50,
        timeout_seconds: float = 4.0,
        rover_id: str = "mining_rover_01",
        enabled: bool = True,
    ):
        self.database = database
        self.server_url = server_url
        self.check_interval = check_interval
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds
        self.rover_id = rover_id
        self.enabled = enabled

        self.retry_manager = retry_manager or RetryManager()
        self.queue_manager = queue_manager or QueueManager(self.database, retry_manager=self.retry_manager)
        self.network_monitor = network_monitor or NetworkMonitor(endpoint_url=self.server_url, check_timeout=self.timeout_seconds)

        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._last_sync_time: Optional[str] = None
        self._last_error: Optional[str] = None
        self._status: str = "IDLE"  # "IDLE" | "SYNCING" | "PAUSED" | "ERROR"
        self._total_synced_session: int = 0

    def start(self) -> None:
        """Starts the background synchronization worker daemon."""
        if not self.enabled:
            logger.info("SyncService is disabled by configuration.")
            return

        with self._lock:
            if self._running:
                return
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="SyncServiceWorker")
            self._thread.start()
            logger.info("SyncService background worker started.")

    def stop(self) -> None:
        """Stops the background synchronization worker gracefully."""
        with self._lock:
            self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
            logger.info("SyncService background worker stopped.")

    def _run_loop(self) -> None:
        while self._running:
            try:
                self.sync_cycle()
            except Exception as e:
                logger.error(f"Unexpected error in sync cycle: {e}")
            time.sleep(self.check_interval)

    def sync_cycle(self) -> Dict[str, Any]:
        """
        Executes a single synchronization cycle.
        Returns a dictionary describing the cycle outcome.
        """
        with self._lock:
            # 1. Verify network reachability
            is_online = self.network_monitor.is_online()
            if not is_online:
                self._status = "PAUSED"
                logger.debug("Network is OFFLINE. Sync cycle paused; rover continues offline operation.")
                return {
                    "status": "paused",
                    "reason": "network_offline",
                    "synced_count": 0,
                    "pending_count": self.queue_manager.get_status().get("pending_count", 0),
                }

            # 2. Retrieve pending batch from SQLite
            batch = self.queue_manager.get_pending_batch(batch_size=self.batch_size)
            if not batch:
                self._status = "IDLE"
                return {
                    "status": "idle",
                    "reason": "no_pending_records",
                    "synced_count": 0,
                    "pending_count": 0,
                }

            # 3. Transmit payload to remote server
            self._status = "SYNCING"
            payload = {
                "rover_id": self.rover_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "batch_size": len(batch),
                "records": batch,
            }

            try:
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    self.server_url,
                    data=data,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "User-Agent": "MiningRover-SyncService/1.0",
                    },
                    method="POST",
                )

                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:
                    if response.status in (200, 201, 202):
                        resp_data = json.loads(response.read().decode("utf-8"))
                        synced_count = self.queue_manager.mark_batch_synced(batch)
                        self._last_sync_time = datetime.now(timezone.utc).isoformat()
                        self._last_error = None
                        self._status = "IDLE"
                        self._total_synced_session += synced_count
                        logger.info(f"Successfully synchronized {synced_count} records to {self.server_url}")

                        return {
                            "status": "success",
                            "synced_count": synced_count,
                            "remote_response": resp_data,
                            "pending_count": self.queue_manager.get_status().get("pending_count", 0),
                        }
                    else:
                        raise RuntimeError(f"Remote returned unexpected HTTP {response.status}")

            except Exception as e:
                err_msg = str(e)
                self._last_error = err_msg
                self._status = "ERROR"
                self.queue_manager.mark_batch_failed(batch, error=err_msg)
                logger.warning(f"Sync attempt failed: {err_msg}. Backoff initiated.")
                return {
                    "status": "failed",
                    "error": err_msg,
                    "synced_count": 0,
                    "pending_count": self.queue_manager.get_status().get("pending_count", 0),
                }

    def get_status(self) -> Dict[str, Any]:
        """Provides a real-time status summary for the dashboard and system monitoring."""
        queue_stats = self.queue_manager.get_status()
        is_online = self.network_monitor.is_online()

        return {
            "network": "online" if is_online else "offline",
            "sync_enabled": self.enabled,
            "sync_status": self._status if is_online else "PAUSED",
            "local_database": "healthy",
            "server_url": self.server_url,
            "pending_count": queue_stats.get("pending_count", 0),
            "synced_count": queue_stats.get("synced_count", 0),
            "in_flight_count": queue_stats.get("in_flight_count", 0),
            "total_records": queue_stats.get("total_count", 0),
            "session_synced": self._total_synced_session,
            "last_sync_time": self._last_sync_time,
            "last_error": self._last_error,
        }


__all__ = ["SyncService"]
