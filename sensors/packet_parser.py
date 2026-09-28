from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sensors.sensor_schema import StandardSensorReading

logger = logging.getLogger("packet_parser")


class PacketParseError(ValueError):
    """Raised when an ESP32 telemetry packet is malformed or invalid."""


class PacketParser:
    """Parser and validator for newline-delimited JSON packets from ESP32."""

    @staticmethod
    def parse_dict(data: Dict[str, Any], strict: bool = False) -> Optional[StandardSensorReading]:
        """Validate and convert a dictionary into a StandardSensorReading."""
        try:
            # 1. Temperature check
            temp_val = data.get("temperature_c") if "temperature_c" in data else data.get("temperature")
            if temp_val is None:
                raise PacketParseError("Missing required field: temperature / temperature_c")
            if not isinstance(temp_val, (int, float)) or isinstance(temp_val, bool):
                raise PacketParseError(f"Invalid temperature value: {temp_val!r} (must be numeric)")
            temp_float = float(temp_val)
            if not (-40.0 <= temp_float <= 100.0):
                raise PacketParseError(f"Temperature {temp_float} °C out of range [-40, 100]")

            # 2. Humidity check
            hum_val = data.get("humidity_percent") if "humidity_percent" in data else data.get("humidity")
            if hum_val is None:
                raise PacketParseError("Missing required field: humidity / humidity_percent")
            if not isinstance(hum_val, (int, float)) or isinstance(hum_val, bool):
                raise PacketParseError(f"Invalid humidity value: {hum_val!r} (must be numeric)")
            hum_float = float(hum_val)
            if not (0.0 <= hum_float <= 100.0):
                raise PacketParseError(f"Humidity {hum_float} % out of range [0, 100]")

            # 3. Pressure check (default standard sea-level 1013.25 hPa if omitted)
            press_val = data.get("pressure_hpa") if "pressure_hpa" in data else data.get("pressure", 1013.25)
            if not isinstance(press_val, (int, float)) or isinstance(press_val, bool):
                raise PacketParseError(f"Invalid pressure value: {press_val!r} (must be numeric)")
            press_float = float(press_val)
            if press_float <= 0.0:
                raise PacketParseError(f"Pressure must be positive: {press_float} hPa")

            # 4. MQ-4 Methane / Gas check
            gas_raw = None
            for key in ("mq4", "methane", "gas", "methane_raw"):
                if key in data and data[key] is not None:
                    gas_raw = data[key]
                    break
            if gas_raw is None:
                raise PacketParseError("Missing required field: mq4 / methane / gas")
            if not isinstance(gas_raw, (int, float)) or isinstance(gas_raw, bool):
                raise PacketParseError(f"Invalid gas/methane value: {gas_raw!r} (must be numeric)")
            gas_float = float(gas_raw)
            if gas_float < 0.0:
                raise PacketParseError(f"Gas/methane reading cannot be negative: {gas_float}")
            # If ESP32 reports raw ADC count (e.g. 12-bit ADC 0-4095), normalize to [0, 1] index
            if gas_float > 1.0:
                gas_normalized = min(1.0, gas_float / 4095.0)
            else:
                gas_normalized = gas_float

            # 5. MQ-135 Air Quality / Smoke check
            air_raw = None
            for key in ("mq135", "air_quality", "smoke", "air_quality_raw"):
                if key in data and data[key] is not None:
                    air_raw = data[key]
                    break
            if air_raw is None:
                raise PacketParseError("Missing required field: mq135 / air_quality / smoke")
            if not isinstance(air_raw, (int, float)) or isinstance(air_raw, bool):
                raise PacketParseError(f"Invalid air quality value: {air_raw!r} (must be numeric)")
            air_float = float(air_raw)
            if air_float < 0.0:
                raise PacketParseError(f"Air quality reading cannot be negative: {air_float}")
            # If ESP32 reports raw ADC count (e.g. 12-bit ADC 0-4095), normalize to [0, 1] index
            if air_float > 1.0:
                air_normalized = min(1.0, air_float / 4095.0)
            else:
                air_normalized = air_float

            # 6. Timestamp handling
            ts_raw = data.get("timestamp")
            timestamp = None
            if ts_raw and isinstance(ts_raw, str) and ts_raw.strip():
                try:
                    iso_candidate = ts_raw.strip()
                    if iso_candidate.endswith("Z"):
                        iso_candidate = iso_candidate[:-1] + "+00:00"
                    dt = datetime.fromisoformat(iso_candidate)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    timestamp = dt.isoformat()
                except Exception:
                    # Invalid timestamp format: fallback to receive timestamp
                    timestamp = None

            if not timestamp:
                timestamp = datetime.now(timezone.utc).isoformat()

            # Metadata
            device_id = str(data.get("device_id") or "sensor_01")
            source = str(data.get("source") or "esp32")
            seq = data.get("sequence_number") or data.get("seq")
            seq_num = int(seq) if seq is not None and str(seq).isdigit() else None

            return StandardSensorReading(
                timestamp=timestamp,
                temperature_c=temp_float,
                humidity_percent=hum_float,
                pressure_hpa=press_float,
                methane=gas_normalized,
                air_quality=air_normalized,
                source=source,
                device_id=device_id,
                sequence_number=seq_num,
            )

        except PacketParseError as exc:
            logger.warning("Packet validation rejected: %s", exc)
            if strict:
                raise
            return None
        except Exception as exc:
            logger.error("Unexpected error validating packet dictionary: %s", exc)
            if strict:
                raise PacketParseError(f"Unexpected packet validation failure: {exc}") from exc
            return None

    @classmethod
    def parse(cls, raw_data: str | bytes, strict: bool = False) -> Optional[StandardSensorReading]:
        """Parse one raw JSON line from ESP32 into a StandardSensorReading."""
        if raw_data is None:
            return None

        if isinstance(raw_data, bytes):
            try:
                line = raw_data.decode("utf-8", errors="replace").strip()
            except Exception as exc:
                logger.warning("Failed to decode raw bytes: %s", exc)
                if strict:
                    raise PacketParseError(f"UTF-8 decode error: {exc}") from exc
                return None
        else:
            line = str(raw_data).strip()

        if not line:
            return None

        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            logger.warning("Malformed JSON packet discarded: %s (%s)", line[:60], exc)
            if strict:
                raise PacketParseError(f"Malformed JSON: {exc}") from exc
            return None

        if not isinstance(payload, dict):
            logger.warning("Packet JSON payload must be a JSON object: %s", type(payload))
            if strict:
                raise PacketParseError("Packet JSON root must be an object")
            return None

        return cls.parse_dict(payload, strict=strict)

    @classmethod
    def parse_stream(cls, stream_data: str | bytes, strict: bool = False) -> List[StandardSensorReading]:
        """Parse multiple newline-delimited packets, discarding invalid ones safely."""
        if isinstance(stream_data, bytes):
            text = stream_data.decode("utf-8", errors="replace")
        else:
            text = str(stream_data)

        readings: List[StandardSensorReading] = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            reading = cls.parse(line, strict=strict)
            if reading is not None:
                readings.append(reading)
        return readings
