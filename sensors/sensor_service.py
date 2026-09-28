from __future__ import annotations

import logging
from typing import Optional, Protocol, runtime_checkable

from sensors.sensor_schema import StandardSensorReading


@runtime_checkable
class SensorSource(Protocol):
    def read(self) -> Optional[StandardSensorReading]:
        """Return a raw or normalized sensor reading."""


class SensorService:
    """Hardware-independent sensor service.
    
    Decouples downstream consumers (Decision Engine, Database, Backend)
    from whether the underlying data originates from physical ESP32
    hardware or the local simulator.
    """

    def __init__(self, source: SensorSource, logger: Optional[logging.Logger] = None) -> None:
        self.source = source
        self.logger = logger or logging.getLogger("sensor_service")
        self._latest_reading: Optional[StandardSensorReading] = None
        self._is_running = False

    @property
    def is_running(self) -> bool:
        return self._is_running

    def start(self) -> None:
        """Start the sensor service."""
        self._is_running = True
        # If source has a connect method (like ESP32Receiver), invoke it
        if hasattr(self.source, "connect") and callable(getattr(self.source, "connect")):
            try:
                self.source.connect()
            except Exception as exc:
                self.logger.warning("Error initiating source connection: %s", exc)
        self.logger.info("Sensor service started (Source: %s)", type(self.source).__name__)

    def stop(self) -> None:
        """Stop the sensor service."""
        self._is_running = False
        if hasattr(self.source, "disconnect") and callable(getattr(self.source, "disconnect")):
            try:
                self.source.disconnect()
            except Exception as exc:
                self.logger.warning("Error disconnecting source: %s", exc)
        self.logger.info("Sensor service stopped")

    def read(self) -> Optional[StandardSensorReading]:
        """Fetch and validate the next reading from the configured sensor source."""
        try:
            raw_reading = self.source.read()
            if raw_reading is None:
                self.logger.debug("Sensor source returned no reading")
                return None

            if isinstance(raw_reading, StandardSensorReading):
                self._latest_reading = raw_reading
                self.logger.debug("Reading received from sensor source")
                return raw_reading

            if isinstance(raw_reading, dict):
                reading = StandardSensorReading.from_dict(raw_reading)
                self._latest_reading = reading
                self.logger.debug("Dictionary reading parsed from sensor source")
                return reading

            raise TypeError(f"Sensor source returned unsupported reading format: {type(raw_reading)}")
        except (TypeError, ValueError) as exc:
            self.logger.error("Invalid sensor reading: %s", exc)
            return None
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.exception("Sensor source failure: %s", exc)
            return None

    def get_latest(self) -> Optional[StandardSensorReading]:
        """Return the latest successfully acquired sensor reading."""
        if self._latest_reading is not None:
            return self._latest_reading
        return self.read()

    def get_all_latest(self) -> Optional[StandardSensorReading]:
        """Convenience method returning the latest reading with all standard metrics."""
        return self.get_latest()


__all__ = ["SensorService", "SensorSource"]
