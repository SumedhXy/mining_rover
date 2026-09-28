from __future__ import annotations

from typing import Iterable, Mapping, Sequence


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, float(value)))


def combined_confidence(evidence: Iterable[Mapping[str, float]]) -> float:
    items = list(evidence)
    if not items:
        return 0.0

    weighted = sum(float(item.get("confidence", 0.0)) for item in items)
    return round(clamp(weighted / max(len(items), 1)), 6)


def evidence_adjustment(base_confidence: float, supporting_signals: int, conflicting_signals: int = 0) -> float:
    adjusted = base_confidence + 0.08 * supporting_signals - 0.12 * conflicting_signals
    return clamp(adjusted)


__all__ = ["clamp", "combined_confidence", "evidence_adjustment"]
