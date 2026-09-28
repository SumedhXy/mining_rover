from __future__ import annotations

from typing import Any, Dict

from database.database import SQLiteDatabase


class TelemetryService:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def latest(self) -> Dict[str, Any]:
        sensors = self.database.get_latest_sensor_readings(limit=20)
        detections = self.database.get_recent_detections(limit=20)
        hazards = self.database.get_recent_hazards(limit=1)

        sensor_summary = {}
        for row in sensors:
            sensor_summary[row["sensor_type"]] = {
                "value": row["value"],
                "unit": row["unit"],
                "timestamp": row["timestamp"],
            }

        latest_hazard = hazards[0] if hazards else None
        return {
            "timestamp": None if not sensors else sensors[0]["timestamp"],
            "sensors": sensor_summary,
            "vision": {"detections": [
                {
                    "class": row["class_name"],
                    "confidence": row["confidence"],
                    "bbox": [row["x_center"], row["y_center"], row["width"], row["height"]],
                }
                for row in detections
            ]},
            "decision": {
                "hazard": latest_hazard["hazard"] if latest_hazard else "none",
                "severity": latest_hazard["severity"] if latest_hazard else "LOW",
                "confidence": latest_hazard["confidence"] if latest_hazard else 0.0,
                "message": latest_hazard["message"] if latest_hazard else "No decision available",
            },
            "system_status": "online",
        }

    def history(self, limit: int = 100) -> Dict[str, Any]:
        sensors = self.database.get_latest_sensor_readings(limit=limit)
        detections = self.database.get_recent_detections(limit=limit)
        hazards = self.database.get_recent_hazards(limit=limit)
        return {
            "sensors": sensors,
            "detections": detections,
            "hazards": hazards,
        }
