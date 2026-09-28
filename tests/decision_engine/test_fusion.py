from decision_engine.fusion import build_evidence, fuse_hazard_signals, normalize_sensor_input, normalize_vision_input


def test_normalize_vision_input_extracts_detection_scores():
    data = {
        "detections": [
            {"class_name": "fire", "confidence": 0.9},
            {"class_name": "smoke", "confidence": 0.6},
        ]
    }

    result = normalize_vision_input(data)

    assert result["fire"] == 0.9
    assert result["smoke"] == 0.6


def test_normalize_sensor_input_keeps_expected_fields():
    result = normalize_sensor_input({
        "temperature": 67.0,
        "humidity": 44.0,
        "gas": 0.7,
        "smoke": 0.8,
    })

    assert result["temperature"] == 67.0
    assert result["gas"] == 0.7
    assert result["smoke"] == 0.8


def test_fusion_scores_combined_evidence():
    vision = normalize_vision_input({"detections": [{"class_name": "fire", "confidence": 0.9}]})
    sensor = normalize_sensor_input({"temperature": 70.0, "smoke": 0.8})

    fused = fuse_hazard_signals(vision, sensor)

    assert "combined" in fused
    assert fused["combined"] >= 0.0


def test_build_evidence_returns_standardized_lists():
    evidence = build_evidence({"fire": 0.9}, {"temperature": 70.0})

    assert len(evidence["vision_evidence"]) == 1
    assert len(evidence["sensor_evidence"]) == 1
    assert evidence["vision_evidence"][0].type == "fire"
