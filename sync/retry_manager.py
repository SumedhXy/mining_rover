from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass
from typing import Dict, Optional

logger = logging.getLogger("sync.retry_manager")


@dataclass
class RetryEntry:
    retry_count: int = 0
    last_attempt_time: float = 0.0
    next_allowed_time: float = 0.0
    last_error: Optional[str] = None


class RetryManager:
    """
    Handles failed synchronization attempts using an exponential backoff strategy
    with randomized jitter to prevent resource starvation or retry storms.
    """

    def __init__(
        self,
        base_delay: float = 2.0,
        max_delay: float = 60.0,
        backoff_multiplier: float = 2.0,
        jitter_factor: float = 0.1,
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_multiplier = backoff_multiplier
        self.jitter_factor = jitter_factor

        self._entries: Dict[str, RetryEntry] = {}

    def get_retry_count(self, key: str) -> int:
        entry = self._entries.get(key)
        return entry.retry_count if entry else 0

    def can_retry(self, key: str, now: Optional[float] = None) -> bool:
        if now is None:
            now = time.time()
        entry = self._entries.get(key)
        if entry is None:
            return True
        return now >= entry.next_allowed_time

    def record_failure(self, key: str, error: str, now: Optional[float] = None) -> float:
        """
        Record a sync failure and calculate the next delay using exponential backoff.
        Returns the delay in seconds until the next retry is allowed.
        """
        if now is None:
            now = time.time()

        entry = self._entries.get(key)
        if entry is None:
            entry = RetryEntry()
            self._entries[key] = entry

        entry.retry_count += 1
        entry.last_attempt_time = now
        entry.last_error = error

        # Exponential backoff formula
        calculated_delay = self.base_delay * (self.backoff_multiplier ** (entry.retry_count - 1))
        bounded_delay = min(self.max_delay, calculated_delay)

        # Apply jitter
        jitter = bounded_delay * self.jitter_factor * (random.uniform(-1.0, 1.0))
        final_delay = max(self.base_delay, bounded_delay + jitter)

        entry.next_allowed_time = now + final_delay

        logger.debug(
            f"Retry registered for '{key}'. Attempt {entry.retry_count}. "
            f"Backoff delay: {final_delay:.2f}s. Error: {error}"
        )
        return final_delay

    def record_success(self, key: str) -> None:
        """Reset retry tracking upon successful sync."""
        if key in self._entries:
            del self._entries[key]

    def reset(self) -> None:
        """Clear all retry entries."""
        self._entries.clear()


__all__ = ["RetryManager", "RetryEntry"]
