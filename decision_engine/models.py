from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class Evidence:
    """Individual piece of supporting evidence from sensors or vision."""

    source: str
    type: str
    confidence: float
    value: Optional[float] = None
    details: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise TypeError("confidence must be numeric")
        self.confidence = float(self.confidence)
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass
class HazardAssessment:
    """Standardized decision engine output assessing hazards, severity, and supporting evidence."""

    timestamp: str
    hazard_type: str
    severity: str
    confidence: float
    reasons: List[str] = field(default_factory=list)
    vision_evidence: List[Any] = field(default_factory=list)
    sensor_evidence: List[Any] = field(default_factory=list)
    source: str = "sensor_vision_fusion"
    decision_id: Optional[str] = None
    all_hazards: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.confidence, (int, float)) or isinstance(self.confidence, bool):
            raise TypeError("confidence must be numeric")
        self.confidence = round(max(0.0, min(1.0, float(self.confidence))), 4)

        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

        if not self.decision_id:
            self.decision_id = str(uuid.uuid4())[:8]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize hazard assessment to JSON-serializable dictionary."""
        vis_ev = []
        for v in self.vision_evidence:
            if isinstance(v, Evidence):
                vis_ev.append(asdict(v))
            elif isinstance(v, dict):
                vis_ev.append(v)
            else:
                vis_ev.append(str(v))

        sens_ev = []
        for s in self.sensor_evidence:
            if isinstance(s, Evidence):
                sens_ev.append(asdict(s))
            elif isinstance(s, dict):
                sens_ev.append(s)
            else:
                sens_ev.append(str(s))

        return {
            "timestamp": self.timestamp,
            "decision_id": self.decision_id,
            "hazard_type": self.hazard_type,
            "severity": self.severity,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "vision_evidence": vis_ev,
            "sensor_evidence": sens_ev,
            "source": self.source,
            "all_hazards": list(self.all_hazards),
        }


__all__ = ["Evidence", "HazardAssessment"]
