from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict

logger = logging.getLogger("decision_thresholds")

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    yaml = None  # type: ignore
    YAML_AVAILABLE = False


DEFAULT_THRESHOLDS: Dict[str, Any] = {
    "temperature": {
        "warning_c": 45.0,
        "high_c": 55.0,
        "critical_c": 65.0,
    },
    "mq4": {
        "warning": 0.40,
        "high": 0.60,
        "critical": 0.80,
    },
    "mq135": {
        "warning": 0.40,
        "high": 0.60,
        "critical": 0.80,
    },
    "pressure": {
        "minimum_hpa": 850.0,
        "maximum_hpa": 1100.0,
    },
    "vision": {
        "minimum_confidence": 0.50,
    },
    "persistence": {
        "required_readings": 3,
    },
    "data_freshness": {
        "sensor_max_age_seconds": 5.0,
        "vision_max_age_seconds": 2.0,
    },
}


@dataclass
class DecisionThresholds:
    temperature: Dict[str, float] = field(default_factory=lambda: DEFAULT_THRESHOLDS["temperature"].copy())
    mq4: Dict[str, float] = field(default_factory=lambda: DEFAULT_THRESHOLDS["mq4"].copy())
    mq135: Dict[str, float] = field(default_factory=lambda: DEFAULT_THRESHOLDS["mq135"].copy())
    pressure: Dict[str, float] = field(default_factory=lambda: DEFAULT_THRESHOLDS["pressure"].copy())
    vision: Dict[str, float] = field(default_factory=lambda: DEFAULT_THRESHOLDS["vision"].copy())
    persistence: Dict[str, int] = field(default_factory=lambda: DEFAULT_THRESHOLDS["persistence"].copy())
    data_freshness: Dict[str, float] = field(default_factory=lambda: DEFAULT_THRESHOLDS["data_freshness"].copy())

    @classmethod
    def load(cls, config_path: str | None = None) -> "DecisionThresholds":
        if config_path is None:
            # Default search locations
            candidates = [
                os.path.join("config", "decision_thresholds.yaml"),
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "decision_thresholds.yaml"),
            ]
            for cand in candidates:
                if os.path.exists(cand):
                    config_path = cand
                    break

        if config_path and os.path.exists(config_path) and YAML_AVAILABLE:
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    raw_data = yaml.safe_load(f)
                if isinstance(raw_data, dict):
                    inst = cls()
                    if "temperature" in raw_data and isinstance(raw_data["temperature"], dict):
                        inst.temperature.update(raw_data["temperature"])
                    if "mq4" in raw_data and isinstance(raw_data["mq4"], dict):
                        inst.mq4.update(raw_data["mq4"])
                    if "mq135" in raw_data and isinstance(raw_data["mq135"], dict):
                        inst.mq135.update(raw_data["mq135"])
                    if "pressure" in raw_data and isinstance(raw_data["pressure"], dict):
                        inst.pressure.update(raw_data["pressure"])
                    if "vision" in raw_data and isinstance(raw_data["vision"], dict):
                        inst.vision.update(raw_data["vision"])
                    if "persistence" in raw_data and isinstance(raw_data["persistence"], dict):
                        inst.persistence.update(raw_data["persistence"])
                    if "data_freshness" in raw_data and isinstance(raw_data["data_freshness"], dict):
                        inst.data_freshness.update(raw_data["data_freshness"])
                    return inst
            except Exception as exc:
                logger.warning("Error reading %s, using defaults: %s", config_path, exc)

        return cls()


def get_default_thresholds() -> DecisionThresholds:
    return DecisionThresholds.load()


__all__ = ["DEFAULT_THRESHOLDS", "DecisionThresholds", "get_default_thresholds"]
