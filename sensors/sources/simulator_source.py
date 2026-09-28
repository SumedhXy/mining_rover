from __future__ import annotations

import math
from datetime import datetime, timezone

from sensors.sensor_schema import StandardSensorReading


class SimulatorSource:
    """Generate gradual, realistic sensor values for development, testing, and offline simulation."""

    def __init__(self, scenario: str = "normal") -> None:
        self.scenario = scenario.lower()
        self._tick = 0

    def set_scenario(self, scenario: str) -> None:
        self.scenario = scenario.lower()

    def read(self) -> StandardSensorReading:
        self._tick += 1

        scenario = self.scenario
        if scenario == "high_temperature":
            temperature = 65.0 + 1.2 * math.sin(self._tick / 4.0)
            humidity = 48.0 + 4.0 * math.cos(self._tick / 5.0)
            pressure = 1008.5 + 1.5 * math.sin(self._tick / 8.0)
            gas = 0.08 + 0.04 * abs(math.sin(self._tick / 6.0))
            smoke = 0.05 + 0.03 * abs(math.cos(self._tick / 8.0))
        elif scenario == "gas_hazard":
            temperature = 38.0 + 1.0 * math.sin(self._tick / 5.0)
            humidity = 60.0 + 5.0 * math.cos(self._tick / 6.0)
            pressure = 1011.0 + 2.0 * math.cos(self._tick / 7.0)
            gas = 0.82 + 0.10 * math.sin(self._tick / 3.0)
            smoke = 0.06 + 0.04 * abs(math.sin(self._tick / 7.0))
        elif scenario == "smoke_hazard":
            temperature = 45.0 + 1.8 * math.sin(self._tick / 4.0)
            humidity = 54.0 + 3.5 * math.cos(self._tick / 7.0)
            pressure = 1012.3 + 1.0 * math.sin(self._tick / 5.0)
            gas = 0.18 + 0.08 * abs(math.sin(self._tick / 5.0))
            smoke = 0.88 + 0.08 * math.sin(self._tick / 4.0)
        else:  # normal scenario
            temperature = 35.0 + 1.8 * math.sin(self._tick / 4.0)
            humidity = 60.0 + 8.0 * math.cos(self._tick / 6.0)
            pressure = 1013.25 + 2.5 * math.sin(self._tick / 10.0)
            gas = 0.12 + 0.10 * abs(math.sin(self._tick / 5.0))
            smoke = 0.03 + 0.07 * abs(math.sin(self._tick / 7.0))

        temperature = max(-40.0, min(100.0, round(temperature, 2)))
        humidity = max(0.0, min(100.0, round(humidity, 2)))
        pressure = max(500.0, min(1500.0, round(pressure, 2)))
        gas = max(0.0, min(1.0, round(gas, 3)))
        smoke = max(0.0, min(1.0, round(smoke, 3)))

        return StandardSensorReading(
            timestamp=datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
            temperature_c=temperature,
            humidity_percent=humidity,
            pressure_hpa=pressure,
            methane=gas,
            air_quality=smoke,
            source="simulator",
            device_id="simulator-01",
            sequence_number=self._tick,
        )


__all__ = ["SimulatorSource"]
