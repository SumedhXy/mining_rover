from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional

logger = logging.getLogger("database.connection")


class DatabaseConnection:
    """Manages SQLite connections with WAL mode, busy timeout, and transaction safety."""

    def __init__(self, path: Optional[str] = None) -> None:
        if path:
            self.path = os.path.abspath(path)
        else:
            default_dir = Path(__file__).resolve().parent
            self.path = str(default_dir / "mining_rover.db")

        # Ensure database directory exists
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Create a new SQLite connection configured for reliability on Raspberry Pi."""
        try:
            conn = sqlite3.connect(self.path, timeout=30.0)
            conn.row_factory = sqlite3.Row

            # Configure PRAGMAs for concurrency and durability
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA busy_timeout = 5000;")
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            return conn
        except sqlite3.Error as exc:
            logger.error("Failed to connect to SQLite at %s: %s", self.path, exc)
            raise

    @contextmanager
    def transaction(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager providing an atomic transaction. Rollbacks automatically on error."""
        conn = self.connect()
        try:
            yield conn
            conn.commit()
        except Exception as exc:
            conn.rollback()
            logger.error("Transaction rolled back due to error: %s", exc)
            raise
        finally:
            conn.close()


__all__ = ["DatabaseConnection"]
