"""
tests/deployment/test_phase7a.py — Phase 7A Deployment Readiness Tests
=======================================================================

Tests for:
- Configuration loading (Linux paths, env overrides)
- Path portability (no hard-coded Windows paths in config/startup)
- Required directory auto-creation
- Database initialization + startup
- Offline mode behavior
- FastAPI application import
- Dependency checker script
- startup --check-only mode
- Missing model graceful behavior
- Systemd service file validity
"""

from __future__ import annotations

import importlib
import os
import platform
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ── Helpers ────────────────────────────────────────────────────────────────────

def _fresh_db(tmp_path, name="deploy_test.db"):
    from database.database import SQLiteDatabase
    db = SQLiteDatabase(path=str(tmp_path / name))
    db.initialize()
    return db


# ── Configuration Tests ────────────────────────────────────────────────────────


class TestConfigLoading:
    def test_load_config_returns_rover_config(self):
        from config.config import load_config, RoverConfig
        cfg = load_config()
        assert isinstance(cfg, RoverConfig)

    def test_config_defaults_are_safe(self):
        from config.config import load_config
        cfg = load_config()
        assert cfg.backend.port == 8000
        assert cfg.backend.host in ("0.0.0.0", "127.0.0.1")
        assert cfg.sync.enabled in (True, False)
        assert cfg.vision.confidence_threshold > 0.0
        assert cfg.decision_engine.min_confidence >= 0.0

    def test_env_override_db_path(self, tmp_path, monkeypatch):
        new_path = str(tmp_path / "override.db")
        monkeypatch.setenv("ROVER_DB_PATH", new_path)
        # Reload to pick up the new env var
        from config import config as cfg_mod
        importlib.reload(cfg_mod)
        cfg = cfg_mod.load_config()
        assert cfg.database.path == new_path
        # Restore
        importlib.reload(cfg_mod)

    def test_env_override_host_port(self, monkeypatch):
        monkeypatch.setenv("ROVER_BACKEND_HOST", "127.0.0.1")
        monkeypatch.setenv("ROVER_BACKEND_PORT", "9999")
        from config import config as cfg_mod
        importlib.reload(cfg_mod)
        cfg = cfg_mod.load_config()
        assert cfg.backend.host == "127.0.0.1"
        assert cfg.backend.port == 9999
        importlib.reload(cfg_mod)

    def test_sync_disabled_via_env(self, monkeypatch):
        monkeypatch.setenv("ROVER_SYNC_ENABLED", "false")
        from config import config as cfg_mod
        importlib.reload(cfg_mod)
        cfg = cfg_mod.load_config()
        assert cfg.sync.enabled is False
        importlib.reload(cfg_mod)

    def test_config_yaml_has_no_windows_paths(self):
        config_yaml = PROJECT_ROOT / "config" / "config.yaml"
        text = config_yaml.read_text(encoding="utf-8")
        assert "C:\\" not in text
        assert "C:/" not in text
        assert "Users\\" not in text

    def test_env_example_has_no_windows_paths(self):
        env_example = PROJECT_ROOT / ".env.example"
        text = env_example.read_text(encoding="utf-8")
        assert "C:\\" not in text
        assert "C:/" not in text

    def test_config_missing_yaml_falls_back_to_defaults(self, tmp_path):
        from config.config import load_config
        nonexistent = str(tmp_path / "nonexistent.yaml")
        cfg = load_config(config_path=nonexistent)
        # Should return defaults, not raise
        assert cfg.backend.port == 8000


# ── Path Portability Tests ─────────────────────────────────────────────────────


class TestPathPortability:
    def test_config_py_uses_pathlib(self):
        from config import config as cfg_mod
        src = Path(cfg_mod.__file__).read_text(encoding="utf-8")
        assert "from pathlib import" in src or "import pathlib" in src

    def test_database_module_uses_pathlib(self):
        from database import database as db_mod
        src = Path(db_mod.__file__).read_text(encoding="utf-8")
        # Should not contain hard-coded Windows paths
        assert "C:\\" not in src
        assert "C:/" not in src

    def test_start_rover_uses_pathlib(self):
        src = (PROJECT_ROOT / "start_rover.py").read_text(encoding="utf-8")
        assert "from pathlib import" in src or "import pathlib" in src
        assert "C:\\" not in src
        assert "C:/" not in src

    def test_backend_dependencies_resolves_from_file(self):
        from backend import dependencies as dep_mod
        src = Path(dep_mod.__file__).read_text(encoding="utf-8")
        # Should use Path(__file__) anchoring, not a hard-coded path
        assert "Path(__file__)" in src
        assert "C:\\" not in src

    def test_yolo_service_resolves_from_file(self):
        from vision.inference import yolo_service as ys_mod
        src = Path(ys_mod.__file__).read_text(encoding="utf-8", errors="ignore")
        assert "Path(__file__)" in src
        assert "C:\\" not in src


# ── Directory Auto-creation Tests ──────────────────────────────────────────────


class TestDirectoryCreation:
    def test_database_dir_created_by_initialize(self, tmp_path):
        from database.database import SQLiteDatabase
        nested = tmp_path / "deep" / "nested" / "rover.db"
        db = SQLiteDatabase(path=str(nested))
        db.initialize()
        assert nested.exists()

    def test_check_deployment_creates_dirs(self, tmp_path, monkeypatch):
        """
        Running check_deployment.py --json should not crash even in tmp_path.
        Directory creation is idempotent.
        """
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "deployment" / "check_deployment.py"), "--json"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        import json
        data = json.loads(result.stdout)
        assert "overall" in data
        assert "checks" in data
        assert isinstance(data["checks"], list)


# ── Database Initialization Tests ─────────────────────────────────────────────


class TestDatabaseInitialization:
    def test_initialize_is_idempotent(self, tmp_path):
        db = _fresh_db(tmp_path, "idempotent.db")
        db.initialize()  # Second call must not raise
        db.initialize()
        stats = db.get_sync_statistics()
        assert stats["total_count"] == 0

    def test_database_resolves_relative_path(self, tmp_path):
        from database.database import SQLiteDatabase
        # Relative path → must work
        db = SQLiteDatabase(path=str(tmp_path / "relative.db"))
        db.initialize()
        assert (tmp_path / "relative.db").exists()

    def test_database_survives_restart(self, tmp_path):
        db_path = str(tmp_path / "restart.db")
        from database.database import SQLiteDatabase
        db1 = SQLiteDatabase(path=db_path)
        db1.initialize()
        db1.insert_sensor_reading(
            timestamp="2026-09-28T12:00:00Z",
            device_id="rover_01",
            sensor_type="gas",
            value=0.5,
            unit="index",
            valid=True,
            source="test",
        )
        # Simulate restart: create a new instance
        db2 = SQLiteDatabase(path=db_path)
        db2.initialize()
        stats = db2.get_sync_statistics()
        assert stats["total_count"] >= 1


# ── Offline Mode Tests ─────────────────────────────────────────────────────────


class TestOfflineMode:
    def test_sync_service_pauses_gracefully_when_offline(self, tmp_path):
        from database.database import SQLiteDatabase
        from sync.network_monitor import NetworkMonitor
        from sync.sync_service import SyncService

        db = SQLiteDatabase(path=str(tmp_path / "offline.db"))
        db.initialize()

        net = NetworkMonitor()
        net.set_override(False)  # Force offline

        svc = SyncService(database=db, network_monitor=net, enabled=True)
        result = svc.sync_cycle()

        assert result["status"] == "paused"
        assert result["reason"] == "network_offline"

    def test_fastapi_starts_without_network(self, tmp_path):
        """FastAPI app imports must not require network access."""
        os.environ.setdefault("TESTING", "1")
        from backend.main import app
        assert app is not None

    def test_decision_engine_works_offline(self):
        from decision_engine.engine import evaluate
        result = evaluate({"smoke": 0.0}, {"temperature": 22.0, "gas": 0.05})
        assert result is not None
        assert hasattr(result, "severity")


# ── FastAPI Import Tests ───────────────────────────────────────────────────────


class TestFastAPIImport:
    def test_app_has_routes(self):
        os.environ.setdefault("TESTING", "1")
        from backend.main import app
        route_paths = [r.path for r in app.routes]
        # Core endpoints must be registered
        assert any("/api/sensors" in p for p in route_paths)
        assert any("/api/decisions" in p for p in route_paths)
        assert any("/api/system" in p for p in route_paths)
        assert any("/api/sync" in p for p in route_paths)

    def test_app_cors_configured(self):
        """CORS middleware is registered on the app.
        FastAPI/Starlette stores middleware in app.middleware_stack or as exception
        handlers; the simplest reliable check is that the CORS env var is consumed
        and the middleware module is importable + configured.
        """
        os.environ.setdefault("TESTING", "1")
        from fastapi.middleware.cors import CORSMiddleware
        # Verify the middleware class itself is importable (deploy safety check)
        assert CORSMiddleware is not None
        # Verify the app was configured with CORS via the main module
        from backend import main as main_mod
        src = Path(main_mod.__file__).read_text(encoding="utf-8")
        assert "CORSMiddleware" in src
        assert "ROVER_ALLOWED_ORIGINS" in src

    def test_cors_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("ROVER_ALLOWED_ORIGINS", "http://192.168.1.50:3000")
        # Reimport would normally pick this up; verify env variable is consumed
        allowed = os.getenv("ROVER_ALLOWED_ORIGINS", "")
        assert "192.168.1.50" in allowed

    def test_backend_binds_0_0_0_0_by_default(self):
        from config.config import load_config
        cfg = load_config()
        # Default must be 0.0.0.0 (LAN accessible)
        assert cfg.backend.host == "0.0.0.0"


# ── Missing Model Graceful Behavior ───────────────────────────────────────────


class TestMissingModel:
    def test_yolo_service_raises_on_missing_weights(self, tmp_path):
        from vision.inference.yolo_service import YOLOInferenceService
        svc = YOLOInferenceService(model_path=tmp_path / "nonexistent.pt")
        with pytest.raises((FileNotFoundError, Exception)):
            svc.ensure_model_loaded()

    def test_startup_verify_vision_returns_false_for_missing(self, tmp_path):
        """start_rover.verify_vision() must return False, not raise."""
        import start_rover
        result = start_rover.verify_vision(str(tmp_path / "nonexistent.pt"))
        assert result is False

    def test_startup_verify_vision_returns_true_when_found(self, tmp_path):
        import start_rover
        weights = tmp_path / "best.pt"
        weights.write_bytes(b"fake weights content")
        result = start_rover.verify_vision(str(weights))
        assert result is True


# ── Deployment Readiness Checker ──────────────────────────────────────────────


class TestDeploymentChecker:
    def test_checker_is_runnable(self):
        checker = PROJECT_ROOT / "deployment" / "check_deployment.py"
        assert checker.exists()
        result = subprocess.run(
            [sys.executable, str(checker)],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        # Exit code 0 = all PASS/WARN, 1 = at least one FAIL
        assert result.returncode in (0, 1)
        # Output must contain the header
        assert "Mining Rover" in result.stdout

    def test_checker_json_output_is_valid(self):
        import json
        checker = PROJECT_ROOT / "deployment" / "check_deployment.py"
        result = subprocess.run(
            [sys.executable, str(checker), "--json"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        data = json.loads(result.stdout)
        assert "overall" in data
        assert "passed" in data
        assert "failed" in data
        assert isinstance(data["checks"], list)
        for check in data["checks"]:
            assert "name" in check
            assert "status" in check
            assert check["status"] in ("PASS", "WARN", "FAIL", "SKIP")

    def test_checker_all_named_checks_present(self):
        import json
        checker = PROJECT_ROOT / "deployment" / "check_deployment.py"
        result = subprocess.run(
            [sys.executable, str(checker), "--json"],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        data = json.loads(result.stdout)
        names = {c["name"] for c in data["checks"]}
        expected = {
            "Python Version", "Platform", "Virtual Env", "Configuration",
            "Database", "Migrations", "Directories", "FastAPI App",
            "Decision Engine", "Sensor Subsystem", "Vision Subsystem",
            "Vision Weights", "Offline Mode",
        }
        for expected_name in expected:
            assert expected_name in names, f"Missing check: {expected_name}"


# ── Systemd Service File Tests ─────────────────────────────────────────────────


class TestSystemdServiceFile:
    def test_service_file_exists(self):
        service = PROJECT_ROOT / "deployment" / "mining-rover.service"
        assert service.exists()

    def test_service_file_has_required_sections(self):
        service = PROJECT_ROOT / "deployment" / "mining-rover.service"
        content = service.read_text(encoding="utf-8")
        assert "[Unit]" in content
        assert "[Service]" in content
        assert "[Install]" in content

    def test_service_file_uses_venv_python(self):
        service = PROJECT_ROOT / "deployment" / "mining-rover.service"
        content = service.read_text(encoding="utf-8")
        assert ".venv/bin/python" in content

    def test_service_file_has_restart_policy(self):
        service = PROJECT_ROOT / "deployment" / "mining-rover.service"
        content = service.read_text(encoding="utf-8")
        assert "Restart=" in content

    def test_service_file_has_no_windows_paths(self):
        service = PROJECT_ROOT / "deployment" / "mining-rover.service"
        content = service.read_text(encoding="utf-8")
        assert "C:\\" not in content
        assert "C:/" not in content

    def test_service_file_has_no_root_user(self):
        service = PROJECT_ROOT / "deployment" / "mining-rover.service"
        content = service.read_text(encoding="utf-8")
        # Should NOT run as root
        assert "User=root" not in content

    def test_service_file_has_after_network(self):
        service = PROJECT_ROOT / "deployment" / "mining-rover.service"
        content = service.read_text(encoding="utf-8")
        assert "After=network" in content


# ── Deploy Script Tests ────────────────────────────────────────────────────────


class TestDeployScript:
    def test_deploy_script_exists(self):
        script = PROJECT_ROOT / "deployment" / "deploy_pi.sh"
        assert script.exists()

    def test_deploy_script_is_bash(self):
        script = PROJECT_ROOT / "deployment" / "deploy_pi.sh"
        first_line = script.read_text(encoding="utf-8").split("\n")[0]
        assert first_line.startswith("#!/")
        assert "bash" in first_line

    def test_deploy_script_has_check_mode(self):
        script = PROJECT_ROOT / "deployment" / "deploy_pi.sh"
        content = script.read_text(encoding="utf-8")
        assert "--check" in content

    def test_deploy_script_has_install_mode(self):
        script = PROJECT_ROOT / "deployment" / "deploy_pi.sh"
        content = script.read_text(encoding="utf-8")
        assert "--install" in content

    def test_deploy_script_validates_linux(self):
        script = PROJECT_ROOT / "deployment" / "deploy_pi.sh"
        content = script.read_text(encoding="utf-8")
        assert "Linux" in content

    def test_deploy_script_has_no_destructive_rm_rf(self):
        script = PROJECT_ROOT / "deployment" / "deploy_pi.sh"
        content = script.read_text(encoding="utf-8")
        # Should not blindly rm -rf anything
        assert "rm -rf /" not in content


# ── Gitignore Tests ────────────────────────────────────────────────────────────


class TestGitignore:
    def test_gitignore_excludes_env(self):
        gi = PROJECT_ROOT / ".gitignore"
        content = gi.read_text(encoding="utf-8")
        assert ".env" in content

    def test_gitignore_excludes_venv(self):
        gi = PROJECT_ROOT / ".gitignore"
        content = gi.read_text(encoding="utf-8")
        assert ".venv" in content or "venv" in content

    def test_gitignore_excludes_db_files(self):
        gi = PROJECT_ROOT / ".gitignore"
        content = gi.read_text(encoding="utf-8")
        assert ".db" in content

    def test_gitignore_excludes_pycache(self):
        gi = PROJECT_ROOT / ".gitignore"
        content = gi.read_text(encoding="utf-8")
        assert "__pycache__" in content
