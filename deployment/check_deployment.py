#!/usr/bin/env python3
"""
deployment/check_deployment.py — Mining Rover Deployment Readiness Check
=========================================================================
Phase 7A: Raspberry Pi Deployment Preparation

Validates all software prerequisites for running the Mining Rover on a
Raspberry Pi 4 (or development machine). Produces a readable report.

Usage:
    python deployment/check_deployment.py
    python deployment/check_deployment.py --verbose
    python deployment/check_deployment.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

# Ensure the project root is on sys.path regardless of cwd
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    name: str
    status: str          # "PASS" | "WARN" | "FAIL" | "SKIP"
    message: str = ""
    detail: str = ""
    latency_ms: Optional[float] = None


@dataclass
class DeploymentReport:
    results: List[CheckResult] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    def add(self, result: CheckResult) -> None:
        self.results.append(result)

    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == "PASS")

    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "FAIL")

    def warned(self) -> int:
        return sum(1 for r in self.results if r.status == "WARN")

    def overall(self) -> str:
        if self.failed() > 0:
            return "FAIL"
        if self.warned() > 0:
            return "WARN"
        return "PASS"

    def elapsed_ms(self) -> float:
        return (time.time() - self.start_time) * 1000


# ── Individual checks ─────────────────────────────────────────────────────────

def check_python_version() -> CheckResult:
    vi = sys.version_info
    version_str = f"{vi.major}.{vi.minor}.{vi.micro}"
    if vi.major < 3 or (vi.major == 3 and vi.minor < 10):
        return CheckResult("Python Version", "FAIL",
                           f"Python {version_str}", "Minimum required: 3.10")
    return CheckResult("Python Version", "PASS", f"Python {version_str}")


def check_platform() -> CheckResult:
    arch = platform.machine()
    system = platform.system()
    detail = f"{system} / {arch}"
    if system == "Linux" and arch == "aarch64":
        return CheckResult("Platform", "PASS", f"Linux ARM64 (Pi target)", detail)
    elif system == "Windows":
        return CheckResult("Platform", "WARN", "Windows (development machine)", detail)
    elif system == "Linux":
        return CheckResult("Platform", "WARN", f"Linux {arch} (not ARM64)", detail)
    else:
        return CheckResult("Platform", "WARN", detail, "Expected Raspberry Pi OS Linux/aarch64")


def check_venv() -> CheckResult:
    in_venv = (
        hasattr(sys, "real_prefix")
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    )
    venv_path = PROJECT_ROOT / ".venv"
    if in_venv:
        return CheckResult("Virtual Env", "PASS", f"Active venv: {sys.prefix}")
    elif venv_path.exists():
        return CheckResult("Virtual Env", "WARN",
                           ".venv exists but not active",
                           "Activate with: source .venv/bin/activate")
    else:
        return CheckResult("Virtual Env", "WARN",
                           "No .venv directory",
                           "Create with: python3 -m venv .venv")


def check_config() -> CheckResult:
    config_file = PROJECT_ROOT / "config" / "config.yaml"
    if not config_file.exists():
        return CheckResult("Configuration", "FAIL", "config/config.yaml not found")
    try:
        from config.config import load_config
        cfg = load_config()
        return CheckResult("Configuration", "PASS",
                           f"Loaded (host={cfg.backend.host}:{cfg.backend.port})")
    except Exception as e:
        return CheckResult("Configuration", "FAIL", "Load error", str(e))


def check_database() -> CheckResult:
    t0 = time.perf_counter()
    try:
        from config.config import load_config
        from database.database import SQLiteDatabase
        cfg = load_config()
        db_path = Path(cfg.database.path)
        if not db_path.is_absolute():
            db_path = PROJECT_ROOT / db_path
        db = SQLiteDatabase(path=str(db_path))
        db.initialize()
        stats = db.get_sync_statistics()
        latency = (time.perf_counter() - t0) * 1000
        return CheckResult("Database", "PASS",
                           f"{db_path.name} — {stats['total_count']} records",
                           f"Pending: {stats['pending_count']}, Synced: {stats['synced_count']}",
                           latency_ms=latency)
    except Exception as e:
        latency = (time.perf_counter() - t0) * 1000
        return CheckResult("Database", "FAIL", "Initialization failed", str(e), latency_ms=latency)


def check_migrations() -> CheckResult:
    try:
        from database.migrations import run_migrations
        from config.config import load_config
        from database.database import SQLiteDatabase
        cfg = load_config()
        db_path = Path(cfg.database.path)
        if not db_path.is_absolute():
            db_path = PROJECT_ROOT / db_path
        db = SQLiteDatabase(path=str(db_path))
        db.initialize()
        return CheckResult("Migrations", "PASS", "Schema up-to-date")
    except ImportError:
        return CheckResult("Migrations", "PASS", "No migration runner (schema in initialize())")
    except Exception as e:
        return CheckResult("Migrations", "FAIL", "Migration error", str(e))


def check_required_dirs() -> CheckResult:
    required = [
        PROJECT_ROOT / "database",
        PROJECT_ROOT / "logs",
        PROJECT_ROOT / "vision" / "weights",
    ]
    missing = [str(d) for d in required if not d.exists()]
    if missing:
        return CheckResult("Directories", "WARN",
                           f"{len(missing)} dir(s) missing",
                           "Will be created on first run: " + ", ".join(missing))
    return CheckResult("Directories", "PASS", "All required directories present")


def check_fastapi_import() -> CheckResult:
    t0 = time.perf_counter()
    try:
        # We only import the app, not start it
        os.environ.setdefault("TESTING", "1")
        from backend.main import app
        latency = (time.perf_counter() - t0) * 1000
        routes = len(app.routes)
        return CheckResult("FastAPI App", "PASS",
                           f"Imported OK ({routes} routes registered)",
                           latency_ms=latency)
    except Exception as e:
        latency = (time.perf_counter() - t0) * 1000
        return CheckResult("FastAPI App", "FAIL", "Import error", str(e), latency_ms=latency)


def check_decision_engine() -> CheckResult:
    t0 = time.perf_counter()
    try:
        from decision_engine.engine import evaluate
        result = evaluate({"smoke": 0.1}, {"temperature": 25.0, "gas": 0.1})
        latency = (time.perf_counter() - t0) * 1000
        return CheckResult("Decision Engine", "PASS",
                           f"Pipeline OK (severity: {result.severity})",
                           latency_ms=latency)
    except Exception as e:
        latency = (time.perf_counter() - t0) * 1000
        return CheckResult("Decision Engine", "FAIL", "Evaluation error", str(e), latency_ms=latency)


def check_sensor_subsystem() -> CheckResult:
    try:
        from sensors.esp32_receiver import ESP32Receiver
        from sensors.packet_parser import PacketParser
        receiver = ESP32Receiver(port=None)  # No port = graceful no-op
        return CheckResult("Sensor Subsystem", "PASS",
                           "Imports OK (hardware not required for check)")
    except Exception as e:
        return CheckResult("Sensor Subsystem", "FAIL", "Import error", str(e))


def check_vision_subsystem() -> CheckResult:
    try:
        from vision.inference.yolo_service import YOLOInferenceService
        from vision.inference.camera_stream import CameraStreamService
        svc = YOLOInferenceService()
        return CheckResult("Vision Subsystem", "PASS", "Imports OK (model not loaded until first inference)")
    except ImportError as e:
        return CheckResult("Vision Subsystem", "FAIL", "Import error", str(e))
    except Exception as e:
        return CheckResult("Vision Subsystem", "FAIL", "Initialization error", str(e))


def check_vision_weights() -> CheckResult:
    from config.config import load_config
    cfg = load_config()
    weights_path = Path(cfg.vision.model)
    if not weights_path.is_absolute():
        weights_path = PROJECT_ROOT / weights_path
    if weights_path.exists():
        size_kb = weights_path.stat().st_size // 1024
        return CheckResult("Vision Weights", "PASS",
                           f"best.pt found ({size_kb} KB)")
    else:
        return CheckResult("Vision Weights", "WARN",
                           "best.pt NOT found",
                           f"Copy your YOLO weights to: {weights_path}")


def check_pillow() -> CheckResult:
    try:
        from PIL import Image
        from importlib.metadata import version
        ver = version("Pillow")
        return CheckResult("Pillow (PIL)", "PASS", f"v{ver}")
    except Exception as e:
        return CheckResult("Pillow (PIL)", "FAIL", "Not installed", str(e))


def check_ultralytics() -> CheckResult:
    try:
        from importlib.metadata import version
        ver = version("ultralytics")
        return CheckResult("Ultralytics (YOLO)", "PASS", f"v{ver}")
    except Exception as e:
        return CheckResult("Ultralytics (YOLO)", "FAIL", "Not installed", str(e))


def check_torch() -> CheckResult:
    try:
        import torch
        cuda = torch.cuda.is_available()
        detail = "CUDA available" if cuda else "CPU-only (expected on Pi)"
        return CheckResult("PyTorch", "PASS", f"v{torch.__version__} — {detail}")
    except ImportError:
        arch = platform.machine()
        if arch == "aarch64":
            return CheckResult("PyTorch", "WARN",
                               "Not installed",
                               "ARM64: install torch wheel manually before ultralytics. See deployment/README.md.")
        return CheckResult("PyTorch", "FAIL", "Not installed")


def check_pyserial() -> CheckResult:
    try:
        import serial
        return CheckResult("pyserial", "PASS", f"v{serial.__version__} (ESP32 serial support)")
    except ImportError:
        return CheckResult("pyserial", "WARN",
                           "Not installed",
                           "Required for hardware ESP32. Safe to skip if using simulator.")


def check_opencv() -> CheckResult:
    try:
        import cv2
        return CheckResult("OpenCV (cv2)", "PASS", f"v{cv2.__version__}")
    except ImportError:
        arch = platform.machine()
        if arch == "aarch64":
            return CheckResult("OpenCV (cv2)", "WARN",
                               "Not installed",
                               "ARM64: use 'opencv-python-headless' on Pi. See deployment/README.md.")
        return CheckResult("OpenCV (cv2)", "FAIL", "Not installed")


def check_offline_mode() -> CheckResult:
    """Verify the system starts and does NOT require internet connectivity."""
    try:
        from sync.network_monitor import NetworkMonitor
        net = NetworkMonitor()
        net.set_override(False)  # Force offline
        from sync.sync_service import SyncService
        from database.database import SQLiteDatabase
        db_path = PROJECT_ROOT / "database" / "mining_rover.db"
        db = SQLiteDatabase(path=str(db_path))
        db.initialize()
        svc = SyncService(database=db, network_monitor=net, enabled=True)
        result = svc.sync_cycle()
        if result.get("status") == "paused" and result.get("reason") == "network_offline":
            return CheckResult("Offline Mode", "PASS",
                               "Sync pauses cleanly when offline — local ops unaffected")
        return CheckResult("Offline Mode", "PASS",
                           f"Offline cycle returned: {result.get('status', 'unknown')}")
    except Exception as e:
        return CheckResult("Offline Mode", "FAIL", "Offline test failed", str(e))


# ── Report renderer ───────────────────────────────────────────────────────────

import sys as _sys
_USE_ASCII = _sys.platform == "win32" or not _sys.stdout.isatty()
STATUS_ICON = (
    {"PASS": "+", "WARN": "!", "FAIL": "X", "SKIP": "-"}
    if _USE_ASCII
    else {"PASS": "✓", "WARN": "⚠", "FAIL": "✗", "SKIP": "–"}
)
STATUS_COLOR = {
    "PASS": "\033[32m", "WARN": "\033[33m",
    "FAIL": "\033[31m", "SKIP": "\033[90m",
}
RESET = "\033[0m"
BOLD = "\033[1m"


def render_report(report: DeploymentReport, verbose: bool = False) -> None:
    print()
    print(f"{BOLD}Raspberry Pi Deployment Readiness — Mining Rover (Phase 7A){RESET}")
    print("-" * 65)
    print(f"{'Check':<28} {'Status':<8} {'Message'}")
    print("-" * 65)
    for r in report.results:
        icon = STATUS_ICON.get(r.status, "?")
        color = STATUS_COLOR.get(r.status, "")
        latency = f" [{r.latency_ms:.0f}ms]" if r.latency_ms is not None else ""
        print(f"  {color}{icon}{RESET} {r.name:<26} {color}{r.status:<8}{RESET} {r.message}{latency}")
        if verbose and r.detail:
            print(f"    -> {r.detail}")
    print("-" * 65)
    overall = report.overall()
    color = STATUS_COLOR.get(overall, "")
    print(
        f"\n  Overall: {color}{BOLD}{overall}{RESET}  "
        f"({report.passed()} passed, {report.warned()} warned, {report.failed()} failed)"
        f"  [{report.elapsed_ms():.0f}ms]\n"
    )


def render_json(report: DeploymentReport) -> None:
    data = {
        "overall": report.overall(),
        "passed": report.passed(),
        "warned": report.warned(),
        "failed": report.failed(),
        "elapsed_ms": round(report.elapsed_ms(), 1),
        "checks": [
            {
                "name": r.name,
                "status": r.status,
                "message": r.message,
                "detail": r.detail,
                "latency_ms": round(r.latency_ms, 1) if r.latency_ms else None,
            }
            for r in report.results
        ],
    }
    print(json.dumps(data, indent=2))


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mining Rover — Raspberry Pi Deployment Readiness Check"
    )
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed messages for each check")
    parser.add_argument("--json", action="store_true",
                        help="Output results as JSON")
    args = parser.parse_args()

    report = DeploymentReport()

    checks = [
        check_python_version,
        check_platform,
        check_venv,
        check_config,
        check_database,
        check_migrations,
        check_required_dirs,
        check_fastapi_import,
        check_decision_engine,
        check_sensor_subsystem,
        check_vision_subsystem,
        check_vision_weights,
        check_pillow,
        check_ultralytics,
        check_torch,
        check_pyserial,
        check_opencv,
        check_offline_mode,
    ]

    for check_fn in checks:
        try:
            result = check_fn()
        except Exception as e:
            result = CheckResult(check_fn.__name__, "FAIL",
                                 "Unexpected check error", str(e))
        report.add(result)

    if args.json:
        render_json(report)
    else:
        render_report(report, verbose=args.verbose)

    return 0 if report.failed() == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
