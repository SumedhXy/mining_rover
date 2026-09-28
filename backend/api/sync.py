from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Set
from fastapi import APIRouter, HTTPException

from backend.schemas.sync import (
    SyncBatchPayload,
    SyncStatusResponse,
    SyncTriggerResponse,
)
from sync.sync_service import SyncService

logger = logging.getLogger("backend.api.sync")

router = APIRouter(prefix="/api/sync", tags=["sync"])
service: SyncService | None = None

# In-memory deduplication set to emulate a remote central server's duplicate protection
_received_unique_ids: Set[str] = set()


@router.get("/status", response_model=SyncStatusResponse, summary="Get synchronization status")
def sync_status() -> Dict[str, Any]:
    """Provide synchronization state, pending records count, and network connectivity."""
    if service is None:
        return {
            "network_available": False,
            "sync_enabled": False,
            "pending_records": 0,
            "last_successful_sync": None,
            "last_sync_error": None,
            "network": "offline",
            "sync_status": "UNAVAILABLE",
            "local_database": "healthy",
            "pending_count": 0,
            "synced_count": 0,
            "in_flight_count": 0,
            "total_records": 0,
            "session_synced": 0,
            "last_sync_time": None,
            "last_error": None,
        }

    raw = service.get_status()
    is_online = raw.get("network") == "online"
    pending = raw.get("pending_count", 0)
    last_sync = raw.get("last_sync_time")
    last_err = raw.get("last_error")

    return {
        "network_available": is_online,
        "sync_enabled": raw.get("sync_enabled", True),
        "pending_records": pending,
        "last_successful_sync": last_sync,
        "last_sync_error": last_err,
        "network": raw.get("network", "offline"),
        "sync_status": raw.get("sync_status", "PAUSED"),
        "local_database": raw.get("local_database", "healthy"),
        "pending_count": pending,
        "synced_count": raw.get("synced_count", 0),
        "in_flight_count": raw.get("in_flight_count", 0),
        "total_records": raw.get("total_records", 0),
        "session_synced": raw.get("session_synced", 0),
        "last_sync_time": last_sync,
        "last_error": last_err,
    }


@router.post("/trigger", response_model=SyncTriggerResponse, summary="Trigger manual synchronization")
def trigger_sync() -> Dict[str, Any]:
    """Asynchronously initiate a synchronization cycle without blocking the HTTP request."""
    if service is None:
        raise HTTPException(status_code=503, detail="Sync service unavailable")

    # Launch non-blocking background thread to perform the cycle
    thread = threading.Thread(target=service.sync_cycle, daemon=True, name="ManualSyncWorker")
    thread.start()

    return {
        "status": "started",
        "message": "Synchronization task initiated",
    }


@router.post("/receive", summary="Central server ingest emulation")
def receive_sync(payload: SyncBatchPayload) -> Dict[str, Any]:
    """Emulates an authorized remote central server receiving synced records from the rover."""
    accepted: List[str] = []
    ignored: List[str] = []

    for r in payload.records:
        uid = r.get("unique_id") or f"{r.get('table_name')}_{r.get('id')}_{r.get('timestamp')}"
        if uid in _received_unique_ids:
            ignored.append(uid)
        else:
            _received_unique_ids.add(uid)
            accepted.append(uid)

    logger.info(
        f"Remote received {len(payload.records)} records from {payload.rover_id}: "
        f"{len(accepted)} accepted, {len(ignored)} duplicates ignored."
    )

    return {
        "status": "success",
        "rover_id": payload.rover_id,
        "accepted_count": len(accepted),
        "ignored_duplicate_count": len(ignored),
        "synced_ids": accepted + ignored,
    }
