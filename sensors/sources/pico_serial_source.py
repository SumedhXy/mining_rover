from __future__ import annotations

from sensors.sensor_schema import StandardSensorReading


class PicoSerialSource:
    """Placeholder adapter for future Raspberry Pi Pico serial sensor input."""

    def __init__(self, serial_port: str = "COM3", baud_rate: int = 115200):
        self.serial_port = serial_port
        self.baud_rate = baud_rate

    def read(self) -> StandardSensorReading:
        raise RuntimeError("Pico serial input is not implemented yet. Configure a real device before use.")
