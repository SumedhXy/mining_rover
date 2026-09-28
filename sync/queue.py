"""
sync/queue.py — Durable SQLite-backed sync queue for the Mining Rover.

Provides a persistent, crash-safe queue abstraction layered directly on
the local SQLite database.  Unlike an in-memory queue, records are never
lost between process restarts: the queue state is the database itself.

Design decisions
----------------
* The "queue" is simply all rows in sensor_readings / vision_detections /
  hazard_events whose ``sync_status`` is ``'pending'``.
* ``SyncQueue`` exposes a minimal interface: ``enqueue``, ``peek_batch``,
  ``ack`` (mark synced), and ``nack`` (mark failed / reset to pending).
* No separate queue table is needed – the existing schema already carries
  ``sync_status`` on every telemetry row.
* Thread-safe at the database level via SQLite WAL mode; no extra locks
  required here beyond the connection-per-call pattern already in place.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from database.database import SQLiteDatabase

logger = logging.getLogger("sync.queue")

_ALLOWED_TABLES = frozenset({"sensor_readings", "vision_detections", "hazard_events"})


class SyncQueue:
    """
    Persistent, SQLite-backed queue of telemetry records awaiting upload.

    This is a thin wrapper around the existing database persistence layer.
    It provides the queue-oriented vocabulary (enqueue / peek / ack / nack)
    that ``SyncService`` needs, without duplicating storage logic.
    """

    def __init__(self, database: SQLiteDatabase) -> None:
        self.database = database

    # ------------------------------------------------------------------
    # Public Queue Interface
    # ------------------------------------------------------------------

    def depth(self) -> int:
        """Return the number of records currently in the pending queue."""
        stats = self.database.get_sync_statistics()
        return stats.get("pending_count", 0)

    def peek_batch(self, batch_size: int = 50) -> List[Dict[str, Any]]:
        """
        Return up to *batch_size* pending records without removing them.

        Records are returned in insertion order (ASC id) so oldest data
        is uploaded first – important for correct chronological replay on
        the remote side.

        Returns an empty list when the queue is empty.
        """
        return self.database.get_pending_sync_records_detailed(limit=batch_size)

    def ack(self, records: List[Dict[str, Any]]) -> int:
        """
        Acknowledge successful upload of *records*.

        Marks every record ``sync_status='synced'`` in SQLite atomically.
        Returns the number of rows updated.
        """
        count = self.database.mark_records_synced_batch(records)
        logger.debug("SyncQueue: acked %d records", count)
        return count

    def nack(self, records: List[Dict[str, Any]]) -> None:
        """
        Negative-acknowledge *records* — leave them in the pending queue.

        Because pending is the default state and we never optimistically
        update to a transient "in-flight" status in the DB itself, a nack
        is a no-op at the database level.  The RetryManager in
        ``QueueManager`` tracks per-record backoff in memory.
        """
        logger.debug("SyncQueue: nack called for %d records (remain pending)", len(records))

    def reset_all_failed(self) -> int:
        """
        Re-queue any records stuck in an intermediate state.

        In practice, because we use only 'pending' / 'synced', this is a
        safety net for records that were accidentally left with a stale
        'syncing' value from a previous crash.

        Returns the number of rows reset.
        """
        conn = self.database.connect()
        try:
            cur = conn.execute(
                """
                UPDATE sensor_readings SET sync_status = 'pending'
                WHERE sync_status NOT IN ('pending', 'synced')
                """
            )
            count = cur.rowcount
            cur = conn.execute(
                """
                UPDATE vision_detections SET sync_status = 'pending'
                WHERE sync_status NOT IN ('pending', 'synced')
                """
            )
            count += cur.rowcount
            cur = conn.execute(
                """
                UPDATE hazard_events SET sync_status = 'pending'
                WHERE sync_status NOT IN ('pending', 'synced')
                """
            )
            count += cur.rowcount
            conn.commit()
            if count:
                logger.info("SyncQueue: reset %d stale in-flight records to 'pending'", count)
            return count
        finally:
            conn.close()

    def statistics(self) -> Dict[str, int]:
        """Delegate to database for queue-depth metrics."""
        return self.database.get_sync_statistics()


__all__ = ["SyncQueue"]
