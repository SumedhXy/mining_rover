import logging

from sensors.sensor_service import SensorService


class SampleSource:
    def __init__(self, reading):
        self._reading = reading

    def read(self):
        return self._reading


def test_sensor_service_passes_valid_reading_through():
    reading = {
        "timestamp": "2026-09-27T13:42:00+05:30",
        "temperature": 35.2,
        "humidity": 61.4,
        "gas": 0.12,
        "smoke": 0.03,
    }

    service = SensorService(source=SampleSource(reading))
    validated = service.read()

    assert validated is not None
    assert validated.temperature == 35.2
    assert validated.humidity == 61.4
    assert validated.gas == 0.12
    assert validated.smoke == 0.03


def test_sensor_service_handles_invalid_reading():
    invalid = {
        "timestamp": "2026-09-27T13:42:00+05:30",
        "temperature": 120.0,
        "humidity": 61.4,
        "gas": 0.12,
        "smoke": 0.03,
    }

    service = SensorService(source=SampleSource(invalid), logger=logging.getLogger("sensor_test"))
    result = service.read()

    assert result is None


def test_service_supports_multiple_source_implementations():
    source_a = SampleSource({
        "timestamp": "2026-09-27T13:42:00+05:30",
        "temperature": 30.0,
        "humidity": 50.0,
        "gas": 0.10,
        "smoke": 0.02,
    })
    source_b = SampleSource({
        "timestamp": "2026-09-27T13:42:00+05:30",
        "temperature": 31.0,
        "humidity": 55.0,
        "gas": 0.15,
        "smoke": 0.03,
    })

    service_a = SensorService(source=source_a)
    service_b = SensorService(source=source_b)

    assert service_a.read().temperature == 30.0
    assert service_b.read().temperature == 31.0
