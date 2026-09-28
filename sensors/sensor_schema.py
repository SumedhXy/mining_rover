from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(init=False)
class StandardSensorReading:
    """Normalized, hardware-independent sensor reading.
    
    Standardized fields:
        timestamp: ISO 8601 UTC timestamp string with timezone.
        device_id: Identifier of the originating sensor node (e.g. 'sensor_01').
        temperature_c: Temperature in degrees Celsius.
        humidity_percent: Relative humidity percentage (0.0 to 100.0%).
        pressure_hpa: Atmospheric pressure in hectopascals (positive float).
        methane: MQ-4 normalized reading / index (>= 0.0).
        air_quality: MQ-135 normalized reading / index (>= 0.0).
        source: Origin identifier ('esp32', 'simulator', etc.).
        sequence_number: Optional sequential packet counter.
    
    Backward-compatibility properties:
        temperature -> temperature_c
        humidity    -> humidity_percent
        pressure    -> pressure_hpa
        gas / mq4 / methane_raw         -> methane
        smoke / mq135 / air_quality_raw -> air_quality
    """

    timestamp: str
    temperature_c: float
    humidity_percent: float
    pressure_hpa: float
    methane: float
    air_quality: float
    source: Optional[str]
    device_id: Optional[str]
    sequence_number: Optional[int]

    def __init__(
        self,
        timestamp: str,
        temperature: Optional[float] = None,
        humidity: Optional[float] = None,
        gas: Optional[float] = None,
        smoke: Optional[float] = None,
        temperature_c: Optional[float] = None,
        humidity_percent: Optional[float] = None,
        pressure_hpa: Optional[float] = None,
        pressure: Optional[float] = None,
        methane: Optional[float] = None,
        air_quality: Optional[float] = None,
        mq4: Optional[float] = None,
        mq135: Optional[float] = None,
        methane_raw: Optional[float] = None,
        air_quality_raw: Optional[float] = None,
        source: Optional[str] = None,
        device_id: Optional[str] = None,
        sequence_number: Optional[int] = None,
    ) -> None:
        self.timestamp = self._validate_timestamp(timestamp)

        # Resolve temperature
        resolved_temp = temperature_c if temperature_c is not None else temperature
        if resolved_temp is None:
            raise ValueError("temperature is required")
        self.temperature_c = self._validate_float("temperature", resolved_temp, -40.0, 100.0)

        # Resolve humidity
        resolved_hum = humidity_percent if humidity_percent is not None else humidity
        if resolved_hum is None:
            raise ValueError("humidity is required")
        self.humidity_percent = self._validate_float("humidity", resolved_hum, 0.0, 100.0)

        # Resolve pressure (default 1013.25 hPa standard atmosphere if omitted)
        resolved_press = pressure_hpa if pressure_hpa is not None else (pressure if pressure is not None else 1013.25)
        self.pressure_hpa = self._validate_pressure("pressure", resolved_press)

        # Resolve methane / gas
        resolved_gas = methane if methane is not None else (
            gas if gas is not None else (mq4 if mq4 is not None else methane_raw)
        )
        if resolved_gas is None:
            raise ValueError("gas/methane is required")
        self.methane = self._validate_float("gas", resolved_gas, 0.0, 1.0)

        # Resolve air_quality / smoke
        resolved_smoke = air_quality if air_quality is not None else (
            smoke if smoke is not None else (mq135 if mq135 is not None else air_quality_raw)
        )
        if resolved_smoke is None:
            raise ValueError("smoke/air_quality is required")
        self.air_quality = self._validate_float("smoke", resolved_smoke, 0.0, 1.0)

        self.source = source
        self.device_id = device_id or "sensor_01"
        self.sequence_number = sequence_number

    # --- Property Aliases for Full Backward Compatibility ---

    @property
    def temperature(self) -> float:
        return self.temperature_c

    @temperature.setter
    def temperature(self, value: float) -> None:
        self.temperature_c = self._validate_float("temperature", value, -40.0, 100.0)

    @property
    def humidity(self) -> float:
        return self.humidity_percent

    @humidity.setter
    def humidity(self, value: float) -> None:
        self.humidity_percent = self._validate_float("humidity", value, 0.0, 100.0)

    @property
    def pressure(self) -> float:
        return self.pressure_hpa

    @pressure.setter
    def pressure(self, value: float) -> None:
        self.pressure_hpa = self._validate_pressure("pressure", value)

    @property
    def gas(self) -> float:
        return self.methane

    @gas.setter
    def gas(self, value: float) -> None:
        self.methane = self._validate_float("gas", value, 0.0, 1.0)

    @property
    def smoke(self) -> float:
        return self.air_quality

    @smoke.setter
    def smoke(self, value: float) -> None:
        self.air_quality = self._validate_float("smoke", value, 0.0, 1.0)

    @property
    def mq4(self) -> float:
        return self.methane

    @property
    def mq135(self) -> float:
        return self.air_quality

    @property
    def methane_raw(self) -> float:
        return self.methane

    @property
    def air_quality_raw(self) -> float:
        return self.air_quality

    # --- Validation Methods ---

    @staticmethod
    def _validate_timestamp(value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("timestamp is required and must be a non-empty ISO 8601 string")

        try:
            iso_str = value
            if iso_str.endswith("Z"):
                iso_str = iso_str[:-1] + "+00:00"
            dt = datetime.fromisoformat(iso_str)
        except ValueError as exc:
            raise ValueError("timestamp must be a valid ISO 8601 string") from exc

        if dt.tzinfo is None or dt.utcoffset() is None:
            raise ValueError("timestamp must include timezone information")

        return value

    @staticmethod
    def _validate_float(field_name: str, value: Any, minimum: float, maximum: float) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{field_name} must be numeric")

        numeric = float(value)
        if numeric < minimum or numeric > maximum:
            raise ValueError(f"{field_name} must be between {minimum} and {maximum}")

        return numeric

    @staticmethod
    def _validate_pressure(field_name: str, value: Any) -> float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{field_name} must be numeric")

        numeric = float(value)
        if numeric <= 0.0:
            raise ValueError(f"{field_name} must be positive")

        return numeric

    @classmethod
    def from_dict(cls, data: dict) -> "StandardSensorReading":
        """Construct a StandardSensorReading instance from a dictionary."""
        has_temp = "temperature" in data or "temperature_c" in data
        has_hum = "humidity" in data or "humidity_percent" in data
        has_gas = any(k in data for k in ("gas", "methane", "mq4", "methane_raw"))
        has_smoke = any(k in data for k in ("smoke", "air_quality", "mq135", "air_quality_raw"))
        has_ts = "timestamp" in data

        missing = []
        if not has_ts:
            missing.append("timestamp")
        if not has_temp:
            missing.append("temperature / temperature_c")
        if not has_hum:
            missing.append("humidity / humidity_percent")
        if not has_gas:
            missing.append("gas / methane / mq4")
        if not has_smoke:
            missing.append("smoke / air_quality / mq135")

        if missing:
            raise ValueError(f"Missing required sensor fields: {', '.join(missing)}")

        return cls(
            timestamp=data["timestamp"],
            temperature=data.get("temperature"),
            temperature_c=data.get("temperature_c"),
            humidity=data.get("humidity"),
            humidity_percent=data.get("humidity_percent"),
            pressure_hpa=data.get("pressure_hpa"),
            pressure=data.get("pressure"),
            methane=data.get("methane"),
            gas=data.get("gas"),
            mq4=data.get("mq4"),
            methane_raw=data.get("methane_raw"),
            air_quality=data.get("air_quality"),
            smoke=data.get("smoke"),
            mq135=data.get("mq135"),
            air_quality_raw=data.get("air_quality_raw"),
            source=data.get("source"),
            device_id=data.get("device_id"),
            sequence_number=data.get("sequence_number"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert reading to dictionary with both canonical and alias fields."""
        return {
            "timestamp": self.timestamp,
            "device_id": self.device_id,
            "temperature_c": self.temperature_c,
            "humidity_percent": self.humidity_percent,
            "pressure_hpa": self.pressure_hpa,
            "methane": self.methane,
            "air_quality": self.air_quality,
            "temperature": self.temperature_c,
            "humidity": self.humidity_percent,
            "pressure": self.pressure_hpa,
            "gas": self.methane,
            "smoke": self.air_quality,
            "source": self.source,
            "sequence_number": self.sequence_number,
        }
