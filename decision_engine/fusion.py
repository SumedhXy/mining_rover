from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from decision_engine.confidence import clamp, combined_confidence
from decision_engine.models import Evidence


def check_staleness(timestamp_str: Optional[str], max_age_seconds: float) -> Tuple[bool, float]:
    """Check if a timestamp is older than max_age_seconds."""
    if not timestamp_str or not isinstance(timestamp_str, str):
        return False, 0.0

    try:
        iso_str = timestamp_str.strip()
        if iso_str.endswith("Z"):
            iso_str = iso_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(iso_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        age = (now - dt).total_seconds()
        # Protect against slight clock skew
        if age < 0:
            age = 0.0
        return (age > max_age_seconds), round(age, 2)
    except Exception:
        return False, 0.0


def normalize_vision_input(vision_data: Any) -> Dict[str, float]:
    """Extract class confidence scores from YOLO vision output.
    
    Supports:
        - Dictionary with 'detections' list
        - Direct list of detection dictionaries
        - Direct mapping of class_name -> confidence
    """
    if not vision_data:
        return {}

    normalized: Dict[str, float] = {}

    detections = []
    if isinstance(vision_data, list):
        detections = vision_data
    elif isinstance(vision_data, dict):
        if "detections" in vision_data and isinstance(vision_data["detections"], list):
            detections = vision_data["detections"]
        else:
            # Check for direct class-to-confidence mapping
            for k, v in vision_data.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    normalized[k.lower()] = clamp(float(v))

    for detection in detections:
        if not isinstance(detection, dict):
            continue
        class_name = str(detection.get("class_name") or detection.get("class") or "").lower()
        if not class_name:
            continue
        confidence = float(detection.get("confidence", 0.0) or 0.0)
        normalized[class_name] = max(normalized.get(class_name, 0.0), clamp(confidence))

    return normalized


def normalize_sensor_input(sensor_data: Any) -> Dict[str, float]:
    """Normalize sensor inputs from Phase 1 StandardSensorReading or dictionary."""
    if not sensor_data:
        return {}

    # Support StandardSensorReading instance
    if hasattr(sensor_data, "to_dict") and callable(getattr(sensor_data, "to_dict")):
        data = sensor_data.to_dict()
    elif hasattr(sensor_data, "__dict__"):
        data = vars(sensor_data)
    elif isinstance(sensor_data, dict):
        data = sensor_data
    else:
        return {}

    temp = (
        data.get("temperature_c")
        if data.get("temperature_c") is not None
        else data.get("temperature", 0.0)
    )
    hum = (
        data.get("humidity_percent")
        if data.get("humidity_percent") is not None
        else data.get("humidity", 0.0)
    )
    press = (
        data.get("pressure_hpa")
        if data.get("pressure_hpa") is not None
        else data.get("pressure", 1013.25)
    )
    gas = (
        data.get("methane")
        if data.get("methane") is not None
        else (data.get("mq4") if data.get("mq4") is not None else data.get("gas", 0.0))
    )
    smoke = (
        data.get("air_quality")
        if data.get("air_quality") is not None
        else (data.get("mq135") if data.get("mq135") is not None else data.get("smoke", 0.0))
    )

    try:
        temp_f = float(temp or 0.0)
        hum_f = float(hum or 0.0)
        press_f = float(press or 1013.25)
        gas_f = float(gas or 0.0)
        smoke_f = float(smoke or 0.0)
    except (ValueError, TypeError):
        temp_f, hum_f, press_f, gas_f, smoke_f = 0.0, 0.0, 1013.25, 0.0, 0.0

    return {
        "temperature": temp_f,
        "temperature_c": temp_f,
        "humidity": hum_f,
        "humidity_percent": hum_f,
        "pressure": press_f,
        "pressure_hpa": press_f,
        "gas": gas_f,
        "methane": gas_f,
        "mq4": gas_f,
        "smoke": smoke_f,
        "air_quality": smoke_f,
        "mq135": smoke_f,
    }


def build_evidence(vision_scores: Dict[str, float], sensor_scores: Dict[str, float]) -> Dict[str, List[Evidence]]:
    """Build structured Evidence objects for explainability."""
    vision_evidence = [
        Evidence(source="vision", type=name, confidence=clamp(value), value=value)
        for name, value in vision_scores.items()
        if value > 0.0
    ]
    sensor_evidence = [
        Evidence(
            source="sensor",
            type=name,
            confidence=clamp(value if name in {"gas", "smoke", "methane", "air_quality"} else min(1.0, value / 100.0)),
            value=value,
        )
        for name, value in sensor_scores.items()
        if name in {"temperature", "gas", "smoke", "pressure_hpa"}
    ]

    return {"vision_evidence": vision_evidence, "sensor_evidence": sensor_evidence}


def fuse_hazard_signals(vision_scores: Dict[str, float], sensor_scores: Dict[str, float]) -> Dict[str, float]:
    """Fuse multiple sensor & vision signals into composite hazard indicators."""
    scores: Dict[str, float] = {}

    fire_v = vision_scores.get("fire", 0.0)
    smoke_v = vision_scores.get("smoke", 0.0)
    temp_s = sensor_scores.get("temperature", 0.0)
    gas_s = sensor_scores.get("gas", 0.0)
    smoke_s = sensor_scores.get("smoke", 0.0)

    # Multi-modal fusion for fire
    fire_fusion = 0.5 * fire_v + 0.25 * (temp_s / 100.0) + 0.25 * smoke_s
    scores["fire"] = clamp(fire_fusion)

    # Multi-modal fusion for smoke
    smoke_fusion = 0.55 * smoke_v + 0.45 * smoke_s
    scores["smoke"] = clamp(smoke_fusion)

    # Gas is primary sensor
    scores["gas"] = clamp(gas_s)

    # Combined general danger score
    scores["combined"] = clamp(max(fire_fusion, smoke_fusion, gas_s))

    return scores


__all__ = [
    "check_staleness",
    "normalize_vision_input",
    "normalize_sensor_input",
    "build_evidence",
    "fuse_hazard_signals",
]
