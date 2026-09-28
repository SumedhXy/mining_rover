# Mining Rover — Phase 2: Decision Engine

## 1. Purpose

Phase 2 builds the Decision Engine for the Mining Rover software.

The Decision Engine combines:

1. YOLO visual detections
2. Sensor readings
3. Confidence values
4. Hazard rules

and produces a structured hazard assessment.

The Decision Engine is the reasoning layer between perception and the rest of the system.

The engine must NOT directly control motors or other physical actuators.

---

# 2. Overall Architecture

The Decision Engine receives two independent sources of information.

### Vision

    Camera
       ↓
    YOLO Model
       ↓
    Visual Detections

### Sensors

    Physical Sensors / Simulator
       ↓
    Sensor Service
       ↓
    Sensor Reading

Both are passed to:

    ┌──────────────────────────────┐
    │       Decision Engine        │
    │                              │
    │  Vision + Sensor Fusion      │
    │  Hazard Rules                │
    │  Confidence Evaluation       │
    │  Severity Calculation        │
    └──────────────┬───────────────┘
                   ↓
           Hazard Assessment

---

# 3. Phase 2 Scope

## Included

- Vision input interface
- Sensor input interface
- Hazard definitions
- Rule engine
- Multimodal data fusion
- Confidence calculation
- Severity calculation
- Hazard assessment schema
- Explanation/reason generation
- Unit tests

## NOT included

- SQLite database
- FastAPI
- React dashboard
- Online/offline synchronization
- Motor control
- Autonomous navigation
- Rover movement
- Hardware drivers
- YOLO training

Those are handled in later phases.

---

# 4. Important Design Principle

The Decision Engine must NOT directly depend on the YOLO implementation.

It should receive standardized visual detection data.

For example:

    {
        "class_name": "rock",
        "confidence": 0.91,
        "bbox": [120, 200, 400, 500]
    }

The Decision Engine should not care whether the detection came from:

- YOLO11
- YOLOv8
- another vision model
- a simulator

Similarly, it should not directly communicate with physical sensors.

It receives standardized sensor readings from Phase 1.

---

# 5. Project Structure

Create:

    decision_engine/
    │
    ├── engine.py
    ├── fusion.py
    ├── rules.py
    ├── hazard_schema.py
    └── confidence.py

Tests:

    tests/
    └── decision_engine/
        ├── test_rules.py
        ├── test_fusion.py
        ├── test_confidence.py
        └── test_engine.py

---

# 6. Inputs

The Decision Engine has two primary inputs.

## 6.1 Vision Input

Example:

    {
        "timestamp": "2026-09-27T14:00:00+05:30",
        "detections": [
            {
                "class_name": "rock",
                "confidence": 0.91,
                "bbox": [120, 200, 400, 500]
            }
        ]
    }

Possible visual classes for the current Mining Rover system may include:

    person
    fire
    smoke
    debris
    rock

The final class list must match the trained YOLO model.

Do not hard-code assumptions that are not present in the trained model.

---

# 7. Sensor Input

The Decision Engine receives the standardized sensor reading from Phase 1.

Example:

    {
        "timestamp": "2026-09-27T14:00:00+05:30",
        "temperature": 38.5,
        "humidity": 62.0,
        "gas": 0.35,
        "smoke": 0.12
    }

The Decision Engine should not read the Pico directly.

---

# 8. Hazard Categories

The initial Decision Engine should support the following logical hazard categories.

## 8.1 Blocked Path

Possible evidence:

- rock detected
- debris detected
- large object detected
- multiple obstructions detected

Example:

    rock detected
          ↓
    possible blocked path

However, a rock in the image does NOT automatically mean the path is blocked.

The system should consider the object's position and size where possible.

---

# 9. Fire Hazard

Possible evidence:

Vision:

    fire detected
    smoke detected

Sensors:

    high temperature
    high smoke value

Multimodal evidence:

    fire + smoke
    fire + high temperature
    smoke + high temperature

The engine should increase confidence when independent sources support the same hazard.

---

# 10. Gas Hazard

Possible evidence:

    high gas sensor value

The engine should not claim a specific gas type unless the actual sensor identifies that gas.

For example:

Correct:

    "Gas hazard indicator elevated"

Incorrect:

    "Methane leak detected"

unless a methane sensor is actually being used.

---

# 11. Smoke Hazard

Possible evidence:

Vision:

    smoke detected

Sensor:

    smoke value elevated

Both sources can contribute to the final assessment.

---

# 12. Person Detection

Person detection is not automatically a hazard.

A person may simply be present in the environment.

Person detection may become relevant when combined with another hazard.

Example:

    person + fire
    person + blocked path
    person + gas hazard

The Decision Engine should distinguish:

    detected object

from:

    actual hazard

---

# 13. Severity Levels

The engine should produce:

    LOW
    MEDIUM
    HIGH
    CRITICAL

These levels are system classifications and must be clearly documented.

They should not be treated as medical, legal, or safety certification.

---

# 14. Severity Concept

Severity should depend on multiple factors.

Conceptually:

    Severity =
        hazard evidence
        +
        sensor evidence
        +
        vision confidence
        +
        multimodal agreement
        +
        contextual factors

Do NOT make severity depend on a single detection confidence value.

For example:

    rock confidence = 0.95

does not automatically mean:

    severity = CRITICAL

A highly confident rock detection could still represent a LOW hazard if the rock is small and outside the rover's path.

---

# 15. Multimodal Fusion

The central purpose of Phase 2 is multimodal fusion.

Example:

### Case 1

Vision:

    rock = 0.90

Sensors:

    gas = 0.10
    smoke = 0.02
    temperature = 35

Possible result:

    hazard = blocked_path
    severity = LOW/MEDIUM

depending on spatial/context information.

---

### Case 2

Vision:

    fire = 0.87
    smoke = 0.91

Sensors:

    temperature = 68
    smoke = 0.82

The evidence agrees across independent sources.

Possible result:

    hazard = fire
    severity = HIGH/CRITICAL

The exact thresholds must be configurable.

---

### Case 3

Vision:

    smoke = 0.82

Sensors:

    smoke = 0.05
    temperature = 32

The sources disagree.

The engine should NOT blindly declare a critical fire.

Instead, it should reduce confidence and report the disagreement.

Example:

    hazard = smoke
    severity = MEDIUM
    confidence = reduced
    reason = "Vision detected smoke but sensor evidence is low"

---

# 16. Confidence vs Severity

These are two different concepts.

### Confidence

How strongly the system believes the hazard classification is supported.

Example:

    confidence = 0.91

### Severity

How serious the detected hazard is.

Example:

    severity = HIGH

Do not use these terms interchangeably.

Example:

    confidence = 0.95
    severity = LOW

is completely valid.

A small rock can be detected with very high confidence but still be a low-severity obstruction.

---

# 17. Evidence

Every decision should contain evidence.

Example:

    {
        "source": "vision",
        "type": "rock",
        "confidence": 0.91
    }

and:

    {
        "source": "sensor",
        "type": "gas",
        "value": 0.82
    }

The final result should preserve enough information to explain why the engine produced the decision.

---

# 18. Explanation

Every hazard assessment should include human-readable reasons.

Example:

    reasons:
      - "Rock detected with 0.91 confidence"
      - "Object is located inside estimated path region"

Another example:

    reasons:
      - "Fire detected visually"
      - "Smoke detected visually"
      - "Temperature is elevated"
      - "Smoke sensor value is elevated"

This will later be displayed on the dashboard.

---

# 19. Hazard Assessment Schema

The Decision Engine should return a standardized structure.

Example:

    {
        "timestamp": "2026-09-27T14:00:05+05:30",
        "hazard_type": "fire",
        "severity": "HIGH",
        "confidence": 0.93,
        "reasons": [
            "Fire detected visually",
            "Smoke detected visually",
            "Temperature elevated"
        ],
        "vision_evidence": [],
        "sensor_evidence": []
    }

The exact implementation may use a Python dataclass or Pydantic model.

---

# 20. No-Hazard Result

The engine must also support a safe/no-hazard result.

Example:

    {
        "hazard_type": "none",
        "severity": "LOW",
        "confidence": 0.88,
        "reasons": [
            "No significant hazard evidence detected"
        ]
    }

The system should not force a hazard classification when evidence is insufficient.

---

# 21. Rule Engine

Rules should be separated from the main engine.

Example conceptual rule:

    IF
        fire_detected
        AND smoke_detected
        AND temperature_high

    THEN
        fire hazard evidence increases

Another:

    IF
        rock_detected
        AND rock_inside_path_region

    THEN
        blocked_path evidence increases

Rules should be stored in `rules.py`.

Avoid placing every rule directly inside `engine.py`.

---

# 22. Configurable Thresholds

Thresholds should be configurable rather than scattered throughout the code.

Example:

    GAS_WARNING = 0.50
    GAS_HIGH = 0.75

    SMOKE_WARNING = 0.40
    SMOKE_HIGH = 0.70

    TEMPERATURE_WARNING = 50
    TEMPERATURE_HIGH = 65

These are initial development values only.

They are NOT certified mine-safety thresholds.

Actual thresholds must later be determined using the selected sensors, calibration data, environmental conditions, and appropriate safety requirements.

---

# 23. Spatial Reasoning for Path Blocking

A major requirement is distinguishing:

    "rock detected"

from:

    "path blocked"

The engine should eventually use the object's bounding box to estimate whether the object lies inside the rover's travel corridor.

Conceptually:

    Camera Frame

    ┌──────────────────────────┐
    │                          │
    │       ROCK               │
    │      █████               │
    │       ███                │
    │                          │
    │      PATH REGION         │
    │       │      │           │
    │       │      │           │
    │       │      │           │
    └──────────────────────────┘

If the detected object overlaps the estimated path region:

    blocked_path evidence ↑

This can be improved later using depth, stereo vision, LiDAR, or rover geometry.

For Phase 2, keep the implementation simple and clearly document its limitations.

---

# 24. Temporal Reasoning

The engine should eventually avoid making major decisions from a single noisy reading.

Example:

    Frame 1 → smoke detected
    Frame 2 → smoke detected
    Frame 3 → smoke detected

This is stronger evidence than:

    Frame 1 → smoke detected
    Frame 2 → nothing
    Frame 3 → nothing

Similarly, repeated sensor readings can increase confidence.

For the initial implementation, temporal smoothing may be simple.

Do not build a complex tracking system in Phase 2 unless necessary.

---

# 25. Conflicting Evidence

The engine must handle conflicting evidence.

Example:

    Vision:
        smoke = 0.90

    Sensor:
        smoke = 0.05

The result should indicate uncertainty.

Example:

    confidence = reduced

    reason:
        "Vision and sensor evidence disagree"

Do not hide conflicting evidence.

This is important for a real-world safety-oriented system.

---

# 26. Sensor Failure

A missing sensor must not cause the entire Decision Engine to fail.

Example:

    temperature = unavailable
    gas = 0.75
    smoke = 0.70

The engine should still process available information.

The output should indicate that some sensor information was unavailable if relevant.

---

# 27. Vision Failure

Similarly, if YOLO is unavailable:

    vision = unavailable

the engine should still be capable of processing sensor data.

Example:

    gas = 0.90
    smoke = 0.80

The engine can still report:

    gas/smoke hazard

while clearly indicating that vision evidence was unavailable.

---

# 28. Decision Engine API

The core engine should expose a simple interface.

Conceptually:

    result = decision_engine.evaluate(
        vision_data,
        sensor_data
    )

It should return:

    HazardAssessment

The engine should not:

- access HTTP
- access SQLite
- access React
- access the camera directly
- access the Pico directly

Keep the core engine independent.

---

# 29. Testing

Create tests for:

### Rules

Test individual hazard rules.

Examples:

- fire detection
- smoke detection
- gas hazard
- blocked path
- person + hazard

### Fusion

Test:

- vision only
- sensor only
- both agree
- sources disagree
- missing vision
- missing sensors

### Confidence

Test:

- high-confidence detection
- low-confidence detection
- multiple supporting signals
- conflicting signals

### Engine

Test complete end-to-end decisions.

---

# 30. Example Test Cases

## Test 1 — No Hazard

Input:

    Vision:
        []

    Sensors:
        temperature = 32
        gas = 0.10
        smoke = 0.02

Expected:

    hazard_type = none

---

## Test 2 — Rock

Input:

    Vision:
        rock = 0.92

Expected:

    hazard_type = blocked_path or obstruction
    depending on spatial/path information

Do NOT automatically classify it as CRITICAL.

---

## Test 3 — Fire

Input:

    Vision:
        fire = 0.90
        smoke = 0.88

    Sensors:
        temperature = 70
        smoke = 0.80

Expected:

    hazard_type = fire
    severity = HIGH or CRITICAL

The exact severity must depend on configured rules.

---

## Test 4 — Gas

Input:

    Vision:
        []

    Sensors:
        gas = 0.90

Expected:

    gas-related hazard

---

## Test 5 — Conflicting Evidence

Input:

    Vision:
        smoke = 0.90

    Sensors:
        smoke = 0.05
        temperature = 30

Expected:

    smoke-related assessment
    with reduced confidence
    and an explanation of the disagreement

---

# 31. Safety Principle

The Decision Engine is a prototype decision-support component.

It must NOT claim that its classifications are certified mine-safety decisions.

It must not automatically trigger:

- emergency shutdown
- evacuation
- motor control
- braking
- physical intervention

in Phase 2.

The system should initially provide information to the operator/dashboard.

---

# 32. Performance Requirements

The engine should be lightweight.

Target:

    Input
      ↓
    Fusion
      ↓
    Rules
      ↓
    Assessment

should execute quickly enough for near-real-time monitoring.

Avoid unnecessary machine-learning models inside the Decision Engine.

The YOLO model already provides the visual ML component.

The Decision Engine should primarily use:

- rules
- thresholds
- weighted evidence
- confidence
- simple temporal logic

---

# 33. Extensibility

The architecture must allow future additions such as:

- LiDAR
- depth camera
- vibration sensors
- methane sensor
- CO sensor
- H2S sensor
- GPS
- IMU
- thermal camera

without rewriting the entire Decision Engine.

New evidence sources should be converted into standardized evidence before fusion.

---

# 34. Acceptance Criteria

Phase 2 is complete when:

[ ] Decision Engine exists.

[ ] Vision input schema exists.

[ ] Sensor input is compatible with Phase 1.

[ ] Hazard schema exists.

[ ] Rule engine exists.

[ ] Multimodal fusion exists.

[ ] Confidence calculation exists.

[ ] Severity calculation exists.

[ ] Human-readable reasons are generated.

[ ] No-hazard result is supported.

[ ] Missing sensor data is handled.

[ ] Missing vision data is handled.

[ ] Conflicting evidence is handled.

[ ] Basic path-blocking logic exists or has a clearly defined interface.

[ ] Unit tests pass.

[ ] The engine can be executed independently without FastAPI, SQLite, or React.

---

# 35. Final Phase 2 Architecture

    ┌──────────────────────┐
    │     YOLO Vision      │
    │                      │
    │ rock                 │
    │ debris               │
    │ fire                 │
    │ smoke                │
    │ person               │
    └──────────┬───────────┘
               │
               │
               ↓
        ┌───────────────┐
        │               │
        │   Decision    │
        │    Engine     │
        │               │
        │ ┌───────────┐ │
        │ │  Fusion   │ │
        │ ├───────────┤ │
        │ │   Rules   │ │
        │ ├───────────┤ │
        │ │ Confidence│ │
        │ ├───────────┤ │
        │ │ Severity  │ │
        │ └───────────┘ │
        └───────┬───────┘
                ↑
                │
        ┌───────┴────────┐
        │ Sensor Service │
        │                │
        │ temperature    │
        │ humidity       │
        │ gas            │
        │ smoke          │
        └────────────────┘

                ↓

        Hazard Assessment

        ┌─────────────────────────┐
        │ Hazard Type              │
        │ Severity                 │
        │ Confidence              │
        │ Reasons                 │
        │ Vision Evidence         │
        │ Sensor Evidence         │
        └─────────────────────────┘

                ↓

        Future Database / API
```

---

# 36. Development Rule
Implement Phase 2 independently first.

Use simulated vision detections and the Phase 1 sensor simulator for testing.

Do NOT wait for:

- Raspberry Pi
- Pico
- physical sensors
- database
- dashboard
The complete Decision Engine should be testable on a normal laptop.

Once Phase 2 is stable, connect it to the actual YOLO inference module and Phase 1 Sensor Service.
