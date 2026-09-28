from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.database import SQLiteDatabase


class VisionAPIService:
    def __init__(self, database: SQLiteDatabase):
        self.database = database

    def add_detection(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        timestamp = payload.get("timestamp") or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        device_id = payload.get("device_id", "mining_rover_01")
        for detection in payload.get("detections", []) or []:
            class_name = detection.get("class_name") or detection.get("class") or "unknown"
            confidence = float(detection.get("confidence", 0.0) or 0.0)
            bbox = detection.get("bbox") or []
            image_path = detection.get("image_path")
            source = detection.get("source", "yolo")

            bbox_x1 = float(bbox[0]) if len(bbox) > 0 else None
            bbox_y1 = float(bbox[1]) if len(bbox) > 1 else None
            bbox_x2 = float(bbox[2]) if len(bbox) > 2 else None
            bbox_y2 = float(bbox[3]) if len(bbox) > 3 else None

            self.database.insert_vision_detection(
                timestamp=detection.get("timestamp") or timestamp,
                device_id=detection.get("device_id", device_id),
                class_name=class_name,
                confidence=confidence,
                bbox_x1=bbox_x1,
                bbox_y1=bbox_y1,
                bbox_x2=bbox_x2,
                bbox_y2=bbox_y2,
                image_path=image_path,
                source=source,
                x_center=bbox_x1,
                y_center=bbox_y1,
                width=bbox_x2,
                height=bbox_y2,
            )
        return {"status": "accepted", "timestamp": timestamp}

    def latest(self) -> Dict[str, Any]:
        rows = self.database.get_recent_detections(limit=20)
        detections: List[Dict[str, Any]] = []
        for row in rows:
            # Build bounding box
            if row.get("bbox_x1") is not None:
                box = [row["bbox_x1"], row.get("bbox_y1", 0.0), row.get("bbox_x2", 0.0), row.get("bbox_y2", 0.0)]
            else:
                box = [row.get("x_center", 0.0), row.get("y_center", 0.0), row.get("width", 0.0), row.get("height", 0.0)]

            detections.append({
                "class_name": row["class_name"],
                "class": row["class_name"],  # backward compatibility alias
                "confidence": row["confidence"],
                "bbox": box,
                "image_path": row.get("image_path"),
                "source": row.get("source", "yolo"),
                "device_id": row.get("device_id", "mining_rover_01"),
                "timestamp": row.get("timestamp"),
            })

        return {
            "timestamp": rows[0]["timestamp"] if rows else None,
            "detections": detections,
        }

    def history(
        self,
        limit: int = 100,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        conn = self.database.connect()
        try:
            query = "SELECT * FROM vision_detections WHERE 1=1"
            params: List[Any] = []
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, tuple(params)).fetchall()
            items: List[Dict[str, Any]] = []
            for r in rows:
                row = dict(r)
                if row.get("bbox_x1") is not None:
                    box = [row["bbox_x1"], row.get("bbox_y1", 0.0), row.get("bbox_x2", 0.0), row.get("bbox_y2", 0.0)]
                else:
                    box = [row.get("x_center", 0.0), row.get("y_center", 0.0), row.get("width", 0.0), row.get("height", 0.0)]

                items.append({
                    "id": row.get("id"),
                    "timestamp": row.get("timestamp"),
                    "class_name": row.get("class_name"),
                    "confidence": row.get("confidence"),
                    "bbox": box,
                    "image_path": row.get("image_path"),
                    "source": row.get("source", "yolo"),
                    "device_id": row.get("device_id", "mining_rover_01"),
                })
            return items
        finally:
            conn.close()
