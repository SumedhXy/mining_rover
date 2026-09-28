# Phase 1 — Sensor Data Acquisition & Normalization

## 1. Purpose

The Sensor Data Service is responsible for receiving environmental sensor telemetry, validating values against safety ranges, normalizing data into a hardware-agnostic model, and distributing it to downstream consumers (Decision Engine, Local SQLite Database, and FastAPI Backend).

The entire sensor pipeline runs **100% offline-first**. No external network connectivity or cloud APIs are required for acquiring, validating, or processing sensor readings.

---

## 2. Sensor Hardware

The ESP32 Environmental Sensor Node #1 interfaces with the following environmental sensors:

- **DHT11**: Temperature (°C) and Relative Humidity (%)
- **BMP180**: Atmospheric pressure (hPa)
- **MQ-4**: Methane / hydrocarbon combustible gas detection (raw ADC / normalized index)
- **MQ-135**: Air quality / toxic gas / smoke detection (raw ADC / normalized index)
- **OLED Display** *(ESP32 local only)*: Direct visual readout on the rover chassis
- **SD Card** *(ESP32 local only)*: Physical fallback blackbox storage

> **Calibration Notice:** MQ-4 and MQ-135 readings are treated as raw ADC values or normalized index values (`[0.0, 1.0]`). They are deliberately not labelled as calibrated ppm until hardware calibration curves are executed against known gas concentrations.

---

## 3. Architecture

The architecture ensures complete hardware independence. The Decision Engine, Database, and Backend consume a unified `StandardSensorReading` regardless of data origin.

### Simulation Path
```text
┌─────────────────┐
│ SimulatorSource │
└────────┬────────┘
         │ StandardSensorReading
         ▼
┌─────────────────┐
│  SensorService  │
└────────┬────────┘
         │ StandardSensorReading
         ├───► Decision Engine
         ├───► SQLite Database
         └───► FastAPI Backend
```

### Real Hardware Path
```text
┌─────────────────────────┐
│ ESP32 Sensor Controller │
└────────────┬────────────┘
             │ Newline-delimited JSON over USB Serial / UART
             ▼
┌─────────────────────────┐
│      ESP32Receiver      │ (esp32_receiver.py)
└────────────┬────────────┘
             │ Raw line / bytes
             ▼
┌─────────────────────────┐
│      PacketParser       │ (packet_parser.py)
└────────────┬────────────┘
             │ StandardSensorReading
             ▼
┌─────────────────────────┐
│      SensorService      │ (sensor_service.py)
└────────────┬────────────┘
             │ StandardSensorReading
             ├───► Decision Engine
             ├───► SQLite Database
             └───► FastAPI Backend
```

---

## 4. StandardSensorReading Data Model

Implemented in `sensors/sensor_schema.py`.

```python
@dataclass
class StandardSensorReading:
    timestamp: str              # ISO 8601 UTC with timezone (e.g. 2026-09-28T11:30:20Z)
    temperature_c: float        # Valid range: -40.0 to 100.0 °C
    humidity_percent: float     # Valid range: 0.0 to 100.0 %
    pressure_hpa: float         # Valid range: > 0.0 hPa (nominal ~1013.25)
    methane: float              # MQ-4 normalized reading / index (>= 0.0)
    air_quality: float          # MQ-135 normalized reading / index (>= 0.0)
    source: Optional[str]       # "esp32", "simulator", etc.
    device_id: Optional[str]    # "sensor_01"
    sequence_number: Optional[int] # Incrementing packet counter
```

Backward-compatibility property aliases:
- `reading.temperature` ↔ `reading.temperature_c`
- `reading.humidity` ↔ `reading.humidity_percent`
- `reading.pressure` ↔ `reading.pressure_hpa`
- `reading.gas` / `reading.mq4` / `reading.methane_raw` ↔ `reading.methane`
- `reading.smoke` / `reading.mq135` / `reading.air_quality_raw` ↔ `reading.air_quality`

---

## 5. ESP32 Packet Format

ESP32 transmits newline-delimited JSON packets over USB serial or UART at 115200 baud.

### Example Packet:
```json
{
  "device_id": "sensor_01",
  "timestamp": "2026-09-28T11:30:20Z",
  "temperature_c": 34.5,
  "humidity_percent": 67.0,
  "pressure_hpa": 998.2,
  "mq4": 0.42,
  "mq135": 0.31
}
```

Stream structure:
```text
{"device_id":"sensor_01","timestamp":"2026-09-28T11:30:20Z","temperature_c":34.5,"humidity_percent":67.0,"pressure_hpa":998.2,"mq4":0.42,"mq135":0.31}\n
{"device_id":"sensor_01","timestamp":"2026-09-28T11:30:21Z","temperature_c":34.6,"humidity_percent":66.8,"pressure_hpa":998.1,"mq4":0.41,"mq135":0.30}\n
```

---

## 6. Simulator

Implemented in `sensors/simulator.py` and `sensors/sources/simulator_source.py`.

Generates realistic environmental waveforms and hazards without hardware:
- **`normal`**: Realistic drift around mining ambient levels (35 °C, 60% RH, 1013 hPa, low gas/smoke)
- **`high_temperature`**: Thermal buildup (> 65 °C)
- **`gas_hazard`**: Elevated methane spikes (> 0.8)
- **`smoke_hazard`**: Elevated particulate/smoke spikes (> 0.8)

Run simulator standalone:
```bash
python sensors/simulator.py
```

---

## 7. ESP32 Receiver

Implemented in `sensors/esp32_receiver.py`.

- Encapsulates `serial.Serial` communications.
- Provides `connect()`, `disconnect()`, and `read()`.
- Implements the `SensorSource` protocol.
- Tolerates absent hardware, reconnects automatically, and logs errors fail-soft without crashing the application.
- Exposes alias `ESP32SerialSource`.

---

## 8. Configuration

Configurable via environment variables or explicit constructor parameters:

| Variable | Default | Description |
|---|---|---|
| `ROVER_SENSOR_PORT` | `None` / auto | Serial port path (e.g. `COM3` on Windows, `/dev/ttyUSB0` on Linux) |
| `ROVER_SENSOR_BAUDRATE` | `115200` | Baud rate for serial link |
| `ROVER_SENSOR_TIMEOUT` | `1.0` | Read timeout in seconds |

Example in code:
```python
from sensors import SensorService, ESP32Receiver

receiver = ESP32Receiver(port="/dev/ttyUSB0", baudrate=115200)
service = SensorService(source=receiver)
service.start()
reading = service.read()
```

---

## 9. Error Handling & Validation Rules

- **Malformed JSON**: Discarded, logged as warning, receiver continues listening.
- **Missing Required Fields**: Discarded, logged, rover never crashes.
- **Type Safety**: Non-numeric fields trigger validation rejection.
- **Range Constraints**:
  - `temperature_c`: must be between -40.0 °C and 100.0 °C
  - `humidity_percent`: must be between 0.0 % and 100.0 %
  - `pressure_hpa`: must be strictly positive (> 0.0 hPa)
  - `methane` / `air_quality`: must be non-negative (>= 0.0)
- **Timestamp Fallback**: If ESP32 timestamp is omitted or corrupted, Raspberry Pi automatically stamps current UTC ISO 8601 time.
- **Stream Resilience**: If packet #1 is invalid, packet #1 is rejected and packet #2 is immediately parsed without crashing.

---

## 10. Offline Behavior

The Sensor Data Service has **zero external cloud or network dependencies**. All parsing, validation, and normalization execute locally in memory on the Raspberry Pi.

---

## 11. Testing

Execute the sensor test suite:
```bash
python -m pytest tests/sensors/
```

All 14 minimum integration tests pass:
1. Valid ESP32 packet
2. Missing field rejection
3. Invalid JSON resilience
4. Invalid numeric value rejection
5. Out-of-range humidity rejection
6. Negative pressure rejection
7. Negative gas raw value rejection
8. Timestamp parsing and fallback handling
9. Simulator output verification
10. ESP32 serial source stream output
11. Source interchangeability between Simulator and ESP32
12. Serial disconnect exception handling
13. Multiple packet stream processing
14. Malformed packet recovery

---

## 12. Future Hardware Connection

When physical ESP32 hardware is plugged in via USB:

1. Identify the port:
   - Linux / Raspberry Pi: `/dev/ttyUSB0` or `/dev/ttyACM0`
   - Windows: `COM3`, `COM4`, etc.
2. Set environment variable:
   ```bash
   export ROVER_SENSOR_PORT="/dev/ttyUSB0"
   export ROVER_SENSOR_BAUDRATE="115200"
   ```
3. Initialize `SensorService(source=ESP32SerialSource())`.
4. Downstream Decision Engine, Database, and Backend require zero changes.
