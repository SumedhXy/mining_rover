from __future__ import annotations

from typing import Any, Dict, List, Optional

from decision_engine.thresholds import DecisionThresholds, get_default_thresholds

# Preserved for backward-compatibility with test_rules.py
DEFAULT_RULES: Dict[str, Any] = {
    "GAS_WARNING": 0.50,
    "GAS_HIGH": 0.75,
    "SMOKE_WARNING": 0.40,
    "SMOKE_HIGH": 0.70,
    "TEMPERATURE_WARNING": 50.0,
    "TEMPERATURE_HIGH": 65.0,
    "ROCK_CONFIDENCE": 0.70,
    "FIRE_CONFIDENCE": 0.70,
    "SMOKE_CONFIDENCE": 0.65,
}


def rule_fire(
    vision: Dict[str, Any],
    sensor: Dict[str, Any],
    thresholds: Optional[DecisionThresholds] = None,
) -> Dict[str, Any]:
    """Evaluate fire hazard combining YOLO fire/smoke detections and sensor heat/combustion indicators."""
    thresh = thresholds or get_default_thresholds()

    fire_conf = float(vision.get("fire", 0.0) or 0.0)
    smoke_conf = float(vision.get("smoke", 0.0) or 0.0)
    temp_c = float(sensor.get("temperature_c") or sensor.get("temperature", 0.0) or 0.0)
    smoke_val = float(
        sensor.get("air_quality")
        or sensor.get("smoke")
        or sensor.get("mq135")
        or 0.0
    )

    min_vis_conf = thresh.vision.get("minimum_confidence", 0.50)
    temp_warn = thresh.temperature.get("warning_c", 45.0)
    temp_high = thresh.temperature.get("high_c", 55.0)
    temp_crit = thresh.temperature.get("critical_c", 65.0)
    smoke_warn = thresh.mq135.get("warning", 0.40)
    smoke_high = thresh.mq135.get("high", 0.60)

    score = 0.0
    reasons: List[str] = []

    if fire_conf >= min_vis_conf:
        score += 0.65 * (fire_conf / 1.0)
        reasons.append(f"Fire detected visually by YOLO with confidence {fire_conf:.2f}")

    if smoke_conf >= min_vis_conf:
        score += 0.20 * (smoke_conf / 1.0)
        reasons.append(f"Smoke detected visually by YOLO with confidence {smoke_conf:.2f}")

    if temp_c >= temp_crit:
        score += 0.35
        reasons.append(f"Critical temperature elevation ({temp_c:.1f} °C >= {temp_crit} °C)")
    elif temp_c >= temp_high:
        score += 0.25
        reasons.append(f"High temperature detected ({temp_c:.1f} °C >= {temp_high} °C)")
    elif temp_c >= temp_warn:
        score += 0.15
        reasons.append(f"Elevated temperature warning ({temp_c:.1f} °C >= {temp_warn} °C)")

    if smoke_val >= smoke_high:
        score += 0.25
        reasons.append(f"MQ-135 air-quality / combustion index elevated to {smoke_val:.2f}")
    elif smoke_val >= smoke_warn:
        score += 0.15
        reasons.append(f"MQ-135 air-quality / combustion index moderately elevated to {smoke_val:.2f}")

    # Fire hazard triggered if score >= 0.45 or strong visual fire >= 0.60
    is_fire = score >= 0.45 or fire_conf >= 0.60
    return {
        "hazard_type": "fire" if is_fire else None,
        "score": min(1.0, score),
        "confidence": min(0.99, max(0.0, score if is_fire else 0.0)),
        "reasons": reasons,
    }


def rule_smoke(
    vision: Dict[str, Any],
    sensor: Dict[str, Any],
    thresholds: Optional[DecisionThresholds] = None,
) -> Dict[str, Any]:
    """Evaluate smoke / poor air quality hazard."""
    thresh = thresholds or get_default_thresholds()

    smoke_vis = float(vision.get("smoke", 0.0) or 0.0)
    smoke_sensor = float(
        sensor.get("air_quality")
        or sensor.get("smoke")
        or sensor.get("mq135")
        or 0.0
    )

    min_vis_conf = thresh.vision.get("minimum_confidence", 0.50)
    smoke_warn = thresh.mq135.get("warning", 0.40)
    smoke_high = thresh.mq135.get("high", 0.60)
    smoke_crit = thresh.mq135.get("critical", 0.80)

    score = 0.0
    reasons: List[str] = []

    if smoke_vis >= min_vis_conf:
        score += 0.50 * (smoke_vis / 1.0)
        reasons.append(f"Smoke detected visually by YOLO with confidence {smoke_vis:.2f}")

    if smoke_sensor >= smoke_crit:
        score += 0.75
        reasons.append(f"MQ-135 sensor at critical air-quality level ({smoke_sensor:.2f})")
    elif smoke_sensor >= smoke_high:
        score += 0.55
        reasons.append(f"MQ-135 sensor elevated ({smoke_sensor:.2f})")
    elif smoke_sensor >= smoke_warn:
        score += 0.35
        reasons.append(f"MQ-135 sensor moderately elevated ({smoke_sensor:.2f})")

    is_smoke = score >= 0.45 or smoke_vis >= 0.70 or smoke_sensor >= smoke_high
    return {
        "hazard_type": "smoke" if is_smoke else None,
        "score": min(1.0, score),
        "confidence": min(0.99, max(0.0, score if is_smoke else 0.0)),
        "reasons": reasons,
    }


def rule_gas(
    sensor: Dict[str, Any],
    thresholds: Optional[DecisionThresholds] = None,
) -> Dict[str, Any]:
    """Evaluate combustible / methane gas hazard. Reports gas level/index without false ppm claims."""
    thresh = thresholds or get_default_thresholds()

    gas_val = float(
        sensor.get("methane")
        or sensor.get("gas")
        or sensor.get("mq4")
        or sensor.get("methane_raw")
        or 0.0
    )

    gas_warn = thresh.mq4.get("warning", 0.40)
    gas_high = thresh.mq4.get("high", 0.60)
    gas_crit = thresh.mq4.get("critical", 0.80)

    if gas_val >= gas_crit:
        return {
            "hazard_type": "gas",
            "score": 1.0,
            "confidence": min(0.98, 0.85 + 0.13 * (gas_val - gas_crit)),
            "reasons": [f"MQ-4 methane sensor index at critical level ({gas_val:.2f} >= {gas_crit})"],
        }
    if gas_val >= gas_high:
        return {
            "hazard_type": "gas",
            "score": 0.85,
            "confidence": 0.85,
            "reasons": [f"MQ-4 methane sensor index elevated ({gas_val:.2f} >= {gas_high})"],
        }
    if gas_val >= gas_warn:
        return {
            "hazard_type": "gas",
            "score": 0.65,
            "confidence": 0.70,
            "reasons": [f"MQ-4 methane sensor index above warning threshold ({gas_val:.2f} >= {gas_warn})"],
        }

    return {
        "hazard_type": None,
        "score": 0.0,
        "confidence": 0.0,
        "reasons": [],
    }


def rule_high_temperature(
    sensor: Dict[str, Any],
    thresholds: Optional[DecisionThresholds] = None,
) -> Dict[str, Any]:
    """Evaluate standalone thermal hazard."""
    thresh = thresholds or get_default_thresholds()

    temp_c = float(sensor.get("temperature_c") or sensor.get("temperature", 0.0) or 0.0)
    temp_warn = thresh.temperature.get("warning_c", 45.0)
    temp_high = thresh.temperature.get("high_c", 55.0)
    temp_crit = thresh.temperature.get("critical_c", 65.0)

    if temp_c >= temp_crit:
        return {
            "hazard_type": "high_temperature",
            "score": 0.95,
            "confidence": 0.92,
            "reasons": [f"Critical ambient temperature ({temp_c:.1f} °C >= {temp_crit} °C)"],
        }
    if temp_c >= temp_high:
        return {
            "hazard_type": "high_temperature",
            "score": 0.75,
            "confidence": 0.80,
            "reasons": [f"High ambient temperature ({temp_c:.1f} °C >= {temp_high} °C)"],
        }
    if temp_c >= temp_warn:
        return {
            "hazard_type": "high_temperature",
            "score": 0.50,
            "confidence": 0.60,
            "reasons": [f"Elevated temperature warning ({temp_c:.1f} °C >= {temp_warn} °C)"],
        }

    return {
        "hazard_type": None,
        "score": 0.0,
        "confidence": 0.0,
        "reasons": [],
    }


def rule_pressure_anomaly(
    sensor: Dict[str, Any],
    thresholds: Optional[DecisionThresholds] = None,
) -> Dict[str, Any]:
    """Evaluate atmospheric pressure anomaly (treated as environmental anomaly, not guaranteed explosion)."""
    thresh = thresholds or get_default_thresholds()

    press_hpa = float(sensor.get("pressure_hpa") or sensor.get("pressure", 0.0) or 0.0)
    if press_hpa <= 0.0:
        return {"hazard_type": None, "score": 0.0, "confidence": 0.0, "reasons": []}

    min_press = thresh.pressure.get("minimum_hpa", 850.0)
    max_press = thresh.pressure.get("maximum_hpa", 1100.0)

    if press_hpa < min_press:
        return {
            "hazard_type": "pressure_anomaly",
            "score": 0.70,
            "confidence": 0.75,
            "reasons": [f"Atmospheric pressure below normal range ({press_hpa:.1f} hPa < {min_press} hPa)"],
        }
    if press_hpa > max_press:
        return {
            "hazard_type": "pressure_anomaly",
            "score": 0.70,
            "confidence": 0.75,
            "reasons": [f"Atmospheric pressure above normal range ({press_hpa:.1f} hPa > {max_press} hPa)"],
        }

    return {
        "hazard_type": None,
        "score": 0.0,
        "confidence": 0.0,
        "reasons": [],
    }


def rule_blocked_path(
    vision: Dict[str, Any],
    thresholds: Optional[DecisionThresholds] = None,
) -> Dict[str, Any]:
    """Evaluate navigational obstacles (rock, debris). Reports hazard only; does NOT command motors."""
    thresh = thresholds or get_default_thresholds()
    min_conf = thresh.vision.get("minimum_confidence", 0.50)

    rock_conf = float(vision.get("rock", 0.0) or 0.0)
    debris_conf = float(vision.get("debris", 0.0) or 0.0)

    reasons: List[str] = []
    score = 0.0

    if rock_conf >= min_conf:
        score += 0.70 * (rock_conf / 1.0)
        reasons.append(f"Rock obstacle detected visually with confidence {rock_conf:.2f}")
    if debris_conf >= min_conf:
        score += 0.60 * (debris_conf / 1.0)
        reasons.append(f"Debris detected visually with confidence {debris_conf:.2f}")

    if not reasons:
        return {"hazard_type": None, "score": 0.0, "confidence": 0.0, "reasons": []}

    return {
        "hazard_type": "blocked_path",
        "score": min(1.0, score),
        "confidence": min(0.99, max(0.0, score)),
        "reasons": reasons,
    }


def rule_person(vision: Dict[str, Any], hazard_type: str) -> Dict[str, Any]:
    """Check if personnel are present in a hazard zone."""
    person_conf = float(vision.get("person", 0.0) or 0.0)
    if person_conf <= 0.0:
        return {"hazard_type": hazard_type, "score": 0.0, "confidence": 0.0, "reasons": []}
    return {
        "hazard_type": hazard_type,
        "score": 0.10,
        "confidence": min(0.90, person_conf * 0.75),
        "reasons": [f"Person detected in area with confidence {person_conf:.2f}"],
    }


__all__ = [
    "DEFAULT_RULES",
    "rule_fire",
    "rule_smoke",
    "rule_gas",
    "rule_high_temperature",
    "rule_pressure_anomaly",
    "rule_blocked_path",
    "rule_person",
]
