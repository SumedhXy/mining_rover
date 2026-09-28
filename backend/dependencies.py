from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from database.database import SQLiteDatabase
from database.repository import Repository
from sync.sync_service import SyncService

# Project root directory and default database path (Raspberry Pi & cross-platform safe)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "database" / "mining_rover.db"

_db_instance: Optional[SQLiteDatabase] = None
_sync_instance: Optional[SyncService] = None


def get_db_path() -> str:
    """Return database path honoring ROVER_DB_PATH environment variable."""
    return os.getenv("ROVER_DB_PATH", str(DEFAULT_DB_PATH))


def get_db() -> SQLiteDatabase:
    """Return or initialize the singleton SQLiteDatabase instance."""
    global _db_instance
    if _db_instance is None:
        db_path = get_db_path()
        _db_instance = SQLiteDatabase(path=db_path)
        _db_instance.initialize()
    return _db_instance


def set_db(db: SQLiteDatabase) -> None:
    """Override singleton database instance (useful for testing)."""
    global _db_instance
    _db_instance = db


def get_repository() -> Repository:
    """Dependency provider for database repository."""
    return get_db().repo


def get_sync_service() -> SyncService:
    """Return or initialize the singleton SyncService."""
    global _sync_instance
    if _sync_instance is None:
        database = get_db()
        server_url = os.getenv("ROVER_SYNC_URL", "http://127.0.0.1:8000/api/sync/receive")
        _sync_instance = SyncService(database=database, server_url=server_url)
    return _sync_instance


def set_sync_service(service: SyncService) -> None:
    """Override singleton sync service instance (useful for testing)."""
    global _sync_instance
    _sync_instance = service
