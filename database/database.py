from __future__ import annotations

import sqlite3
from typing import Any, Dict, List, Optional

from database.connection import DatabaseConnection
from database.migrations import run_migrations
from database.repository import Repository


class SQLiteDatabase:
    """Primary local SQLite database manager for Mining Rover.
    
    Provides offline-first persistence across all telemetry, vision,
    decisions, missions, locations, and synchronization queues.
    """

    def __init__(self, path: Optional[str] = None) -> None:
        self.connection = DatabaseConnection(path=path)
        self.path = self.connection.path
        self.repo = Repository(self.connection)

    def connect(self) -> sqlite3.Connection:
        """Return a configured connection directly."""
        return self.connection.connect()

    def initialize(self) -> None:
        """Run idempotent migrations and initialize all tables and indexes."""
        with self.connection.transaction() as conn:
            run_migrations(conn)

    # ---------------------------------------------------------
    # Forwarded Sensor Telemetry Methods
    # ---------------------------------------------------------
    def insert_sensor_reading(
        self,
        timestamp: str,
        device_id: str = "mining_rover_01",
        sensor_type: Optional[str] = None,
        value: Optional[float] = None,
        unit: Optional[str] = None,
        valid: Optional[bool] = None,
        source: str = "simulator",
        synced: Optional[bool] = None,
        temperature_c: Optional[float] = None,
        humidity_percent: Optional[float] = None,
        pressure_hpa: Optional[float] = None,
        mq4: Optional[float] = None,
        mq135: Optional[float] = None,
        sequence_number: Optional[int] = None,
        sync_status: str = "pending",
    ) -> Optional[int]:
        return self.repo.insert_sensor_reading(
            timestamp=timestamp,
            device_id=device_id,
            temperature_c=temperature_c,
            humidity_percent=humidity_percent,
            pressure_hpa=pressure_hpa,
            mq4=mq4,
            mq135=mq135,
            sequence_number=sequence_number,
            source=source,
            sync_status=sync_status,
            sensor_type=sensor_type,
            value=value,
            unit=unit,
            valid=valid,
            synced=synced,
        )

    def get_latest_sensor_readings(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.repo.get_latest_sensor_readings(limit=limit)

    def get_sensor_history(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        return self.repo.get_sensor_history(start_time=start_time, end_time=end_time, limit=limit)

    # ---------------------------------------------------------
    # Forwarded Vision Detection Methods
    # ---------------------------------------------------------
    def insert_vision_detection(
        self,
        timestamp: str,
        device_id: str = "mining_rover_01",
        class_name: str = "fire",
        confidence: float = 0.0,
        x_center: Optional[float] = None,
        y_center: Optional[float] = None,
        width: Optional[float] = None,
        height: Optional[float] = None,
        source: str = "yolo",
        synced: Optional[bool] = None,
        bbox_x1: Optional[float] = None,
        bbox_y1: Optional[float] = None,
        bbox_x2: Optional[float] = None,
        bbox_y2: Optional[float] = None,
        image_path: Optional[str] = None,
        mission_id: Optional[int] = None,
        location_id: Optional[int] = None,
        sync_status: str = "pending",
    ) -> Optional[int]:
        return self.repo.insert_vision_detection(
            timestamp=timestamp,
            class_name=class_name,
            confidence=confidence,
            bbox_x1=bbox_x1,
            bbox_y1=bbox_y1,
            bbox_x2=bbox_x2,
            bbox_y2=bbox_y2,
            image_path=image_path,
            source=source,
            mission_id=mission_id,
            location_id=location_id,
            sync_status=sync_status,
            device_id=device_id,
            x_center=x_center,
            y_center=y_center,
            width=width,
            height=height,
            synced=synced,
        )

    def get_latest_detections(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.repo.get_latest_detections(limit=limit)

    get_recent_detections = get_latest_detections

    # ---------------------------------------------------------
    # Forwarded Hazard Event Methods
    # ---------------------------------------------------------
    def insert_hazard_event(
        self,
        timestamp: str,
        device_id: str = "mining_rover_01",
        hazard: Optional[str] = None,
        severity: Optional[str] = None,
        confidence: Optional[float] = None,
        sources: Optional[str] = None,
        message: Optional[str] = None,
        recommended_action: Optional[str] = None,
        synced: Optional[bool] = None,
        hazard_type: Optional[str] = None,
        decision_id: Optional[str] = None,
        mission_id: Optional[int] = None,
        location_id: Optional[int] = None,
        reasons_json: Optional[str] = None,
        sensor_evidence_json: Optional[str] = None,
        vision_evidence_json: Optional[str] = None,
        source: str = "sensor_vision_fusion",
        sync_status: str = "pending",
    ) -> Optional[int]:
        return self.repo.insert_hazard_event(
            timestamp=timestamp,
            hazard_type=hazard_type,
            severity=severity,
            confidence=confidence,
            decision_id=decision_id,
            mission_id=mission_id,
            location_id=location_id,
            reasons_json=reasons_json,
            sensor_evidence_json=sensor_evidence_json,
            vision_evidence_json=vision_evidence_json,
            source=source,
            sync_status=sync_status,
            device_id=device_id,
            hazard=hazard,
            sources=sources,
            message=message,
            recommended_action=recommended_action,
            synced=synced,
        )

    def get_latest_hazard(self) -> Optional[Dict[str, Any]]:
        return self.repo.get_latest_hazard()

    def get_recent_hazards(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.repo.get_recent_hazards(limit=limit)

    def get_hazard_history(
        self,
        mission_id: Optional[int] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        return self.repo.get_hazard_history(
            mission_id=mission_id, start_time=start_time, end_time=end_time, limit=limit
        )

    # ---------------------------------------------------------
    # Forwarded Mission Management Methods
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
        return self.repo.create_mission(
            mission_code=mission_code,
            status=status,
            started_at=started_at,
            notes=notes,
            start_location_json=start_location_json,
            end_location_json=end_location_json,
        )

    def start_mission(self, mission_code_or_id: str | int) -> bool:
        return self.repo.start_mission(mission_code_or_id)

    def end_mission(self, mission_code_or_id: str | int, status: str = "COMPLETED") -> bool:
        return self.repo.end_mission(mission_code_or_id, status=status)

    def get_active_mission(self) -> Optional[Dict[str, Any]]:
        return self.repo.get_active_mission()

    def get_mission(self, mission_id: Optional[int] = None, mission_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.repo.get_mission(mission_id=mission_id, mission_code=mission_code)

    def get_mission_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self.repo.get_mission_history(limit=limit)

    # ---------------------------------------------------------
    # Forwarded Mission Logs & Location Methods
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
        return self.repo.insert_mission_log(
            level=level,
            event_type=event_type,
            message=message,
            mission_id=mission_id,
            timestamp=timestamp,
            metadata_json=metadata_json,
        )

    def get_mission_logs(self, mission_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
        return self.repo.get_mission_logs(mission_id=mission_id, limit=limit)

    def create_location(
        self,
        location_type: str = "LOCAL_POSITION",
        x: Optional[float] = None,
        y: Optional[float] = None,
        z: Optional[float] = None,
        label: Optional[str] = None,
        mission_id: Optional[int] = None,
    ) -> int:
        return self.repo.create_location(
            location_type=location_type, x=x, y=y, z=z, label=label, mission_id=mission_id
        )

    def get_location(self, location_id: int) -> Optional[Dict[str, Any]]:
        return self.repo.get_location(location_id=location_id)

    def get_reconstructed_observation(
        self,
        decision_id: Optional[str] = None,
        hazard_event_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        return self.repo.get_reconstructed_observation(
            decision_id=decision_id, hazard_event_id=hazard_event_id
        )

    # ---------------------------------------------------------
    # Forwarded System Status Methods
    # ---------------------------------------------------------
    def update_system_status(
        self,
        timestamp: str,
        device_id: str = "mining_rover_01",
        network_status: str = "OFFLINE",
        battery_level: Optional[float] = None,
        system_status: str = "RUNNING",
        last_sensor_update: Optional[str] = None,
        last_vision_update: Optional[str] = None,
        last_decision_update: Optional[str] = None,
        rover_status: str = "RUNNING",
        camera_status: str = "OK",
        sensor_status: str = "OK",
        database_status: str = "OK",
        sync_status: str = "pending",
        storage_available_mb: Optional[float] = None,
        cpu_temperature_c: Optional[float] = None,
    ) -> Optional[int]:
        return self.repo.update_system_status(
            timestamp=timestamp,
            rover_status=rover_status,
            camera_status=camera_status,
            sensor_status=sensor_status,
            database_status=database_status,
            network_status=network_status,
            sync_status=sync_status,
            storage_available_mb=storage_available_mb,
            cpu_temperature_c=cpu_temperature_c,
            device_id=device_id,
            battery_level=battery_level,
            system_status=system_status,
            last_sensor_update=last_sensor_update,
            last_vision_update=last_vision_update,
            last_decision_update=last_decision_update,
        )

    def get_latest_system_status(self) -> Optional[Dict[str, Any]]:
        return self.repo.get_latest_system_status()

    # ---------------------------------------------------------
    # Sync Queue Integration Methods (Preserved)
    # ---------------------------------------------------------
    def get_unsynced_records(self) -> List[Dict[str, Any]]:
        conn = self.connect()
        try:
            rows = conn.execute(
                """
                SELECT 'sensor_readings' AS table_name, id, timestamp, device_id, synced
                FROM sensor_readings
                WHERE synced = 0 OR sync_status = 'pending'
                UNION ALL
                SELECT 'vision_detections' AS table_name, id, timestamp, device_id, synced
                FROM vision_detections
                WHERE synced = 0 OR sync_status = 'pending'
                UNION ALL
                SELECT 'hazard_events' AS table_name, id, timestamp, device_id, synced
                FROM hazard_events
                WHERE synced = 0 OR sync_status = 'pending'
                ORDER BY timestamp DESC, id DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def mark_record_synced(self, table_name: str, record_id: int) -> None:
        allowed = {"sensor_readings", "vision_detections", "hazard_events", "missions"}
        if table_name not in allowed:
            raise ValueError(f"Unsupported table: {table_name}")

        conn = self.connect()
        try:
            conn.execute(
                f"UPDATE {table_name} SET synced = 1, sync_status = 'synced' WHERE id = ?",
                (record_id,),
            )
            conn.commit()
        finally:
            conn.close()

    def mark_records_synced_batch(self, records: List[Dict[str, Any]]) -> int:
        allowed = {"sensor_readings", "vision_detections", "hazard_events", "missions"}
        conn = self.connect()
        count = 0
        try:
            for item in records:
                table_name = item.get("table_name")
                record_id = item.get("id") or item.get("record_id")
                if table_name in allowed and record_id is not None:
                    conn.execute(
                        f"UPDATE {table_name} SET synced = 1, sync_status = 'synced' WHERE id = ?",
                        (record_id,),
                    )
                    count += 1
            conn.commit()
            return count
        finally:
            conn.close()

    def get_pending_sync_records_detailed(self, limit: int = 50) -> List[Dict[str, Any]]:
        conn = self.connect()
        results: List[Dict[str, Any]] = []
        per_table = max(1, limit // 3)
        try:
            sensors = conn.execute(
                """
                SELECT 'sensor_readings' AS table_name, id, timestamp, device_id, sensor_type, value, unit, valid, source, created_at
                FROM sensor_readings
                WHERE synced = 0 OR sync_status = 'pending'
                ORDER BY id ASC
                LIMIT ?
                """,
                (per_table,),
            ).fetchall()
            for r in sensors:
                d = dict(r)
                d["unique_id"] = f"sensor_{d['id']}_{d['timestamp']}"
                results.append(d)

            visions = conn.execute(
                """
                SELECT 'vision_detections' AS table_name, id, timestamp, device_id, class_name, confidence, x_center, y_center, width, height, source, created_at
                FROM vision_detections
                WHERE synced = 0 OR sync_status = 'pending'
                ORDER BY id ASC
                LIMIT ?
                """,
                (per_table,),
            ).fetchall()
            for r in visions:
                d = dict(r)
                d["unique_id"] = f"vision_{d['id']}_{d['timestamp']}"
                results.append(d)

            hazards = conn.execute(
                """
                SELECT 'hazard_events' AS table_name, id, timestamp, device_id, hazard, severity, confidence, sources, message, recommended_action, created_at
                FROM hazard_events
                WHERE synced = 0 OR sync_status = 'pending'
                ORDER BY id ASC
                LIMIT ?
                """,
                (per_table,),
            ).fetchall()
            for r in hazards:
                d = dict(r)
                d["unique_id"] = f"hazard_{d['id']}_{d['timestamp']}"
                results.append(d)

            return results
        finally:
            conn.close()

    def get_sync_statistics(self) -> Dict[str, int]:
        conn = self.connect()
        try:
            pending_res = conn.execute(
                """
                SELECT
                    (SELECT COUNT(*) FROM sensor_readings WHERE synced = 0 OR sync_status = 'pending') +
                    (SELECT COUNT(*) FROM vision_detections WHERE synced = 0 OR sync_status = 'pending') +
                    (SELECT COUNT(*) FROM hazard_events WHERE synced = 0 OR sync_status = 'pending') AS pending_count,
                    (SELECT COUNT(*) FROM sensor_readings WHERE synced = 1 OR sync_status = 'synced') +
                    (SELECT COUNT(*) FROM vision_detections WHERE synced = 1 OR sync_status = 'synced') +
                    (SELECT COUNT(*) FROM hazard_events WHERE synced = 1 OR sync_status = 'synced') AS synced_count,
                    (SELECT COUNT(*) FROM sensor_readings) +
                    (SELECT COUNT(*) FROM vision_detections) +
                    (SELECT COUNT(*) FROM hazard_events) AS total_count
                """
            ).fetchone()
            return {
                "pending_count": pending_res["pending_count"] if pending_res else 0,
                "synced_count": pending_res["synced_count"] if pending_res else 0,
                "total_count": pending_res["total_count"] if pending_res else 0,
            }
        finally:
            conn.close()


__all__ = ["SQLiteDatabase"]
