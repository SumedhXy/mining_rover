# Phase 2 — Mining Rover Decision Engine

## 1. Objective & Scope

The Decision Engine is the intelligence layer for the Mining Rover. It analyzes incoming environmental telemetry from Phase 1 alongside visual object detections from the YOLO Vision module to evaluate hazards, calculate severity, generate internal confidence scores, and formulate human-explainable reasons.

> **CRITICAL ARCHITECTURAL BOUNDARY:**
> The Decision Engine evaluates hazards only. It **does NOT** control motors, wheels, PWM actuators, steering, or navigation logic. Hazard assessments are strictly informational and decoupled from rover movement.

---

## 2. Architecture

```text
       ESP32 Sensor Node
               │
               ▼
       Sensor Data Service (Phase 1)
               │
       ┌───────┴───────┐
       ▼               ▼
  Sensor Data     YOLO Vision
       │               │
       └───────┬───────┘
               ▼
       DECISION ENGINE (Phase 2)
               │
               ▼ HazardAssessment
       ┌───────┴───────┐
       ▼               ▼
     SQLite         FastAPI
       │               │
       └───────┬───────┘
               ▼
           Dashboard
```

The entire decision pipeline operates **100% offline-first** on the Raspberry Pi 4 without cloud APIs or network connectivity.

---

## 3. Inputs

### 3.1 Sensor Input (Phase 1 Standardized Schema)
Accepts either `StandardSensorReading` or dictionary input:
- `device_id`: Originating sensor controller ID
- `timestamp`: ISO-8601 UTC timestamp
- `temperature_c` (or `temperature`): Celsius reading
- `humidity_percent` (or `humidity`): Relative humidity %
- `pressure_hpa` (or `pressure`): Barometric pressure in hPa
- `mq4` (or `methane`, `gas`): Normalized MQ-4 methane index (`[0.0, 1.0]`)
- `mq135` (or `air_quality`, `smoke`): Normalized MQ-135 index (`[0.0, 1.0]`)

*Important:* MQ-4 and MQ-135 readings are treated as sensor levels/indices. They are never falsely represented as ppm.

### 3.2 Vision Input (YOLO Detections)
Accepts single or multi-detection lists:
```json
{
  "detections": [
    {
      "class_name": "fire",
      "confidence": 0.85,
      "bbox": [100, 120, 300, 400],
      "source": "yolo"
    },
    {
      "class_name": "smoke",
      "confidence": 0.72,
      "bbox": [250, 100, 500, 350],
      "source": "yolo"
    }
  ]
}
```

---

## 4. Hazard Categories & Decision Rules

1. **`fire`**: Multi-modal fusion combining visual fire/smoke detections with elevated ambient temperatures and MQ-135 combustion indications.
2. **`smoke`**: Visual smoke detection combined with elevated MQ-135 air-quality sensor readings.
3. **`gas`**: Combustible gas / methane detection from elevated MQ-4 indices (warning >= 0.40, high >= 0.60, critical >= 0.80).
4. **`high_temperature`**: Thermal hazard when ambient temperature exceeds configured thresholds (warning >= 45 °C, high >= 55 °C, critical >= 65 °C).
5. **`pressure_anomaly`**: Atmospheric pressure outside normal mine operational range (850 to 1100 hPa).
6. **`blocked_path`**: Obstacles (rock, debris) detected visually in rover path.
7. **`none`**: Default state when no hazard thresholds are exceeded (`severity="NONE"`, confidence <= 0.20).

---

## 5. External Configuration

Thresholds are externalized in [`config/decision_thresholds.yaml`](file:///c:/Users/sumed/Mining_Rover_software/config/decision_thresholds.yaml):

```yaml
temperature:
  warning_c: 45.0
  high_c: 55.0
  critical_c: 65.0

mq4:
  warning: 0.40
  high: 0.60
  critical: 0.80

mq135:
  warning: 0.40
  high: 0.60
  critical: 0.80

pressure:
  minimum_hpa: 850.0
  maximum_hpa: 1100.0

vision:
  minimum_confidence: 0.50

persistence:
  required_readings: 3

data_freshness:
  sensor_max_age_seconds: 5.0
  vision_max_age_seconds: 2.0
```

Programmatic overrides and fallback defaults are managed via `decision_engine/thresholds.py`.

---

## 6. Severity & Confidence Model

### Severity Levels
- `CRITICAL`: Score >= 0.85 (Multi-signal high-severity confirmation or extreme sensor violations)
- `HIGH`: Score >= 0.65 (Strong evidence from vision or sensor)
- `MEDIUM`: Score >= 0.40 (Single clear signal or moderate threshold breach)
- `LOW`: Score >= 0.15 (Weak indicator)
- `NONE`: No thresholds exceeded

### Confidence Score
Internal score bounded strictly between `0.0` and `1.0`:
- Scaled by detection strength, sensor violation magnitude, and multi-modal agreement.
- Discounted when vision and sensor evidence conflict (e.g. camera sees smoke but gas sensor is near zero).
- Discounted if input data is stale.

---

## 7. Output Model: `HazardAssessment`

Implemented in `decision_engine/models.py`:

```json
{
  "timestamp": "2026-09-28T11:35:10Z",
  "decision_id": "a1b2c3d4",
  "hazard_type": "fire",
  "severity": "HIGH",
  "confidence": 0.87,
  "reasons": [
    "Fire detected visually by YOLO with confidence 0.85",
    "High temperature detected (58.2 °C >= 55.0 °C)",
    "MQ-135 air-quality / combustion index elevated to 0.71"
  ],
  "sensor_evidence": [
    {"source": "sensor", "type": "temperature", "confidence": 0.58, "value": 58.2},
    {"source": "sensor", "type": "smoke", "confidence": 0.71, "value": 0.71}
  ],
  "vision_evidence": [
    {"source": "vision", "type": "fire", "confidence": 0.85, "value": 0.85}
  ],
  "source": "sensor_vision_fusion",
  "all_hazards": [
    {"hazard_type": "fire", "severity": "HIGH", "confidence": 0.87, "reasons": [...]},
    {"hazard_type": "high_temperature", "severity": "HIGH", "confidence": 0.80, "reasons": [...]}
  ]
}
```

---

## 8. Multi-Hazard, Staleness & Temporal Stability

- **Multiple Hazards**: All detected hazards are retained in `all_hazards`, and the most severe is designated as the primary `hazard_type`.
- **Temporal Persistence (Debounce)**: Configurable `persistence.required_readings` (default 3) prevents single-cycle sensor glitches from causing premature critical alerts.
- **Staleness Tracking**: Inputs older than configured freshness limits (`5s` for sensors, `2s` for vision) are flagged in `reasons` and penalized in confidence.
- **Missing Inputs**: If only sensors are available, evaluates sensor hazards. If only vision is available, evaluates vision hazards. If both are missing, reports `none` with `"Insufficient input data"` without crashing.

---

## 9. Testing & Verification

Run the complete test suite:
```bash
python -m pytest tests/decision_engine/
```

Covers all 20 required scenarios across 37 comprehensive unit tests:
- `test_engine.py`: Core evaluation, fusion, multiple hazards, pressure anomaly, low YOLO confidence rejection.
- `test_rules.py`: Deterministic thresholds and hazard category detection rules.
- `test_fusion.py`: Normalization, evidence extraction, and signal fusion.
- `test_confidence.py`: Math clamping and confidence adjustments.
- `test_missing_data.py`: Handling missing, invalid, and stale inputs.
- `test_temporal_stability.py`: Persistence streaks, reset logic, confidence bounds, and safety separation.
