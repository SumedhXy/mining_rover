from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from database.database import SQLiteDatabase
from sync.retry_manager import RetryManager

logger = logging.getLogger("sync.queue_manager")


class QueueManager:
    """
    Manages the queue of records awaiting synchronization to the remote server.
    Ensures unique record identifiers, tracks retry states via RetryManager,
    and coordinates batch retrieval from the SQLite database.
    """

    def __init__(self, database: SQLiteDatabase, retry_manager: Optional[RetryManager] = None):
        self.database = database
        self.retry_manager = retry_manager or RetryManager()
        self._in_flight: Dict[str, Dict[str, Any]] = {}

    def get_pending_batch(self, batch_size: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves a batch of pending records from SQLite.
        Filters out any record currently constrained by the retry backoff delay.
        """
        all_pending = self.database.get_pending_sync_records_detailed(limit=batch_size * 2)
        eligible_batch: List[Dict[str, Any]] = []
        now = time.time()

        for record in all_pending:
            key = record.get("unique_id") or f"{record.get('table_name')}_{record.get('id')}"
            
            # Check if retry backoff allows another attempt
            if self.retry_manager.can_retry(key, now=now):
                record["sync_status"] = "SYNCING"
                record["retry_count"] = self.retry_manager.get_retry_count(key)
                eligible_batch.append(record)
                self._in_flight[key] = record

                if len(eligible_batch) >= batch_size:
                    break

        return eligible_batch

    def mark_batch_synced(self, records: List[Dict[str, Any]]) -> int:
        """
        Marks successfully synchronized records as SYNCED in the SQLite database
        and clears retry tracking.
        """
        count = self.database.mark_records_synced_batch(records)
        for r in records:
            key = r.get("unique_id") or f"{r.get('table_name')}_{r.get('id')}"
            self.retry_manager.record_success(key)
            self._in_flight.pop(key, None)

        logger.info(f"Marked {count} records as SYNCED in local database")
        return count

    def mark_batch_failed(self, records: List[Dict[str, Any]], error: str) -> None:
        """
        Records failure and calculates backoff for each failed record.
        """
        for r in records:
            key = r.get("unique_id") or f"{r.get('table_name')}_{r.get('id')}"
            self.retry_manager.record_failure(key, error=error)
            self._in_flight.pop(key, None)

        logger.warning(f"Batch of {len(records)} records marked as FAILED with error: {error}")

    def get_status(self) -> Dict[str, Any]:
        """Returns statistics on the local sync queue."""
        stats = self.database.get_sync_statistics()
        return {
            "pending_count": stats.get("pending_count", 0),
            "synced_count": stats.get("synced_count", 0),
            "total_count": stats.get("total_count", 0),
            "in_flight_count": len(self._in_flight),
        }


__all__ = ["QueueManager"]
