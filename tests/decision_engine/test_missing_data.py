from datetime import datetime, timezone, timedelta
from decision_engine.engine import DecisionEngine, evaluate
from decision_engine.models import HazardAssessment


def test_both_inputs_missing_returns_safe_assessment():
    res = evaluate(None, None)
    assert isinstance(res, HazardAssessment)
    assert res.hazard_type == "none"
    assert res.severity == "NONE"
    assert res.confidence == 0.0
    assert any("Insufficient input data" in r for r in res.reasons)


def test_empty_dictionaries_returns_safe_assessment():
    res = evaluate({}, {})
    assert res.hazard_type == "none"
    assert res.severity == "NONE"
    assert res.confidence == 0.0


def test_sensor_data_only_evaluates_hazards():
    # Only sensor data provided (e.g. camera offline)
    res = evaluate(
        None,
        {"temperature_c": 35.0, "humidity_percent": 50.0, "mq4": 0.85, "mq135": 0.20},
    )
    assert res.hazard_type == "gas"
    assert res.severity in {"HIGH", "CRITICAL"}
    assert res.confidence >= 0.70
    assert len(res.reasons) > 0


def test_vision_data_only_evaluates_hazards():
    # Only vision data provided (e.g. sensor node disconnected)
    res = evaluate(
        {"detections": [{"class_name": "fire", "confidence": 0.88}]},
        None,
    )
    assert res.hazard_type == "fire"
    assert res.severity in {"MEDIUM", "HIGH", "CRITICAL"}
    assert res.confidence >= 0.50
    assert len(res.reasons) > 0


def test_invalid_and_corrupt_sensor_values_handled_gracefully():
    # Non-numeric or missing sensor values
    res = evaluate(
        {"detections": []},
        {"temperature": "EXTREME_HEAT", "humidity": None, "gas": -5.0, "smoke": "heavy"},
    )
    # Does not crash, handles gracefully
    assert isinstance(res, HazardAssessment)
    assert res.hazard_type in {"none", "gas", "smoke"}


def test_stale_sensor_data_is_detected_and_flagged():
    old_time = (datetime.now(timezone.utc) - timedelta(seconds=15)).isoformat()
    res = evaluate(
        {"detections": []},
        {
            "timestamp": old_time,
            "temperature_c": 32.0,
            "humidity_percent": 50.0,
            "mq4": 0.1,
            "mq135": 0.1,
        },
    )
    assert any("Sensor data is stale" in r for r in res.reasons)


def test_stale_vision_data_is_detected_and_flagged():
    old_time = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    res = evaluate(
        {
            "timestamp": old_time,
            "detections": [{"class_name": "fire", "confidence": 0.80}],
        },
        {"temperature": 25.0, "gas": 0.1, "smoke": 0.1},
    )
    assert any("Vision data is stale" in r for r in res.reasons)
