from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


@dataclass
class DatabaseConfig:
    path: str = "./database/mining_rover.db"


@dataclass
class BackendConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass
class SyncConfig:
    enabled: bool = True
    server_url: str = "http://127.0.0.1:8000/api/sync/receive"
    health_check_url: str = "http://127.0.0.1:8000/api/system/status"
    check_interval: float = 5.0
    retry_interval: float = 10.0
    batch_size: int = 50
    max_retry_delay: float = 60.0
    timeout_seconds: float = 4.0


@dataclass
class VisionConfig:
    model: str = "./vision/weights/best.pt"
    camera_index: int = 0
    confidence_threshold: float = 0.50


@dataclass
class DecisionEngineConfig:
    min_confidence: float = 0.20
    sensor_weight: float = 0.50
    vision_weight: float = 0.50


@dataclass
class RoverConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    backend: BackendConfig = field(default_factory=BackendConfig)
    sync: SyncConfig = field(default_factory=SyncConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    decision_engine: DecisionEngineConfig = field(default_factory=DecisionEngineConfig)


def load_config(config_path: Optional[str] = None) -> RoverConfig:
    if config_path is None:
        project_root = Path(__file__).resolve().parents[1]
        default_yaml = project_root / "config" / "config.yaml"
        if default_yaml.exists():
            config_path = str(default_yaml)

    raw_data: Dict[str, Any] = {}
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    raw_data = loaded
        except Exception:
            raw_data = {}

    db_data = raw_data.get("database", {})
    backend_data = raw_data.get("backend", {})
    sync_data = raw_data.get("sync", {})
    vision_data = raw_data.get("vision", {})
    de_data = raw_data.get("decision_engine", {})

    db_cfg = DatabaseConfig(
        path=os.getenv("ROVER_DB_PATH", db_data.get("path", "./database/mining_rover.db"))
    )
    backend_cfg = BackendConfig(
        host=os.getenv("ROVER_BACKEND_HOST", backend_data.get("host", "0.0.0.0")),
        port=int(os.getenv("ROVER_BACKEND_PORT", backend_data.get("port", 8000))),
    )
    sync_cfg = SyncConfig(
        enabled=os.getenv("ROVER_SYNC_ENABLED", str(sync_data.get("enabled", True))).lower() in ("true", "1", "yes"),
        server_url=os.getenv("ROVER_SYNC_SERVER_URL", sync_data.get("server_url", "http://127.0.0.1:8000/api/sync/receive")),
        health_check_url=os.getenv("ROVER_SYNC_HEALTH_URL", sync_data.get("health_check_url", "http://127.0.0.1:8000/api/system/status")),
        check_interval=float(os.getenv("ROVER_SYNC_INTERVAL", sync_data.get("check_interval", 5.0))),
        retry_interval=float(sync_data.get("retry_interval", 10.0)),
        batch_size=int(sync_data.get("batch_size", 50)),
        max_retry_delay=float(sync_data.get("max_retry_delay", 60.0)),
        timeout_seconds=float(sync_data.get("timeout_seconds", 4.0)),
    )
    vision_cfg = VisionConfig(
        model=os.getenv("ROVER_VISION_MODEL", vision_data.get("model", "./vision/weights/best.pt")),
        camera_index=int(vision_data.get("camera_index", 0)),
        confidence_threshold=float(vision_data.get("confidence_threshold", 0.50)),
    )
    de_cfg = DecisionEngineConfig(
        min_confidence=float(de_data.get("min_confidence", 0.20)),
        sensor_weight=float(de_data.get("sensor_weight", 0.50)),
        vision_weight=float(de_data.get("vision_weight", 0.50)),
    )

    return RoverConfig(
        database=db_cfg,
        backend=backend_cfg,
        sync=sync_cfg,
        vision=vision_cfg,
        decision_engine=de_cfg,
    )
