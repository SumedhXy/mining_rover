from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SyncStatusResponse(BaseModel):
    network_available: bool = False
    sync_enabled: bool = True
    pending_records: int = 0
    last_successful_sync: Optional[str] = None
    last_sync_error: Optional[str] = None
    # Compatibility with frontend dashboard
    network: str = "offline"
    sync_status: str = "PAUSED"
    local_database: str = "healthy"
    pending_count: int = 0
    synced_count: int = 0
    in_flight_count: int = 0
    total_records: int = 0
    session_synced: int = 0
    last_sync_time: Optional[str] = None
    last_error: Optional[str] = None


class SyncTriggerResponse(BaseModel):
    status: str = "started"
    message: Optional[str] = "Synchronization cycle triggered"


class SyncBatchPayload(BaseModel):
    rover_id: str = "mining_rover_01"
    timestamp: str
    batch_size: int = 0
    records: List[Dict[str, Any]] = Field(default_factory=list)
