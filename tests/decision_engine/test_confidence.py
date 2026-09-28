from decision_engine.confidence import clamp, combined_confidence, evidence_adjustment


def test_clamp_keeps_values_in_range():
    assert clamp(1.5) == 1.0
    assert clamp(-0.2) == 0.0
    assert clamp(0.5) == 0.5


def test_combined_confidence_averages_evidence():
    confidence = combined_confidence([{"confidence": 0.9}, {"confidence": 0.8}, {"confidence": 0.7}])
    assert confidence == 0.8


def test_evidence_adjustment_increases_with_support():
    score = evidence_adjustment(0.5, supporting_signals=2, conflicting_signals=1)
    assert score > 0.4
    assert score <= 1.0
