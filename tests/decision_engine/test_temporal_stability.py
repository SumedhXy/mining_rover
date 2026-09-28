import inspect
from decision_engine.engine import DecisionEngine
from decision_engine.thresholds import DecisionThresholds


def test_temporal_persistence_tracking():
    custom_thresholds = DecisionThresholds()
    custom_thresholds.persistence["required_readings"] = 3

    engine = DecisionEngine(thresholds=custom_thresholds)

    sensor_gas = {"mq4": 0.85, "temperature_c": 30.0}

    # Reading 1: transient spike
    res1 = engine.evaluate(None, sensor_gas)
    assert res1.hazard_type == "gas"
    assert any("sample 1/3 required" in r for r in res1.reasons)

    # Reading 2: ongoing
    res2 = engine.evaluate(None, sensor_gas)
    assert res2.hazard_type == "gas"
    assert any("sample 2/3 required" in r for r in res2.reasons)

    # Reading 3: persistent confirmed
    res3 = engine.evaluate(None, sensor_gas)
    assert res3.hazard_type == "gas"
    # Once 3 readings achieved, confirmed without persistence warning
    assert not any("sample" in r and "required" in r for r in res3.reasons)


def test_persistence_streak_resets_when_hazard_clears():
    custom_thresholds = DecisionThresholds()
    custom_thresholds.persistence["required_readings"] = 3
    engine = DecisionEngine(thresholds=custom_thresholds)

    sensor_gas = {"mq4": 0.85, "temperature_c": 30.0}
    sensor_clear = {"mq4": 0.10, "temperature_c": 30.0}

    # Reading 1: spike
    engine.evaluate(None, sensor_gas)
    # Reading 2: clear
    res_clear = engine.evaluate(None, sensor_clear)
    assert res_clear.hazard_type == "none"

    # Reading 3: gas appears again -> starts back at sample 1
    res_again = engine.evaluate(None, sensor_gas)
    assert any("sample 1/3 required" in r for r in res_again.reasons)


def test_engine_reset_state():
    engine = DecisionEngine()
    engine.evaluate(None, {"mq4": 0.85})
    assert len(engine._consecutive_counts) > 0

    engine.reset_state()
    assert len(engine._consecutive_counts) == 0
    assert engine._last_hazard_type is None


def test_confidence_values_always_bounded():
    engine = DecisionEngine()
    scenarios = [
        ({"detections": [{"class_name": "fire", "confidence": 1.5}]}, {"temperature": 150.0}),
        (None, {"mq4": -20.0}),
        ({"detections": []}, {"pressure_hpa": 1200.0}),
        (None, None),
    ]

    for v, s in scenarios:
        res = engine.evaluate(v, s)
        assert 0.0 <= res.confidence <= 1.0


def test_safety_separation_no_motor_control_artifacts():
    import decision_engine
    import decision_engine.engine
    import decision_engine.rules
    import decision_engine.fusion
    import decision_engine.models

    forbidden_keywords = [
        "set_motor_speed",
        "motor_speed",
        "motor_command",
        "drive_command",
        "wheel_speed",
        "turn_left",
        "turn_right",
        "pwm",
        "navigate_to",
        "rover_move",
    ]

    for mod in [decision_engine.engine, decision_engine.rules, decision_engine.fusion, decision_engine.models]:
        source_code = inspect.getsource(mod).lower()
        for kw in forbidden_keywords:
            assert kw not in source_code, f"Found forbidden motor/drive keyword '{kw}' in {mod.__name__}"
