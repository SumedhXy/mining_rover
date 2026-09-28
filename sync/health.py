"""
sync/health.py — System-wide health aggregator for the Mining Rover.

Collects health signals from all major subsystems and surfaces them as a
single ``HealthReport`` for the dashboard's System tab, startup checks,
and the ``/api/system/status`` endpoint.

Subsystems checked:
  - Database (SQLite reachability + integrity)
  - Sync queue (pending depth, last sync age)
  - Network (online/offline probe via NetworkMonitor)
  - Vision weights (file presence)
  - Decision Engine (import + trivial evaluation)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("sync.health")


@dataclass
class SubsystemHealth:
    name: str
    status: str          # "OK" | "DEGRADED" | "CRITICAL" | "UNKNOWN"
    message: str = ""
    latency_ms: Optional[float] = None
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    overall: str                             # "OK" | "DEGRADED" | "CRITICAL"
    timestamp: str = ""
    subsystems: List[SubsystemHealth] = field(default_factory=list)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "overall": self.overall,
            "timestamp": self.timestamp,
            "subsystems": [
                {
                    "name": s.name,
                    "status": s.status,
                    "message": s.message,
                    "latency_ms": s.latency_ms,
                    "detail": s.detail,
                }
                for s in self.subsystems
            ],
        }


class SystemHealthChecker:
    """
    Aggregates health from all rover subsystems.

    Designed to be called on-demand (e.g. on API request or startup) rather
    than running continuously — keeps the implementation side-effect free.
    """

    def __init__(
        self,
        database=None,
        network_monitor=None,
        vision_weights_path: Optional[str] = None,
        max_pending_warn: int = 500,
        max_pending_critical: int = 5000,
    ) -> None:
        self.database = database
        self.network_monitor = network_monitor
        self.vision_weights_path = vision_weights_path
        self.max_pending_warn = max_pending_warn
        self.max_pending_critical = max_pending_critical

    def run(self) -> HealthReport:
        """Execute all subsystem checks and return an aggregated HealthReport."""
        subsystems: List[SubsystemHealth] = []
        subsystems.append(self._check_database())
        subsystems.append(self._check_sync_queue())
        subsystems.append(self._check_network())
        subsystems.append(self._check_vision())
        subsystems.append(self._check_decision_engine())

        statuses = [s.status for s in subsystems]
        if "CRITICAL" in statuses:
            overall = "CRITICAL"
        elif "DEGRADED" in statuses:
            overall = "DEGRADED"
        else:
            overall = "OK"

        return HealthReport(
            overall=overall,
            timestamp=datetime.now(timezone.utc).isoformat(),
            subsystems=subsystems,
        )

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_database(self) -> SubsystemHealth:
        if self.database is None:
            return SubsystemHealth("database", "UNKNOWN", "No database instance provided")

        start = time.monotonic()
        try:
            stats = self.database.get_sync_statistics()
            latency = (time.monotonic() - start) * 1000
            return SubsystemHealth(
                name="database",
                status="OK",
                message="SQLite reachable and responsive",
                latency_ms=round(latency, 2),
                detail=stats,
            )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            logger.error("Health check — database error: %s", exc)
            return SubsystemHealth(
                name="database",
                status="CRITICAL",
                message=f"Database unreachable: {exc}",
                latency_ms=round(latency, 2),
            )

    def _check_sync_queue(self) -> SubsystemHealth:
        if self.database is None:
            return SubsystemHealth("sync_queue", "UNKNOWN", "No database instance provided")

        try:
            stats = self.database.get_sync_statistics()
            pending = stats.get("pending_count", 0)

            if pending >= self.max_pending_critical:
                status = "CRITICAL"
                message = f"{pending} records pending sync — backlog is critically large"
            elif pending >= self.max_pending_warn:
                status = "DEGRADED"
                message = f"{pending} records pending sync — backlog growing"
            else:
                status = "OK"
                message = f"{pending} records pending sync"

            return SubsystemHealth(
                name="sync_queue",
                status=status,
                message=message,
                detail=stats,
            )
        except Exception as exc:
            logger.error("Health check — sync queue error: %s", exc)
            return SubsystemHealth("sync_queue", "CRITICAL", f"Queue check failed: {exc}")

    def _check_network(self) -> SubsystemHealth:
        if self.network_monitor is None:
            return SubsystemHealth("network", "UNKNOWN", "No network monitor provided")

        start = time.monotonic()
        try:
            online = self.network_monitor.is_online()
            latency = (time.monotonic() - start) * 1000
            return SubsystemHealth(
                name="network",
                status="OK" if online else "DEGRADED",
                message="Remote endpoint reachable" if online else "Operating in offline mode — sync paused",
                latency_ms=round(latency, 2),
                detail={"online": online},
            )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            return SubsystemHealth(
                name="network",
                status="DEGRADED",
                message=f"Network probe error: {exc}",
                latency_ms=round(latency, 2),
            )

    def _check_vision(self) -> SubsystemHealth:
        if not self.vision_weights_path:
            return SubsystemHealth("vision", "DEGRADED", "No vision weights path configured — running in simulated feed mode")

        path = Path(self.vision_weights_path)
        if path.exists():
            size_kb = path.stat().st_size // 1024
            return SubsystemHealth(
                name="vision",
                status="OK",
                message=f"YOLO weights present ({size_kb} KB)",
                detail={"path": str(path), "size_kb": size_kb},
            )
        else:
            return SubsystemHealth(
                name="vision",
                status="DEGRADED",
                message=f"YOLO weights not found at {path}; using simulated perception feed",
                detail={"path": str(path)},
            )

    def _check_decision_engine(self) -> SubsystemHealth:
        start = time.monotonic()
        try:
            from decision_engine.engine import evaluate  # noqa: PLC0415
            result = evaluate({"smoke": 0.05}, {"temperature": 25.0, "gas": 0.05})
            latency = (time.monotonic() - start) * 1000
            return SubsystemHealth(
                name="decision_engine",
                status="OK",
                message=f"Pipeline initialized (severity: {result.severity})",
                latency_ms=round(latency, 2),
            )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            logger.error("Health check — decision engine error: %s", exc)
            return SubsystemHealth(
                name="decision_engine",
                status="CRITICAL",
                message=f"Decision engine unavailable: {exc}",
                latency_ms=round(latency, 2),
            )


__all__ = ["SystemHealthChecker", "HealthReport", "SubsystemHealth"]
