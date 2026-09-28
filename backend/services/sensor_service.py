from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.database import SQLiteDatabase


class SensorAPIService:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def add_reading(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = payload.get("timestamp") or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        device_id = payload.get("device_id", "mining_rover_01")
        source = payload.get("source", "simulator")

        # Map flat temperature / gas keys to Phase 3 columns
        temp_c = payload.get("temperature_c") or payload.get("temperature")
        hum_pct = payload.get("humidity_percent") or payload.get("humidity")
        press_hpa = payload.get("pressure_hpa") or payload.get("pressure")
        mq4_val = payload.get("mq4") or payload.get("gas")
        mq135_val = payload.get("mq135") or payload.get("smoke")

        # Insert multi-column record in Phase 3 table
        self.database.insert_sensor_reading(
            timestamp=timestamp,
            device_id=device_id,
            temperature_c=float(temp_c) if temp_c is not None else None,
            humidity_percent=float(hum_pct) if hum_pct is not None else None,
            pressure_hpa=float(press_hpa) if press_hpa is not None else None,
            mq4=float(mq4_val) if mq4_val is not None else None,
            mq135=float(mq135_val) if mq135_val is not None else None,
            source=source,
        )

        # Also store individual metric records for backwards compatibility
        for key in ("temperature", "humidity", "gas", "smoke", "battery", "vibration"):
            if key in payload and payload[key] is not None:
                self.database.insert_sensor_reading(
                    timestamp=timestamp,
                    device_id=device_id,
                    sensor_type=key,
                    value=float(payload[key]),
                    unit="C" if key == "temperature" else "%" if key in {"humidity", "battery"} else "g" if key == "vibration" else "normalized",
                    valid=True,
                    source=source,
                )

        return {"status": "accepted", "timestamp": timestamp}

    def latest(self) -> Dict[str, Any]:
        rows = self.database.get_latest_sensor_readings(limit=25)
        latest_ts = rows[0]["timestamp"] if rows else None
        source_val = rows[0]["source"] if rows else "esp32_sensor_01"

        temp_c: Optional[float] = None
        hum_pct: Optional[float] = None
        press_hpa: Optional[float] = None
        mq4_val: Optional[float] = None
        mq135_val: Optional[float] = None

        readings_list: List[Dict[str, Any]] = []

        for row in rows:
            if temp_c is None and row.get("temperature_c") is not None:
                temp_c = float(row["temperature_c"])
            if hum_pct is None and row.get("humidity_percent") is not None:
                hum_pct = float(row["humidity_percent"])
            if press_hpa is None and row.get("pressure_hpa") is not None:
                press_hpa = float(row["pressure_hpa"])
            if mq4_val is None and row.get("mq4") is not None:
                mq4_val = float(row["mq4"])
            if mq135_val is None and row.get("mq135") is not None:
                mq135_val = float(row["mq135"])

            st = row.get("sensor_type")
            val = row.get("value")
            if st and val is not None:
                if temp_c is None and st in {"temperature", "temp"}:
                    temp_c = float(val)
                elif hum_pct is None and st in {"humidity", "hum"}:
                    hum_pct = float(val)
                elif press_hpa is None and st in {"pressure", "press"}:
                    press_hpa = float(val)
                elif mq4_val is None and st in {"gas", "mq4"}:
                    mq4_val = float(val)
                elif mq135_val is None and st in {"smoke", "mq135"}:
                    mq135_val = float(val)

                readings_list.append({
                    "sensor_type": st,
                    "value": val,
                    "unit": row.get("unit", ""),
                    "valid": bool(row.get("valid", True)),
                    "source": row.get("source", "simulator"),
                    "device_id": row.get("device_id", "mining_rover_01"),
                })

        return {
            "timestamp": latest_ts,
            "temperature_c": temp_c,
            "humidity_percent": hum_pct,
            "pressure_hpa": press_hpa,
            "mq4": mq4_val,
            "mq135": mq135_val,
            "source": source_val,
            "readings": readings_list,
        }

    def history(
        self,
        limit: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        rows = self.database.get_sensor_history(start_time=start_time, end_time=end_time, limit=limit)
        return [
            {
                "id": row.get("id"),
                "timestamp": row.get("timestamp"),
                "sensor_type": row.get("sensor_type"),
                "value": row.get("value"),
                "unit": row.get("unit"),
                "temperature_c": row.get("temperature_c"),
                "humidity_percent": row.get("humidity_percent"),
                "pressure_hpa": row.get("pressure_hpa"),
                "mq4": row.get("mq4"),
                "mq135": row.get("mq135"),
                "valid": bool(row.get("valid", True)),
                "source": row.get("source"),
                "device_id": row.get("device_id"),
            }
            for row in rows
        ]
