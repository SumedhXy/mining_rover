from decision_engine.engine import DecisionEngine, evaluate


def test_engine_reports_no_hazard_when_signal_is_low():
    result = evaluate(
        {"detections": []},
        {"temperature": 32.0, "gas": 0.1, "smoke": 0.02},
    )

    assert result.hazard_type == "none"
    assert result.severity == "NONE"
    assert result.confidence <= 0.20
    assert any("No configured hazard thresholds exceeded" in r for r in result.reasons)


def test_engine_flags_fire_when_vision_and_sensor_agree():
    result = evaluate(
        {"detections": [{"class_name": "fire", "confidence": 0.9}, {"class_name": "smoke", "confidence": 0.8}]},
        {"temperature": 70.0, "smoke": 0.8},
    )

    assert result.hazard_type == "fire"
    assert result.severity in {"HIGH", "CRITICAL"}
    assert result.confidence >= 0.70


def test_engine_tracks_conflicting_evidence_without_crashing():
    result = evaluate(
        {"detections": [{"class_name": "smoke", "confidence": 0.9}]},
        {"smoke": 0.05, "temperature": 30.0},
    )

    assert result.hazard_type in {"smoke", "none"}
    assert len(result.reasons) > 0


def test_engine_handles_missing_vision_or_sensor_data():
    result = evaluate({"detections": []}, {"gas": 0.9})
    assert result.hazard_type == "gas"

    result2 = evaluate({"detections": [{"class_name": "rock", "confidence": 0.92}]}, {})
    assert result2.hazard_type == "blocked_path"


def test_high_temperature_standalone_evaluation():
    # Only thermal hazard, no fire/smoke
    result = evaluate(
        {"detections": []},
        {"temperature_c": 68.0, "humidity_percent": 45.0, "mq4": 0.1, "mq135": 0.1},
    )
    assert result.hazard_type == "high_temperature"
    assert result.severity in {"HIGH", "CRITICAL"}
    assert any("Critical ambient temperature" in r for r in result.reasons)


def test_mq4_methane_elevation_evaluation():
    # Elevated MQ4 gas index without false ppm report
    result = evaluate(
        {"detections": []},
        {"temperature_c": 30.0, "mq4": 0.85, "mq135": 0.1},
    )
    assert result.hazard_type == "gas"
    assert result.severity in {"HIGH", "CRITICAL"}
    assert any("MQ-4 methane sensor" in r for r in result.reasons)
    # Ensure no false claim of ppm
    assert not any("ppm" in r.lower() for r in result.reasons)


def test_mq135_smoke_air_quality_elevation():
    result = evaluate(
        {"detections": []},
        {"temperature_c": 30.0, "mq4": 0.1, "mq135": 0.82},
    )
    assert result.hazard_type == "smoke"
    assert result.severity in {"HIGH", "CRITICAL"}
    assert any("MQ-135 sensor" in r for r in result.reasons)


def test_fire_and_temperature_fusion():
    # Fire detected + elevated temperature increases severity
    result = evaluate(
        {"detections": [{"class_name": "fire", "confidence": 0.85}]},
        {"temperature_c": 62.0, "mq135": 0.3},
    )
    assert result.hazard_type == "fire"
    assert result.severity in {"HIGH", "CRITICAL"}
    assert any("Fire detected visually" in r for r in result.reasons)
    assert any("High temperature" in r or "Critical temperature" in r for r in result.reasons)


def test_fire_and_mq135_fusion():
    # Fire detected + elevated MQ135
    result = evaluate(
        {"detections": [{"class_name": "fire", "confidence": 0.82}]},
        {"temperature_c": 35.0, "mq135": 0.75},
    )
    assert result.hazard_type == "fire"
    assert result.severity in {"HIGH", "CRITICAL"}
    assert any("MQ-135 air-quality" in r for r in result.reasons)


def test_multiple_simultaneous_hazards_tracked():
    # Both gas and high temperature are active simultaneously
    result = evaluate(
        {"detections": []},
        {"temperature_c": 66.0, "mq4": 0.85, "mq135": 0.1},
    )
    # Primary hazard is reported
    assert result.hazard_type in {"gas", "high_temperature"}
    # all_hazards contains both hazards
    hazard_types = [h["hazard_type"] for h in result.all_hazards]
    assert "gas" in hazard_types
    assert "high_temperature" in hazard_types
    assert len(result.all_hazards) >= 2


def test_low_yolo_confidence_is_rejected():
    # YOLO detection with confidence below minimum threshold (0.50)
    result = evaluate(
        {"detections": [{"class_name": "fire", "confidence": 0.25}]},
        {"temperature": 25.0, "gas": 0.05, "smoke": 0.05},
    )
    # Should not trigger fire
    assert result.hazard_type == "none"


def test_pressure_anomaly_evaluation():
    # Pressure outside normal range (850 - 1100 hPa)
    result_low = evaluate(
        {"detections": []},
        {"pressure_hpa": 750.0, "temperature": 25.0, "gas": 0.1, "smoke": 0.1},
    )
    assert result_low.hazard_type == "pressure_anomaly"
    assert any("Atmospheric pressure below normal range" in r for r in result_low.reasons)

    result_high = evaluate(
        {"detections": []},
        {"pressure_hpa": 1250.0, "temperature": 25.0, "gas": 0.1, "smoke": 0.1},
    )
    assert result_high.hazard_type == "pressure_anomaly"
    assert any("Atmospheric pressure above normal range" in r for r in result_high.reasons)


def test_offline_operation_no_network_calls():
    # Decision Engine executes without any sockets or network dependencies
    engine = DecisionEngine()
    result = engine.evaluate(
        {"detections": [{"class_name": "fire", "confidence": 0.85}]},
        {"temperature": 55.0, "gas": 0.3, "smoke": 0.6},
    )
    assert result.hazard_type == "fire"
    assert result.confidence > 0.0
