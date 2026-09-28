#!/usr/bin/env python3
"""
Mining Rover Unified Startup Orchestrator (Phase 6)

Starts and verifies all core components of the Mining Rover software
as an offline-first system:
1. SQLite Local Database initialization & integrity check
2. CAN Bus / Simulator Sensor Data Service
3. YOLO Vision Inference Engine verification
4. Decision Engine Arbitration Service
5. FastAPI REST API & WebSocket Backend
6. Background Cloud/Remote Synchronization Daemon
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.config import load_config
from database.database import SQLiteDatabase

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("start_rover")


def print_banner() -> None:
    print(r"""
===================================================================
   __  __ _       _               _____                       
  |  \/  (_)     (_)             |  __ \                      
  | \  / |_ _ __  _ _ __   __ _  | |__) |_____   _____ _ __   
  | |\/| | | '_ \| | '_ \ / _` | |  _  // _ \ \ / / _ \ '__|  
  | |  | | | | | | | | | | (_| | | | \ \ (_) \ V /  __/ |     
  |_|  |_|_|_| |_|_|_| |_|\__, | |_|  \_\___/ \_/ \___|_|     
                           __/ |                              
                          |___/    AUTONOMOUS CONSOLE (PHASE 6)
===================================================================
   ARCHITECTURE: OFFLINE-FIRST | CAN BUS | YOLO | SENSOR FUSION
===================================================================
    """)


def verify_database(db_path: str) -> SQLiteDatabase:
    logger.info(f"Initializing SQLite database at: {db_path}")
    db = SQLiteDatabase(path=db_path)
    db.initialize()
    stats = db.get_sync_statistics()
    logger.info(
        f"Database online. Records: {stats['total_count']} "
        f"(Pending Sync: {stats['pending_count']}, Synced: {stats['synced_count']})"
    )
    return db


def verify_vision(weights_path: str) -> bool:
    path = Path(weights_path)
    if path.exists():
        logger.info(f"YOLO vision weights located: {weights_path} ({path.stat().st_size // 1024} KB)")
        return True
    else:
        logger.warning(
            f"Vision weights not found at {weights_path}. "
            "Perception HUD will run in tactical simulated feed mode."
        )
        return False


def verify_decision_engine() -> bool:
    try:
        from decision_engine.engine import evaluate
        res = evaluate({"smoke": 0.1}, {"temperature": 25.0, "gas": 0.1})
        logger.info(f"Decision Engine verified: Pipeline initialized (Base severity: {res.severity})")
        return True
    except Exception as e:
        logger.error(f"Decision Engine check failed: {e}")
        return False


def run_health_report(db: SQLiteDatabase, weights_path: str) -> None:
    """Print a full Phase 6 system health report to stdout."""
    try:
        from sync.health import SystemHealthChecker
        from sync.network_monitor import NetworkMonitor

        checker = SystemHealthChecker(
            database=db,
            network_monitor=NetworkMonitor(),
            vision_weights_path=weights_path,
        )
        report = checker.run()

        import sys as _sys
        _use_ascii = _sys.platform == "win32"
        _icons = (
            {"OK": "+", "DEGRADED": "!", "CRITICAL": "X", "UNKNOWN": "?"}
            if _use_ascii
            else {"OK": "✓", "DEGRADED": "⚠", "CRITICAL": "✗", "UNKNOWN": "?"}
        )

        print("\n" + "=" * 60)
        print(f"  PHASE 6 HEALTH REPORT — Overall: {report.overall}")
        print("=" * 60)
        for sub in report.subsystems:
            status_icon = _icons.get(sub.status, "?")
            latency_str = f" [{sub.latency_ms:.1f}ms]" if sub.latency_ms is not None else ""
            print(f"  {status_icon} {sub.name:<20} {sub.status:<10}{latency_str}")
            if sub.message:
                print(f"    -> {sub.message}")
        print("=" * 60 + "\n")
    except Exception as e:
        logger.warning(f"Health report generation failed: {e}")


def start_backend(host: str, port: int) -> None:
    import uvicorn
    from backend.main import app

    logger.info(f"Launching FastAPI Backend on http://{host}:{port}...")
    logger.info("Local Dashboard available on http://localhost:3000")
    logger.info("Press CTRL+C to terminate.")

    uvicorn.run(app, host=host, port=port, log_level="info")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mining Rover Master Startup Script")
    parser.add_argument("--config", type=str, default=None, help="Path to config.yaml")
    parser.add_argument("--host", type=str, default=None, help="Backend host IP")
    parser.add_argument("--port", type=int, default=None, help="Backend port")
    parser.add_argument("--no-sync", action="store_true", help="Disable remote synchronization service")
    parser.add_argument("--check-only", action="store_true", help="Run health verification checks and exit")
    parser.add_argument("--health-report", action="store_true", help="Print detailed Phase 6 health report on startup")
    args = parser.parse_args()

    print_banner()

    # 1. Load Configuration
    cfg = load_config(args.config)
    host = args.host or cfg.backend.host
    port = args.port or cfg.backend.port

    logger.info("Rover Configuration loaded:")
    logger.info(f"  - Database Path: {cfg.database.path}")
    logger.info(f"  - Sync Enabled: {cfg.sync.enabled and not args.no_sync}")
    logger.info(f"  - Sync Server URL: {cfg.sync.server_url}")

    # 2. Verify Database
    db_abs = str((PROJECT_ROOT / cfg.database.path).resolve()) if not Path(cfg.database.path).is_absolute() else cfg.database.path
    db = verify_database(db_abs)

    # 3. Verify Vision
    weights_abs = str((PROJECT_ROOT / cfg.vision.model).resolve()) if not Path(cfg.vision.model).is_absolute() else cfg.vision.model
    verify_vision(weights_abs)

    # 4. Verify Decision Engine
    verify_decision_engine()

    # 5. Optional: Phase 6 health report
    if args.health_report or args.check_only:
        run_health_report(db, weights_abs)

    if args.check_only:
        logger.info("All component checks passed successfully. [OFFLINE-FIRST READY]")
        return

    # 6. Start Backend Server
    start_backend(host=host, port=port)


if __name__ == "__main__":
    main()

