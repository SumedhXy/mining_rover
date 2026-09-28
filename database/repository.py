from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from database.connection import DatabaseConnection

logger = logging.getLogger("database.repository")


class Repository:
    """Repository providing domain-level data access operations on SQLite."""

    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    # ---------------------------------------------------------
    # 1. Sensor Telemetry
    # ---------------------------------------------------------
    def insert_sensor_reading(
        self,
        timestamp: str,
        device_id: str = "mining_rover_01",
        temperature_c: Optional[float] = None,
        humidity_percent: Optional[float] = None,
        pressure_hpa: Optional[float] = None,
        mq4: Optional[float] = None,
        mq135: Optional[float] = None,
        sequence_number: Optional[int] = None,
        source: str = "simulator",
        sync_status: str = "pending",
        # Legacy keyword parameters for backward compatibility
        sensor_type: Optional[str] = None,
        value: Optional[float] = None,
        unit: Optional[str] = None,
        valid: Optional[bool] = None,
        synced: Optional[bool] = None,
    ) -> int:
        """Insert a sensor telemetry record, supporting both Phase 3 and legacy interfaces."""
        if synced is not None:
            sync_status = "synced" if synced else "pending"
        synced_int = 1 if sync_status == "synced" else 0

        # Handle legacy sensor_type / value mapping if caller passed single sensor metrics
        if sensor_type is not None and value is not None:
            st = str(sensor_type).lower()
            val_f = float(value)
            if st in {"temp", "temperature"} and temperature_c is None:
                temperature_c = val_f
            elif st in {"hum", "humidity"} and humidity_percent is None:
                humidity_percent = val_f
            elif st in {"press", "pressure"} and pressure_hpa is None:
                pressure_hpa = val_f
            elif st in {"gas", "methane", "mq4"} and mq4 is None:
                mq4 = val_f
            elif st in {"smoke", "air_quality", "mq135"} and mq135 is None:
                mq135 = val_f

        legacy_sensor_type = sensor_type or "standard_reading"
        legacy_value = value if value is not None else (temperature_c or 0.0)
        legacy_unit = unit or ("C" if temperature_c is not None else "")
        legacy_valid = 1 if (valid is None or valid) else 0

        with self.connection.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sensor_readings (
                    device_id, timestamp, temperature_c, humidity_percent, pressure_hpa,
                    mq4, mq135, sequence_number, source, sync_status,
                    sensor_type, value, unit, valid, synced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    device_id,
                    timestamp,
                    float(temperature_c) if temperature_c is not None else None,
                    float(humidity_percent) if humidity_percent is not None else None,
                    float(pressure_hpa) if pressure_hpa is not None else None,
                    float(mq4) if mq4 is not None else None,
                    float(mq135) if mq135 is not None else None,
                    sequence_number,
                    source,
                    sync_status,
                    legacy_sensor_type,
                    float(legacy_value),
                    legacy_unit,
                    legacy_valid,
                    synced_int,
                ),
            )
            return cursor.lastrowid

    def get_latest_sensor_readings(self, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self.connection.connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM sensor_readings
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_sensor_history(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        conn = self.connection.connect()
        try:
            if start_time and end_time:
                rows = conn.execute(
                    """
                    SELECT * FROM sensor_readings
                    WHERE timestamp >= ? AND timestamp <= ?
                    ORDER BY timestamp ASC, id ASC
                    LIMIT ?
                    """,
                    (start_time, end_time, limit),
                ).fetchall()
            elif start_time:
                rows = conn.execute(
                    """
                    SELECT * FROM sensor_readings
                    WHERE timestamp >= ?
                    ORDER BY timestamp ASC, id ASC
                    LIMIT ?
                    """,
                    (start_time, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM sensor_readings
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ---------------------------------------------------------
    # 2. Vision Detections
    # ---------------------------------------------------------
    def insert_vision_detection(
        self,
        timestamp: str,
        class_name: str,
        confidence: float,
        bbox_x1: Optional[float] = None,
        bbox_y1: Optional[float] = None,
        bbox_x2: Optional[float] = None,
        bbox_y2: Optional[float] = None,
        image_path: Optional[str] = None,
        source: str = "yolo",
        mission_id: Optional[int] = None,
        location_id: Optional[int] = None,
        sync_status: str = "pending",
        device_id: str = "mining_rover_01",
        # Legacy parameters
        x_center: Optional[float] = None,
        y_center: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
        synced: Optional[bool] = None,
    ) -> int:
        if synced is not None:
            sync_status = "synced" if synced else "pending"
        synced_int = 1 if sync_status == "synced" else 0

        # If normalized center bbox given, compute box bounds if not provided
        if bbox_x1 is None and x_center is not None and width is not None:
            bbox_x1 = max(0.0, x_center - width / 2.0)
            bbox_x2 = min(1.0, x_center + width / 2.0)
        if bbox_y1 is None and y_center is not None and height is not None:
            bbox_y1 = max(0.0, y_center - height / 2.0)
            bbox_y2 = min(1.0, y_center + height / 2.0)

        with self.connection.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO vision_detections (
                    timestamp, class_name, confidence, bbox_x1, bbox_y1, bbox_x2, bbox_y2,
                    image_path, source, mission_id, location_id, sync_status, device_id,
                    x_center, y_center, width, height, synced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    class_name,
                    float(confidence),
                    float(bbox_x1) if bbox_x1 is not None else None,
                    float(bbox_y1) if bbox_y1 is not None else None,
                    float(bbox_x2) if bbox_x2 is not None else None,
                    float(bbox_y2) if bbox_y2 is not None else None,
                    image_path,
                    source,
                    mission_id,
                    location_id,
                    sync_status,
                    device_id,
                    float(x_center) if x_center is not None else None,
                    float(y_center) if y_center is not None else None,
                    float(width) if width is not None else None,
                    float(height) if height is not None else None,
                    synced_int,
                ),
            )
            return cursor.lastrowid

    def get_latest_detections(self, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self.connection.connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM vision_detections
                ORDER BY timestamp DESC, id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    get_recent_detections = get_latest_detections

    # ---------------------------------------------------------
    # 3. Hazard Events
    # ---------------------------------------------------------
    def insert_hazard_event(
        self,
        timestamp: str,
        hazard_type: Optional[str] = None,
        severity: Optional[str] = None,
        confidence: Optional[float] = None,
        decision_id: Optional[str] = None,
        mission_id: Optional[int] = None,
        location_id: Optional[int] = None,
        reasons_json: Optional[str] = None,
        sensor_evidence_json: Optional[str] = None,
        vision_evidence_json: Optional[str] = None,
        source: str = "sensor_vision_fusion",
        sync_status: str = "pending",
        device_id: str = "mining_rover_01",
        # Legacy parameters
        hazard: Optional[str] = None,
        sources: Optional[str] = None,
        message: Optional[str] = None,
        recommended_action: Optional[str] = None,
        synced: Optional[bool] = None,
    ) -> int:
        if synced is not None:
            sync_status = "synced" if synced else "pending"
        synced_int = 1 if sync_status == "synced" else 0

        final_hazard_type = hazard_type or hazard or "none"
        final_severity = severity or "LOW"
        final_confidence = float(confidence if confidence is not None else 0.5)
        final_decision_id = decision_id or str(uuid.uuid4())[:12]

        legacy_hazard = hazard or final_hazard_type
        legacy_sources = sources or source
        legacy_message = message or reasons_json or ""
        legacy_action = recommended_action or ("EVACUATE" if final_severity in {"HIGH", "CRITICAL"} else "MONITOR")

        with self.connection.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO hazard_events (
                    decision_id, timestamp, mission_id, location_id, hazard_type, severity,
                    confidence, reasons_json, sensor_evidence_json, vision_evidence_json,
                    source, sync_status, device_id, hazard, sources, message,
                    recommended_action, synced
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    final_decision_id,
                    timestamp,
                    mission_id,
                    location_id,
                    final_hazard_type,
                    final_severity,
                    final_confidence,
                    reasons_json,
                    sensor_evidence_json,
                    vision_evidence_json,
                    source,
                    sync_status,
                    device_id,
                    legacy_hazard,
                    legacy_sources,
                    legacy_message,
                    legacy_action,
                    synced_int,
                ),
            )
            return cursor.lastrowid

    def get_latest_hazard(self) -> Optional[Dict[str, Any]]:
        conn = self.connection.connect()
        try:
            row = conn.execute(
                """
                SELECT * FROM hazard_events
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_recent_hazards(self, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self.connection.connect()
        try:
            rows = conn.execute(
                """
                SELECT * FROM hazard_events
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def get_hazard_history(
        self,
        mission_id: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        conn = self.connection.connect()
        try:
            query = "SELECT * FROM hazard_events WHERE 1=1"
            params: List[Any] = []
            if mission_id is not None:
                query += " AND mission_id = ?"
                params.append(mission_id)
            if start_time:
                query += " AND timestamp >= ?"
                params.append(start_time)
            if end_time:
                query += " AND timestamp <= ?"
                params.append(end_time)
            query += " ORDER BY timestamp DESC, id DESC LIMIT ?"
            params.append(limit)

            rows = conn.execute(query, tuple(params)).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ---------------------------------------------------------
    # 4. Missions
    # ---------------------------------------------------------
    def create_mission(
        self,
        mission_code: str,
        status: str = "PLANNED",
        started_at: Optional[str] = None,
        notes: Optional[str] = None,
        start_location_json: Optional[str] = None,
        end_location_json: Optional[str] = None,
    ) -> int:
        now_ts = started_at or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        with self.connection.transaction() as conn:
            if status == "ACTIVE":
                conn.execute("UPDATE missions SET status = 'COMPLETED', ended_at = ? WHERE status = 'ACTIVE'", (now_ts,))
            cursor = conn.execute(
                """
                INSERT INTO missions (
                    mission_code, status, started_at, start_location_json, end_location_json, notes
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (mission_code, status, now_ts, start_location_json, end_location_json, notes),
            )
            return cursor.lastrowid

    def start_mission(self, mission_code_or_id: str | int) -> bool:
        now_ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        with self.connection.transaction() as conn:
            conn.execute("UPDATE missions SET status = 'COMPLETED', ended_at = ? WHERE status = 'ACTIVE'", (now_ts,))
            if isinstance(mission_code_or_id, int) or str(mission_code_or_id).isdigit():
                cursor = conn.execute(
                    "UPDATE missions SET status = 'ACTIVE', started_at = ? WHERE id = ?",
                    (now_ts, int(mission_code_or_id)),
                )
            else:
                cursor = conn.execute(
                    "UPDATE missions SET status = 'ACTIVE', started_at = ? WHERE mission_code = ?",
                    (now_ts, str(mission_code_or_id)),
                )
            return cursor.rowcount > 0

    def end_mission(self, mission_code_or_id: str | int, status: str = "COMPLETED") -> bool:
        now_ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        with self.connection.transaction() as conn:
            if isinstance(mission_code_or_id, int) or str(mission_code_or_id).isdigit():
                cursor = conn.execute(
                    "UPDATE missions SET status = ?, ended_at = ? WHERE id = ?",
                    (status, now_ts, int(mission_code_or_id)),
                )
            else:
                cursor = conn.execute(
                    "UPDATE missions SET status = ?, ended_at = ? WHERE mission_code = ?",
                    (status, now_ts, str(mission_code_or_id)),
                )
            return cursor.rowcount > 0

    def get_active_mission(self) -> Optional[Dict[str, Any]]:
        conn = self.connection.connect()
        try:
            row = conn.execute(
                "SELECT * FROM missions WHERE status = 'ACTIVE' ORDER BY id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def get_mission(self, mission_id: Optional[int] = None, mission_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        conn = self.connection.connect()
        try:
            if mission_id is not None:
                row = conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
            elif mission_code:
                row = conn.execute("SELECT * FROM missions WHERE mission_code = ?", (mission_code,)).fetchone()
            else:
                return None
            return dict(row) if row else None
        finally:
            conn.close()

    def get_mission_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self.connection.connect()
        try:
            rows = conn.execute(
                "SELECT * FROM missions ORDER BY started_at DESC, id DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ---------------------------------------------------------
    # 5. Mission Logs
    # ---------------------------------------------------------
    def insert_mission_log(
        self,
        level: str,
        event_type: str,
        message: str,
        mission_id: Optional[int] = None,
        timestamp: Optional[str] = None,
        metadata_json: Optional[str] = None,
    ) -> int:
        now_ts = timestamp or datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
        with self.connection.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO mission_logs (
                    mission_id, timestamp, level, event_type, message, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (mission_id, now_ts, level.upper(), event_type.upper(), message, metadata_json),
            )
            return cursor.lastrowid

    def get_mission_logs(self, mission_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        conn = self.connection.connect()
        try:
            if mission_id is not None:
                rows = conn.execute(
                    """
                    SELECT * FROM mission_logs
                    WHERE mission_id = ?
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ?
                    """,
                    (mission_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM mission_logs
                    ORDER BY timestamp DESC, id DESC
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    # ---------------------------------------------------------
    # 6. Location / Observation Points
    # ---------------------------------------------------------
    def create_location(
        self,
        location_type: str = "LOCAL_POSITION",
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        label: Optional[str] = None,
        mission_id: Optional[int] = None,
    ) -> int:
        with self.connection.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO locations (mission_id, location_type, x, y, z, label)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    mission_id,
                    location_type,
                    float(x) if x is not None else None,
                    float(y) if y is not None else None,
                    float(z) if z is not None else None,
                    label,
                ),
            )
            return cursor.lastrowid

    def get_location(self, location_id: int) -> Optional[Dict[str, Any]]:
        conn = self.connection.connect()
        try:
            row = conn.execute("SELECT * FROM locations WHERE id = ?", (location_id,)).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ---------------------------------------------------------
    # 7. System Status
    # ---------------------------------------------------------
    def update_system_status(
        self,
        timestamp: str,
        rover_status: str = "RUNNING",
        camera_status: str = "OK",
        sensor_status: str = "OK",
        database_status: str = "OK",
        network_status: str = "OFFLINE",
        sync_status: str = "pending",
        storage_available_mb: Optional[float] = None,
        cpu_temperature_c: Optional[float] = None,
        device_id: str = "mining_rover_01",
        # Legacy parameters
        battery_level: Optional[float] = None,
        system_status: Optional[str] = None,
        last_sensor_update: Optional[str] = None,
        last_vision_update: Optional[str] = None,
        last_decision_update: Optional[str] = None,
    ) -> int:
        legacy_sys = system_status or rover_status
        with self.connection.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO system_status (
                    timestamp, rover_status, camera_status, sensor_status, database_status,
                    network_status, sync_status, storage_available_mb, cpu_temperature_c,
                    device_id, battery_level, system_status, last_sensor_update,
                    last_vision_update, last_decision_update
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    rover_status,
                    camera_status,
                    sensor_status,
                    database_status,
                    network_status,
                    sync_status,
                    float(storage_available_mb) if storage_available_mb is not None else None,
                    float(cpu_temperature_c) if cpu_temperature_c is not None else None,
                    device_id,
                    float(battery_level) if battery_level is not None else None,
                    legacy_sys,
                    last_sensor_update,
                    last_vision_update,
                    last_decision_update,
                ),
            )
            return cursor.lastrowid

    def get_latest_system_status(self) -> Optional[Dict[str, Any]]:
        conn = self.connection.connect()
        try:
            row = conn.execute(
                "SELECT * FROM system_status ORDER BY timestamp DESC, id DESC LIMIT 1"
            ).fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    # ---------------------------------------------------------
    # 8. Reconstructed Observation Record (Section 27)
    # ---------------------------------------------------------
    def get_reconstructed_observation(
        self,
        decision_id: Optional[str] = None,
        hazard_event_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Reconstruct a complete observation combining mission, location, time, telemetry, vision, and decision."""
        conn = self.connection.connect()
        try:
            if decision_id:
                hazard_row = conn.execute(
                    "SELECT * FROM hazard_events WHERE decision_id = ? LIMIT 1",
                    (decision_id,),
                ).fetchone()
            elif hazard_event_id:
                hazard_row = conn.execute(
                    "SELECT * FROM hazard_events WHERE id = ? LIMIT 1",
                    (hazard_event_id,),
                ).fetchone()
            else:
                hazard_row = conn.execute(
                    "SELECT * FROM hazard_events ORDER BY id DESC LIMIT 1"
                ).fetchone()

            if not hazard_row:
                return None

            hazard = dict(hazard_row)
            ts = hazard["timestamp"]

            # Associated mission
            mission = None
            if hazard.get("mission_id"):
                m_row = conn.execute("SELECT * FROM missions WHERE id = ?", (hazard["mission_id"],)).fetchone()
                if m_row:
                    mission = dict(m_row)

            # Associated location
            location = None
            if hazard.get("location_id"):
                loc_row = conn.execute("SELECT * FROM locations WHERE id = ?", (hazard["location_id"],)).fetchone()
                if loc_row:
                    location = dict(loc_row)

            # Contemporaneous sensor readings
            sensor_row = conn.execute(
                """
                SELECT * FROM sensor_readings
                ORDER BY ABS(strftime('%s', timestamp) - strftime('%s', ?)) ASC, id DESC
                LIMIT 1
                """,
                (ts,),
            ).fetchone()
            sensors = dict(sensor_row) if sensor_row else None

            # Contemporaneous vision detection / image
            vision_row = conn.execute(
                """
                SELECT * FROM vision_detections
                ORDER BY ABS(strftime('%s', timestamp) - strftime('%s', ?)) ASC, id DESC
                LIMIT 1
                """,
                (ts,),
            ).fetchone()
            vision = dict(vision_row) if vision_row else None

            # Associated logs
            logs = conn.execute(
                """
                SELECT * FROM mission_logs
                ORDER BY ABS(strftime('%s', timestamp) - strftime('%s', ?)) ASC, id DESC
                LIMIT 3
                """,
                (ts,),
            ).fetchall()

            return {
                "timestamp": ts,
                "decision_id": hazard.get("decision_id"),
                "mission": mission,
                "location": location,
                "hazard_event": hazard,
                "sensor_reading": sensors,
                "vision_detection": vision,
                "image_path": vision.get("image_path") if vision else None,
                "logs": [dict(l) for l in logs],
            }
        finally:
            conn.close()


__all__ = ["Repository"]
