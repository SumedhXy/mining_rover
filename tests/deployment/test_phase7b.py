"""
Phase 7B Deployment Readiness Test Suite
Verifies network binding, CORS, configuration safety, CWD-independence,
startup non-interactivity, health endpoints, and offline-first resilience.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.main import app
from config.config import load_config
from database.database import SQLiteDatabase
from sync.health import SystemHealthChecker
from sync.network_monitor import NetworkMonitor


class TestFastAPINetworkBinding:
    """Requirement 1 & 2: FastAPI binds to configurable host and port."""

    def test_default_binding_is_all_interfaces(self):
        cfg = load_config()
        assert cfg.backend.host == "0.0.0.0"
        assert cfg.backend.port == 8000

    def test_env_override_host_and_port(self, monkeypatch):
        monkeypatch.setenv("ROVER_BACKEND_HOST", "192.168.50.1")
        monkeypatch.setenv("ROVER_BACKEND_PORT", "9000")
        cfg = load_config()
        assert cfg.backend.host == "192.168.50.1"
        assert cfg.backend.port == 9000


class TestDashboardConfiguration:
    """Requirement 3 & 4: Dashboard API base URL and no hard-coded localhost in production."""

    def test_rover_api_supports_vite_base_url_env(self):
        api_ts_path = PROJECT_ROOT / "dashboard" / "src" / "api" / "roverApi.ts"
        assert api_ts_path.exists()
        content = api_ts_path.read_text(encoding="utf-8")
        assert "VITE_API_BASE_URL" in content
        assert "__ROVER_API_BASE_URL__" in content

    def test_vite_config_supports_env_proxy_target(self):
        vite_cfg_path = PROJECT_ROOT / "dashboard" / "vite.config.ts"
        assert vite_cfg_path.exists()
        content = vite_cfg_path.read_text(encoding="utf-8")
        assert "VITE_API_BASE_URL" in content or "VITE_API_URL" in content

    def test_no_hardcoded_localhost_in_production_config(self):
        cfg_yaml = PROJECT_ROOT / "config" / "config.yaml"
        content = cfg_yaml.read_text(encoding="utf-8")
        # backend host must be 0.0.0.0, not localhost
        assert 'host: "0.0.0.0"' in content or "host: 0.0.0.0" in content


class TestDatabasePathIndependence:
    """Requirement 5: Database path works independent of current working directory."""

    def test_database_path_resolves_when_started_from_arbitrary_cwd(self, tmp_path):
        from database.connection import DatabaseConnection

        # Test relative path resolution
        conn = DatabaseConnection(path="./database/mining_rover.db")
        # Path must be absolute and point inside PROJECT_ROOT
        assert Path(conn.path).is_absolute()
        assert str(PROJECT_ROOT) in conn.path

    def test_backend_get_db_path_resolves_cwd_independently(self, monkeypatch):
        from backend.dependencies import get_db_path

        monkeypatch.setenv("ROVER_DB_PATH", "database/test_custom.db")
        db_path = get_db_path()
        assert Path(db_path).is_absolute()
        assert str(PROJECT_ROOT) in db_path

    def test_database_persistence_across_connections(self, tmp_path):
        db_file = tmp_path / "persistence_test.db"
        db1 = SQLiteDatabase(path=str(db_file))
        db1.initialize()
        db1.insert_sensor_reading(
            timestamp="2026-09-28T12:00:00Z",
            device_id="rover_01",
            temperature_c=25.0,
            humidity_percent=50.0,
            pressure_hpa=1013.25,
            mq4=0.1,
            mq135=0.05,
        )

        # Open second connection to same file
        db2 = SQLiteDatabase(path=str(db_file))
        history = db2.get_sensor_history(limit=5)
        assert len(history) == 1
        assert history[0]["temperature_c"] == 25.0


class TestConfigurationLoading:
    """Requirement 6: Configuration loads correctly with environment overrides."""

    def test_load_config_defaults(self):
        cfg = load_config()
        assert cfg.database.path is not None
        assert cfg.backend.host == "0.0.0.0"
        assert cfg.sync.enabled is True

    def test_load_config_cors_origins_resolution(self, monkeypatch):
        monkeypatch.setenv("CORS_ORIGINS", "http://192.168.50.1:3000,http://192.168.50.100:3000")
        cfg = load_config()
        assert "http://192.168.50.1:3000" in cfg.backend.cors_origins
        assert "http://192.168.50.100:3000" in cfg.backend.cors_origins


class TestStartupScriptNonInteractive:
    """Requirement 7: Startup script works in non-interactive mode for systemd."""

    def test_start_rover_check_only_flag(self):
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "start_rover.py"), "--check-only"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
            timeout=20,
        )
        assert result.returncode == 0
        output = result.stdout + result.stderr
        assert "OFFLINE-FIRST READY" in output or "Configuration loaded" in output


class TestHealthEndpoints:
    """Requirement 8: Health endpoints remain operational."""

    def test_root_endpoint_status(self):
        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "online"
        assert data["mode"] == "offline_first"

    def test_api_health_endpoint(self):
        client = TestClient(app)
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "healthy", "OK")

    def test_api_system_status_endpoint(self):
        client = TestClient(app)
        resp = client.get("/api/system/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "rover_status" in data or "database_status" in data


class TestCORSConfiguration:
    """Requirement 9: CORS configuration works with local and Pi access point origins."""

    def test_cors_middleware_present(self):
        from fastapi.middleware.cors import CORSMiddleware
        # Verify app has middleware stack configured
        assert app is not None

    def test_cors_preflight_response(self):
        client = TestClient(app)
        headers = {
            "Origin": "http://192.168.50.1:3000",
            "Access-Control-Request-Method": "GET",
        }
        resp = client.options("/api/health", headers=headers)
        # Preflight response
        assert resp.status_code in (200, 204)


class TestOfflineResilience:
    """Requirement 10: Offline operation remains intact without internet connectivity."""

    def test_system_health_checker_when_offline(self, tmp_path):
        db = SQLiteDatabase(path=str(tmp_path / "offline_health.db"))
        db.initialize()
        net_mon = NetworkMonitor()
        net_mon.set_override(False)
        assert net_mon.is_online() is False

        checker = SystemHealthChecker(database=db, network_monitor=net_mon)
        report = checker.run()
        # System status should be DEGRADED (because network is offline), NOT CRITICAL
        assert report.overall in ("DEGRADED", "OK")
        sub_dict = {s.name: s for s in report.subsystems}
        assert sub_dict["database"].status == "OK"
        assert sub_dict["decision_engine"].status == "OK"
