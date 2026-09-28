from decision_engine.rules import (
    DEFAULT_RULES,
    rule_blocked_path,
    rule_fire,
    rule_gas,
    rule_smoke,
)


def test_fire_rule_detects_fire_hazard():
    rule = rule_fire({"fire": 0.9, "smoke": 0.8}, {"temperature": 70.0, "smoke": 0.8})

    assert rule["hazard_type"] == "fire"
    assert rule["confidence"] > 0.7


def test_smoke_rule_detects_smoke_hazard():
    rule = rule_smoke({"smoke": 0.9}, {"smoke": 0.75})

    assert rule["hazard_type"] == "smoke"
    assert rule["confidence"] > 0.5


def test_gas_rule_detects_gas_hazard():
    rule = rule_gas({"gas": 0.9})

    assert rule["hazard_type"] == "gas"
    assert rule["confidence"] >= 0.7


def test_blocked_path_rule_for_rock_detection():
    rule = rule_blocked_path({"rock": 0.95})

    assert rule["hazard_type"] == "blocked_path"
    assert rule["confidence"] > 0.6


def test_default_rules_are_configurable_and_present():
    assert DEFAULT_RULES["GAS_WARNING"] == 0.50
    assert DEFAULT_RULES["TEMPERATURE_HIGH"] == 65.0
