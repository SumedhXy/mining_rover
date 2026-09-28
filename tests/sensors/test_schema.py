import pytest

from sensors.sensor_schema import StandardSensorReading


VALID_READING = {
    "timestamp": "2026-09-27T13:42:00+05:30",
    "temperature": 38.5,
    "humidity": 62.0,
    "gas": 0.35,
    "smoke": 0.12,
}


def test_valid_sensor_reading_is_accepted():
    reading = StandardSensorReading(**VALID_READING)

    assert reading.temperature == 38.5
    assert reading.humidity == 62.0
    assert reading.gas == 0.35
    assert reading.smoke == 0.12
    assert reading.timestamp == "2026-09-27T13:42:00+05:30"


def test_invalid_values_are_rejected():
    with pytest.raises(ValueError):
        StandardSensorReading(timestamp="2026-09-27T13:42:00+05:30", temperature=150.0, humidity=50.0, gas=0.1, smoke=0.1)

    with pytest.raises(ValueError):
        StandardSensorReading(timestamp="2026-09-27T13:42:00+05:30", temperature=20.0, humidity=120.0, gas=0.1, smoke=0.1)

    with pytest.raises(ValueError):
        StandardSensorReading(timestamp="2026-09-27T13:42:00+05:30", temperature=20.0, humidity=50.0, gas=-0.1, smoke=0.1)

    with pytest.raises(ValueError):
        StandardSensorReading(timestamp="2026-09-27T13:42:00+05:30", temperature=20.0, humidity=50.0, gas=0.1, smoke=1.5)
