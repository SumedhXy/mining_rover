from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

from sensors.packet_parser import PacketParser
from sensors.sensor_schema import StandardSensorReading

logger = logging.getLogger("esp32_receiver")

# Attempt importing serial; fail-soft if not available
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    serial = None  # type: ignore
    SERIAL_AVAILABLE = False


class ESP32Receiver:
    """Hardware-resilient serial receiver for ESP32 Environmental Sensor Node #1.
    
    Reads newline-delimited JSON packets, parses them via PacketParser,
    and returns StandardSensorReading objects.
    """

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: Optional[int] = None,
        timeout: Optional[float] = None,
        serial_instance: Any = None,
    ) -> None:
        self.port = port or os.getenv("ROVER_SENSOR_PORT")
        self.baudrate = baudrate or int(os.getenv("ROVER_SENSOR_BAUDRATE", "115200"))
        self.timeout = timeout if timeout is not None else float(os.getenv("ROVER_SENSOR_TIMEOUT", "1.0"))
        self.serial = serial_instance
        self._is_external_stream = serial_instance is not None

        # Statistics & status
        self.packets_received = 0
        self.packets_failed = 0
        self.last_packet_time: Optional[float] = None
        self._connected = False
        self._last_reconnect_attempt = 0.0
        self._reconnect_interval = 2.0  # seconds

        if self._is_external_stream:
            self._connected = True

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """Attempt to open the serial port to ESP32."""
        if self._is_external_stream:
            self._connected = True
            return True

        if not self.port:
            logger.debug("No serial port configured for ESP32 receiver (ROVER_SENSOR_PORT is empty)")
            self._connected = False
            return False

        if not SERIAL_AVAILABLE:
            logger.warning("pyserial is not available; cannot open serial port %s", self.port)
            self._connected = False
            return False

        try:
            self.disconnect()
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
            )
            self._connected = True
            logger.info("Connected to ESP32 sensor node on %s @ %d baud", self.port, self.baudrate)
            return True
        except Exception as exc:
            logger.warning("Could not connect to ESP32 on port %s: %s", self.port, exc)
            self._connected = False
            self.serial = None
            return False

    def disconnect(self) -> None:
        """Close serial connection gracefully."""
        self._connected = False
        if self.serial and not self._is_external_stream:
            try:
                self.serial.close()
            except Exception:
                pass
            self.serial = None
            logger.info("Disconnected from ESP32 serial port")

    def read(self) -> Optional[StandardSensorReading]:
        """Read the next packet from ESP32, returning StandardSensorReading or None."""
        if not self._connected and not self._is_external_stream:
            now = time.time()
            if now - self._last_reconnect_attempt >= self._reconnect_interval:
                self._last_reconnect_attempt = now
                if not self.connect():
                    return None
            else:
                return None

        if self.serial is None:
            return None

        try:
            # Read a single newline-terminated line
            raw_line = self.serial.readline()
            if not raw_line:
                # Timeout or empty read
                return None

            reading = PacketParser.parse(raw_line)
            if reading is not None:
                self.packets_received += 1
                self.last_packet_time = time.time()
                return reading
            else:
                self.packets_failed += 1
                return None

        except (OSError, Exception) as exc:
            # Serial disconnect or read error
            logger.warning("Serial error reading from ESP32: %s", exc)
            self.packets_failed += 1
            if not self._is_external_stream:
                self.disconnect()
            return None


# SensorSource alias for backward and modular compatibility
ESP32SerialSource = ESP32Receiver

__all__ = ["ESP32Receiver", "ESP32SerialSource"]
