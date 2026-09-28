import io
import pytest

from sensors.esp32_receiver import ESP32Receiver, ESP32SerialSource
from sensors.packet_parser import PacketParseError, PacketParser
from sensors.sensor_schema import StandardSensorReading
from sensors.sensor_service import SensorService
from sensors.sources.simulator_source import SimulatorSource


# 1. Valid ESP32 packet
def test_valid_esp32_packet():
    raw_packet = (
        '{"device_id": "sensor_01", "timestamp": "2026-09-28T11:30:20Z", '
        '"temperature_c": 34.5, "humidity_percent": 67.0, "pressure_hpa": 998.2, '
        '"mq4": 0.42, "mq135": 0.31}'
    )
    reading = PacketParser.parse(raw_packet)

    assert reading is not None
    assert isinstance(reading, StandardSensorReading)
    assert reading.device_id == "sensor_01"
    assert reading.temperature_c == 34.5
    assert reading.humidity_percent == 67.0
    assert reading.pressure_hpa == 998.2
    assert reading.methane == 0.42
    assert reading.air_quality == 0.31
    assert reading.source == "esp32"

    # Backward-compatible property aliases
    assert reading.temperature == 34.5
    assert reading.humidity == 67.0
    assert reading.pressure == 998.2
    assert reading.gas == 0.42
    assert reading.smoke == 0.31


# 2. Missing field
def test_missing_required_field():
    # Missing humidity
    incomplete_packet = '{"temperature_c": 34.5, "mq4": 0.42, "mq135": 0.31}'
    assert PacketParser.parse(incomplete_packet) is None

    with pytest.raises(PacketParseError, match="Missing required field"):
        PacketParser.parse(incomplete_packet, strict=True)


# 3. Invalid JSON
def test_invalid_json():
    malformed_json = '{"device_id": "sensor_01", "temperature_c": 34.5,'
    assert PacketParser.parse(malformed_json) is None

    with pytest.raises(PacketParseError, match="Malformed JSON"):
        PacketParser.parse(malformed_json, strict=True)


# 4. Invalid numeric value
def test_invalid_numeric_value():
    invalid_num = (
        '{"temperature_c": "HOT", "humidity_percent": 60.0, "pressure_hpa": 1013.25, '
        '"mq4": 0.1, "mq135": 0.1}'
    )
    assert PacketParser.parse(invalid_num) is None

    with pytest.raises(PacketParseError, match="must be numeric"):
        PacketParser.parse(invalid_num, strict=True)


# 5. Out-of-range humidity
def test_out_of_range_humidity():
    hum_too_high = '{"temperature_c": 25.0, "humidity_percent": 110.0, "mq4": 0.1, "mq135": 0.1}'
    assert PacketParser.parse(hum_too_high) is None

    hum_negative = '{"temperature_c": 25.0, "humidity_percent": -5.0, "mq4": 0.1, "mq135": 0.1}'
    assert PacketParser.parse(hum_negative) is None


# 6. Negative pressure
def test_negative_pressure():
    neg_pressure = (
        '{"temperature_c": 25.0, "humidity_percent": 50.0, "pressure_hpa": -15.0, '
        '"mq4": 0.1, "mq135": 0.1}'
    )
    assert PacketParser.parse(neg_pressure) is None

    with pytest.raises(PacketParseError, match="must be positive"):
        PacketParser.parse(neg_pressure, strict=True)


# 7. Negative gas raw value
def test_negative_gas_raw_value():
    neg_gas = '{"temperature_c": 25.0, "humidity_percent": 50.0, "mq4": -0.5, "mq135": 0.1}'
    assert PacketParser.parse(neg_gas) is None

    neg_air = '{"temperature_c": 25.0, "humidity_percent": 50.0, "mq4": 0.1, "mq135": -0.2}'
    assert PacketParser.parse(neg_air) is None


# 8. Timestamp handling
def test_timestamp_handling():
    # 8a: ISO 8601 with Z
    packet_z = '{"timestamp": "2026-09-28T11:30:20Z", "temperature_c": 25.0, "humidity_percent": 50.0, "mq4": 0.1, "mq135": 0.1}'
    reading_z = PacketParser.parse(packet_z)
    assert reading_z is not None
    assert "2026-09-28T11:30:20" in reading_z.timestamp

    # 8b: Missing timestamp auto-assigns valid ISO timestamp
    packet_no_ts = '{"temperature_c": 25.0, "humidity_percent": 50.0, "mq4": 0.1, "mq135": 0.1}'
    reading_no_ts = PacketParser.parse(packet_no_ts)
    assert reading_no_ts is not None
    assert reading_no_ts.timestamp is not None
    assert "T" in reading_no_ts.timestamp

    # 8c: Corrupted timestamp string falls back to auto-assigned receive timestamp without crashing
    packet_bad_ts = '{"timestamp": "INVALID_DATE_XYZ", "temperature_c": 25.0, "humidity_percent": 50.0, "mq4": 0.1, "mq135": 0.1}'
    reading_bad_ts = PacketParser.parse(packet_bad_ts)
    assert reading_bad_ts is not None
    assert reading_bad_ts.timestamp != "INVALID_DATE_XYZ"


# 9. Simulator output
def test_simulator_output():
    sim = SimulatorSource()
    for _ in range(5):
        reading = sim.read()
        assert isinstance(reading, StandardSensorReading)
        assert -40.0 <= reading.temperature_c <= 100.0
        assert 0.0 <= reading.humidity_percent <= 100.0
        assert reading.pressure_hpa > 0.0
        assert 0.0 <= reading.methane <= 1.0
        assert 0.0 <= reading.air_quality <= 1.0
        assert reading.source == "simulator"


# 10. ESP32 source output
def test_esp32_source_output():
    packet_line = b'{"device_id": "sensor_01", "temperature_c": 29.2, "humidity_percent": 58.0, "pressure_hpa": 1010.5, "mq4": 0.15, "mq135": 0.08}\n'
    stream = io.BytesIO(packet_line)

    receiver = ESP32Receiver(serial_instance=stream)
    reading = receiver.read()

    assert reading is not None
    assert reading.temperature_c == 29.2
    assert reading.humidity_percent == 58.0
    assert reading.pressure_hpa == 1010.5
    assert reading.methane == 0.15
    assert reading.air_quality == 0.08
    assert receiver.packets_received == 1


# 11. Source interchangeability
def test_source_interchangeability():
    # Downstream service with SimulatorSource
    service_sim = SensorService(source=SimulatorSource())
    reading_sim = service_sim.read()

    # Downstream service with ESP32SerialSource
    packet_bytes = b'{"temperature_c": 31.0, "humidity_percent": 55.0, "pressure_hpa": 1012.0, "mq4": 0.20, "mq135": 0.10}\n'
    stream = io.BytesIO(packet_bytes)
    service_esp32 = SensorService(source=ESP32SerialSource(serial_instance=stream))
    reading_esp32 = service_esp32.read()

    # Both produce identical StandardSensorReading contract
    assert isinstance(reading_sim, StandardSensorReading)
    assert isinstance(reading_esp32, StandardSensorReading)
    assert hasattr(reading_sim, "temperature_c") and hasattr(reading_esp32, "temperature_c")
    assert hasattr(reading_sim, "methane") and hasattr(reading_esp32, "methane")
    assert hasattr(reading_sim, "air_quality") and hasattr(reading_esp32, "air_quality")


# 12. Serial disconnect handling
def test_serial_disconnect_handling():
    class DisconnectedSerialMock:
        def readline(self):
            raise OSError("Serial port device disconnected")

    receiver = ESP32Receiver(serial_instance=DisconnectedSerialMock())
    reading = receiver.read()

    # Must return None and not crash
    assert reading is None
    assert receiver.packets_failed == 1


# 13. Multiple packets
def test_multiple_packets_stream():
    stream_data = (
        '{"temperature_c": 28.0, "humidity_percent": 50.0, "mq4": 0.1, "mq135": 0.1}\n'
        '{"temperature_c": 28.5, "humidity_percent": 51.0, "mq4": 0.12, "mq135": 0.11}\n'
        '{"temperature_c": 29.0, "humidity_percent": 52.0, "mq4": 0.14, "mq135": 0.12}\n'
    )
    readings = PacketParser.parse_stream(stream_data)

    assert len(readings) == 3
    assert readings[0].temperature_c == 28.0
    assert readings[1].temperature_c == 28.5
    assert readings[2].temperature_c == 29.0


# 14. Malformed packet followed by valid packet
def test_malformed_packet_followed_by_valid_packet():
    stream_data = (
        '{"broken_incomplete_json": 12\n'
        '{"temperature_c": 32.5, "humidity_percent": 65.0, "mq4": 0.25, "mq135": 0.15}\n'
    )
    readings = PacketParser.parse_stream(stream_data)

    # First packet dropped, second packet successfully parsed
    assert len(readings) == 1
    assert readings[0].temperature_c == 32.5
    assert readings[0].humidity_percent == 65.0
    assert readings[0].methane == 0.25
