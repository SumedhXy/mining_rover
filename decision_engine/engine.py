from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from decision_engine.confidence import clamp
from decision_engine.fusion import (
    build_evidence,
    check_staleness,
    fuse_hazard_signals,
    normalize_sensor_input,
    normalize_vision_input,
)
from decision_engine.models import Evidence, HazardAssessment
from decision_engine.rules import (
    rule_blocked_path,
    rule_fire,
    rule_gas,
    rule_high_temperature,
    rule_person,
    rule_pressure_anomaly,
    rule_smoke,
)
from decision_engine.thresholds import DecisionThresholds, get_default_thresholds

logger = logging.getLogger("decision_engine")

SEVERITY_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def severity_from_score(score: float) -> str:
    """Map a normalized score [0, 1] to a discrete severity level."""
    score = clamp(score)
    if score >= 0.85:
        return "CRITICAL"
    if score >= 0.65:
        return "HIGH"
    if score >= 0.40:
        return "MEDIUM"
    if score >= 0.15:
        return "LOW"
    return "NONE"


class DecisionEngine:
    """Hazard assessment intelligence engine.
    
    Evaluates multi-modal sensor and vision inputs to identify hazards,
    calculate severity, compute confidence, and provide explainable reasons.
    
    CRITICAL ARCHITECTURAL BOUNDARY:
    This engine evaluates hazards only. It does NOT command motors, wheels,
    actuators, or navigation logic.
    """

    def __init__(self, thresholds: Optional[DecisionThresholds] = None) -> None:
        self.thresholds = thresholds or get_default_thresholds()
        self._consecutive_counts: Dict[str, int] = defaultdict(int)
        self._last_hazard_type: Optional[str] = None
        self._last_severity: Optional[str] = None

    def reset_state(self) -> None:
        """Reset temporal persistence history."""
        self._consecutive_counts.clear()
        self._last_hazard_type = None
        self._last_severity = None

    def evaluate(
        self,
        vision_data: Optional[Any],
        sensor_data: Optional[Any],
    ) -> HazardAssessment:
        """Perform full multi-modal hazard assessment on sensor and vision inputs."""
        now_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

        # 1. Handle completely missing / empty inputs gracefully
        if not vision_data and not sensor_data:
            return HazardAssessment(
                timestamp=now_iso,
                hazard_type="none",
                severity="NONE",
                confidence=0.0,
                reasons=["Insufficient input data: both sensor and vision inputs are unavailable"],
                vision_evidence=[],
                sensor_evidence=[],
                source="decision_engine",
                all_hazards=[],
            )

        # 2. Check for staleness
        staleness_reasons: List[str] = []

        sensor_ts = None
        if isinstance(sensor_data, dict):
            sensor_ts = sensor_data.get("timestamp")
        elif hasattr(sensor_data, "timestamp"):
            sensor_ts = getattr(sensor_data, "timestamp")

        if sensor_ts:
            max_age = self.thresholds.data_freshness.get("sensor_max_age_seconds", 5.0)
            is_stale, age = check_staleness(sensor_ts, max_age)
            if is_stale:
                staleness_reasons.append(f"Sensor data is stale ({age:.1f}s > {max_age}s max age)")

        vision_ts = None
        if isinstance(vision_data, dict):
            vision_ts = vision_data.get("timestamp")

        if vision_ts:
            max_age_v = self.thresholds.data_freshness.get("vision_max_age_seconds", 2.0)
            is_stale_v, age_v = check_staleness(vision_ts, max_age_v)
            if is_stale_v:
                staleness_reasons.append(f"Vision data is stale ({age_v:.1f}s > {max_age_v}s max age)")

        # 3. Normalize inputs
        vision = normalize_vision_input(vision_data)
        sensor = normalize_sensor_input(sensor_data)
        evidence = build_evidence(vision, sensor)
        _ = fuse_hazard_signals(vision, sensor)

        # 4. Evaluate individual hazard rules
        candidates: List[Dict[str, Any]] = []

        fire_res = rule_fire(vision, sensor, self.thresholds)
        if fire_res.get("hazard_type"):
            candidates.append(fire_res)

        gas_res = rule_gas(sensor, self.thresholds)
        if gas_res.get("hazard_type"):
            candidates.append(gas_res)

        smoke_res = rule_smoke(vision, sensor, self.thresholds)
        if smoke_res.get("hazard_type"):
            candidates.append(smoke_res)

        temp_res = rule_high_temperature(sensor, self.thresholds)
        if temp_res.get("hazard_type") and not fire_res.get("hazard_type"):
            candidates.append(temp_res)

        press_res = rule_pressure_anomaly(sensor, self.thresholds)
        if press_res.get("hazard_type"):
            candidates.append(press_res)

        blocked_res = rule_blocked_path(vision, self.thresholds)
        if blocked_res.get("hazard_type"):
            candidates.append(blocked_res)

        # 5. Build all_hazards list (Section 14: Multiple simultaneous hazards)
        all_hazards: List[Dict[str, Any]] = []
        for cand in candidates:
            h_type = cand["hazard_type"]
            c_score = cand["confidence"]
            all_hazards.append({
                "hazard_type": h_type,
                "severity": severity_from_score(c_score),
                "confidence": round(c_score, 4),
                "reasons": list(cand.get("reasons", [])),
            })

        # 6. No-hazard condition
        if not candidates:
            # Check if any input was provided at all
            reasons = ["No configured hazard thresholds exceeded"]
            if staleness_reasons:
                reasons.extend(staleness_reasons)

            self._consecutive_counts.clear()
            self._last_hazard_type = "none"
            self._last_severity = "NONE"

            return HazardAssessment(
                timestamp=now_iso,
                hazard_type="none",
                severity="NONE",
                confidence=0.05,
                reasons=reasons,
                vision_evidence=[
                    {"source": item.source, "type": item.type, "confidence": item.confidence}
                    for item in evidence["vision_evidence"]
                ],
                sensor_evidence=[
                    {"source": item.source, "type": item.type, "confidence": item.confidence}
                    for item in evidence["sensor_evidence"]
                ],
                source="sensor_vision_fusion",
                all_hazards=[],
            )

        # 7. Select primary hazard
        best = max(candidates, key=lambda item: item["score"])
        primary_hazard = best["hazard_type"]
        confidence = clamp(best["confidence"])
        reasons_list = list(best["reasons"])

        # Personnel detection in hazard zone increases awareness
        if vision.get("person", 0.0) > 0.0:
            person_result = rule_person(vision, primary_hazard)
            if person_result.get("reasons"):
                reasons_list.extend(person_result["reasons"])
                confidence = clamp(confidence + 0.05)

        # Check for disagreement between vision and sensor
        if "smoke" in vision and "smoke" in sensor:
            if vision.get("smoke", 0.0) >= 0.70 and sensor.get("smoke", 0.0) < 0.20:
                reasons_list.append("Vision and sensor evidence disagree")
                confidence = clamp(confidence - 0.15)

        if staleness_reasons:
            reasons_list.extend(staleness_reasons)
            confidence = clamp(confidence * 0.85)

        # 8. Temporal stability / persistence tracking
        req_readings = self.thresholds.persistence.get("required_readings", 3)
        self._consecutive_counts[primary_hazard] += 1
        current_streak = self._consecutive_counts[primary_hazard]

        # Reset counts for other hazards
        for other_h in list(self._consecutive_counts.keys()):
            if other_h != primary_hazard:
                self._consecutive_counts[other_h] = max(0, self._consecutive_counts[other_h] - 1)

        raw_severity = severity_from_score(confidence)
        # If persistence required and readings < threshold, annotate persistence info
        if req_readings > 1 and current_streak < req_readings:
            reasons_list.append(f"Persistence check: sample {current_streak}/{req_readings} required for confirmed persistence")

        severity = raw_severity

        # Deduplicate reasons
        unique_reasons = list(dict.fromkeys(reasons_list))

        # Rate-limited state-change logging
        if primary_hazard != self._last_hazard_type or severity != self._last_severity:
            logger.info(
                "Hazard state transition: [%s] -> [%s | %s | conf=%.2f]",
                self._last_hazard_type,
                primary_hazard.upper(),
                severity,
                confidence,
            )
            self._last_hazard_type = primary_hazard
            self._last_severity = severity

        return HazardAssessment(
            timestamp=now_iso,
            hazard_type=primary_hazard,
            severity=severity,
            confidence=confidence,
            reasons=unique_reasons,
            vision_evidence=[
                {"source": item.source, "type": item.type, "confidence": item.confidence}
                for item in evidence["vision_evidence"]
            ],
            sensor_evidence=[
                {"source": item.source, "type": item.type, "confidence": item.confidence}
                for item in evidence["sensor_evidence"]
            ],
            source="sensor_vision_fusion",
            all_hazards=all_hazards,
        )


# Global default engine instance for functional evaluate() calls
_default_engine = DecisionEngine()


def select_hazard(vision: Dict[str, float], sensor: Dict[str, float]) -> Dict[str, Any]:
    """Backward-compatible helper used in legacy tests."""
    thresh = get_default_thresholds()
    candidates = []

    fire_res = rule_fire(vision, sensor, thresh)
    if fire_res.get("hazard_type"):
        candidates.append(fire_res)

    gas_res = rule_gas(sensor, thresh)
    if gas_res.get("hazard_type"):
        candidates.append(gas_res)

    smoke_res = rule_smoke(vision, sensor, thresh)
    if smoke_res.get("hazard_type"):
        candidates.append(smoke_res)

    blocked_res = rule_blocked_path(vision, thresh)
    if blocked_res.get("hazard_type"):
        candidates.append(blocked_res)

    if not candidates:
        return {
            "hazard_type": "none",
            "severity": "LOW",
            "confidence": 0.2,
            "reasons": ["No significant hazard evidence detected"],
            "score": 0.0,
        }

    best = max(candidates, key=lambda item: item["score"])
    confidence = clamp(best["confidence"])
    reason_parts = list(best["reasons"])

    if "smoke" in vision and "smoke" in sensor:
        if vision.get("smoke", 0.0) >= 0.70 and sensor.get("smoke", 0.0) < 0.20:
            reason_parts.append("Vision and sensor evidence disagree")
            confidence = clamp(confidence - 0.15)

    return {
        "hazard_type": best["hazard_type"],
        "severity": severity_from_score(confidence),
        "confidence": confidence,
        "reasons": list(dict.fromkeys(reason_parts)),
        "score": best["score"],
    }


def evaluate(
    vision_data: Optional[Any],
    sensor_data: Optional[Any],
    thresholds: Optional[DecisionThresholds] = None,
) -> HazardAssessment:
    """Public evaluate function for backward-compatibility and easy usage."""
    if thresholds is not None:
        engine = DecisionEngine(thresholds=thresholds)
        return engine.evaluate(vision_data, sensor_data)
    return _default_engine.evaluate(vision_data, sensor_data)


__all__ = ["DecisionEngine", "evaluate", "severity_from_score", "select_hazard"]
