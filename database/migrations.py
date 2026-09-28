from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone
from typing import Set

logger = logging.getLogger("database.migrations")


def get_existing_columns(conn: sqlite3.Connection, table_name: str) -> Set[str]:
    """Retrieve column names for an existing table."""
    try:
        cursor = conn.execute(f"PRAGMA table_info({table_name});")
        return {row[1] for row in cursor.fetchall()}
    except Exception:
        return set()


def add_column_if_missing(
    conn: sqlite3.Connection, table_name: str, column_name: str, column_def: str
) -> None:
    """Safely append a column to a table if it does not already exist."""
    cols = get_existing_columns(conn, table_name)
    if column_name not in cols:
        logger.debug("Migrating %s: adding column %s", table_name, column_name)
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_def};")


def run_migrations(conn: sqlite3.Connection) -> None:
    """Run all schema definitions and upgrades idempotently."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT NOT NULL
        );
        """
    )

    # 1. sensor_readings
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sensor_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            temperature_c REAL,
            humidity_percent REAL,
            pressure_hpa REAL,
            mq4 REAL,
            mq135 REAL,
            sequence_number INTEGER,
            source TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            sync_status TEXT DEFAULT 'pending',
            -- Legacy columns for complete backward compatibility
            sensor_type TEXT DEFAULT 'temperature',
            value REAL DEFAULT 0.0,
            unit TEXT DEFAULT '',
            valid INTEGER DEFAULT 1,
            synced INTEGER DEFAULT 0
        );
        """
    )
    add_column_if_missing(conn, "sensor_readings", "temperature_c", "REAL")
    add_column_if_missing(conn, "sensor_readings", "humidity_percent", "REAL")
    add_column_if_missing(conn, "sensor_readings", "pressure_hpa", "REAL")
    add_column_if_missing(conn, "sensor_readings", "mq4", "REAL")
    add_column_if_missing(conn, "sensor_readings", "mq135", "REAL")
    add_column_if_missing(conn, "sensor_readings", "sequence_number", "INTEGER")
    add_column_if_missing(conn, "sensor_readings", "source", "TEXT DEFAULT 'simulator'")
    add_column_if_missing(conn, "sensor_readings", "sync_status", "TEXT DEFAULT 'pending'")
    add_column_if_missing(conn, "sensor_readings", "sensor_type", "TEXT DEFAULT 'temperature'")
    add_column_if_missing(conn, "sensor_readings", "value", "REAL DEFAULT 0.0")
    add_column_if_missing(conn, "sensor_readings", "unit", "TEXT DEFAULT ''")
    add_column_if_missing(conn, "sensor_readings", "valid", "INTEGER DEFAULT 1")
    add_column_if_missing(conn, "sensor_readings", "synced", "INTEGER DEFAULT 0")

    # 2. vision_detections
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vision_detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            class_name TEXT NOT NULL,
            confidence REAL NOT NULL,
            bbox_x1 REAL,
            bbox_y1 REAL,
            bbox_x2 REAL,
            bbox_y2 REAL,
            image_path TEXT,
            source TEXT DEFAULT 'yolo',
            mission_id INTEGER,
            location_id INTEGER,
            sync_status TEXT DEFAULT 'pending',
            device_id TEXT DEFAULT 'mining_rover_01',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            -- Legacy columns
            x_center REAL,
            y_center REAL,
            width REAL,
            height REAL,
            synced INTEGER DEFAULT 0
        );
        """
    )
    add_column_if_missing(conn, "vision_detections", "bbox_x1", "REAL")
    add_column_if_missing(conn, "vision_detections", "bbox_y1", "REAL")
    add_column_if_missing(conn, "vision_detections", "bbox_x2", "REAL")
    add_column_if_missing(conn, "vision_detections", "bbox_y2", "REAL")
    add_column_if_missing(conn, "vision_detections", "image_path", "TEXT")
    add_column_if_missing(conn, "vision_detections", "source", "TEXT DEFAULT 'yolo'")
    add_column_if_missing(conn, "vision_detections", "mission_id", "INTEGER")
    add_column_if_missing(conn, "vision_detections", "location_id", "INTEGER")
    add_column_if_missing(conn, "vision_detections", "sync_status", "TEXT DEFAULT 'pending'")
    add_column_if_missing(conn, "vision_detections", "device_id", "TEXT DEFAULT 'mining_rover_01'")
    add_column_if_missing(conn, "vision_detections", "x_center", "REAL")
    add_column_if_missing(conn, "vision_detections", "y_center", "REAL")
    add_column_if_missing(conn, "vision_detections", "width", "REAL")
    add_column_if_missing(conn, "vision_detections", "height", "REAL")
    add_column_if_missing(conn, "vision_detections", "synced", "INTEGER DEFAULT 0")

    # 3. hazard_events
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS hazard_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            decision_id TEXT,
            timestamp TEXT NOT NULL,
            mission_id INTEGER,
            location_id INTEGER,
            hazard_type TEXT NOT NULL DEFAULT 'none',
            severity TEXT NOT NULL DEFAULT 'LOW',
            confidence REAL NOT NULL DEFAULT 0.0,
            reasons_json TEXT,
            sensor_evidence_json TEXT,
            vision_evidence_json TEXT,
            source TEXT DEFAULT 'sensor_vision_fusion',
            sync_status TEXT DEFAULT 'pending',
            device_id TEXT DEFAULT 'mining_rover_01',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            -- Legacy columns
            hazard TEXT,
            sources TEXT,
            message TEXT,
            recommended_action TEXT,
            synced INTEGER DEFAULT 0
        );
        """
    )
    add_column_if_missing(conn, "hazard_events", "decision_id", "TEXT")
    add_column_if_missing(conn, "hazard_events", "mission_id", "INTEGER")
    add_column_if_missing(conn, "hazard_events", "location_id", "INTEGER")
    add_column_if_missing(conn, "hazard_events", "hazard_type", "TEXT DEFAULT 'none'")
    add_column_if_missing(conn, "hazard_events", "severity", "TEXT DEFAULT 'LOW'")
    add_column_if_missing(conn, "hazard_events", "confidence", "REAL DEFAULT 0.0")
    add_column_if_missing(conn, "hazard_events", "reasons_json", "TEXT")
    add_column_if_missing(conn, "hazard_events", "sensor_evidence_json", "TEXT")
    add_column_if_missing(conn, "hazard_events", "vision_evidence_json", "TEXT")
    add_column_if_missing(conn, "hazard_events", "source", "TEXT DEFAULT 'sensor_vision_fusion'")
    add_column_if_missing(conn, "hazard_events", "sync_status", "TEXT DEFAULT 'pending'")
    add_column_if_missing(conn, "hazard_events", "device_id", "TEXT DEFAULT 'mining_rover_01'")
    add_column_if_missing(conn, "hazard_events", "hazard", "TEXT")
    add_column_if_missing(conn, "hazard_events", "sources", "TEXT")
    add_column_if_missing(conn, "hazard_events", "message", "TEXT")
    add_column_if_missing(conn, "hazard_events", "recommended_action", "TEXT")
    add_column_if_missing(conn, "hazard_events", "synced", "INTEGER DEFAULT 0")

    # 4. missions
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS missions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_code TEXT UNIQUE NOT NULL,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            ended_at TEXT,
            start_location_json TEXT,
            end_location_json TEXT,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            sync_status TEXT DEFAULT 'pending'
        );
        """
    )

    # 5. locations
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id INTEGER,
            location_type TEXT,
            x REAL,
            y REAL,
            z REAL,
            label TEXT,
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );
        """
    )

    # 6. mission_logs
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS mission_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mission_id INTEGER,
            timestamp TEXT NOT NULL,
            level TEXT NOT NULL,
            event_type TEXT NOT NULL,
            message TEXT NOT NULL,
            metadata_json TEXT
        );
        """
    )

    # 7. system_status
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS system_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            rover_status TEXT DEFAULT 'RUNNING',
            camera_status TEXT DEFAULT 'OK',
            sensor_status TEXT DEFAULT 'OK',
            database_status TEXT DEFAULT 'OK',
            network_status TEXT DEFAULT 'OFFLINE',
            sync_status TEXT DEFAULT 'pending',
            storage_available_mb REAL,
            cpu_temperature_c REAL,
            device_id TEXT DEFAULT 'mining_rover_01',
            created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
            -- Legacy columns
            battery_level REAL,
            system_status TEXT,
            last_sensor_update TEXT,
            last_vision_update TEXT,
            last_decision_update TEXT
        );
        """
    )
    add_column_if_missing(conn, "system_status", "rover_status", "TEXT DEFAULT 'RUNNING'")
    add_column_if_missing(conn, "system_status", "camera_status", "TEXT DEFAULT 'OK'")
    add_column_if_missing(conn, "system_status", "sensor_status", "TEXT DEFAULT 'OK'")
    add_column_if_missing(conn, "system_status", "database_status", "TEXT DEFAULT 'OK'")
    add_column_if_missing(conn, "system_status", "storage_available_mb", "REAL")
    add_column_if_missing(conn, "system_status", "cpu_temperature_c", "REAL")

    # Indexes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sensor_timestamp ON sensor_readings (timestamp);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sensor_device_timestamp ON sensor_readings (device_id, timestamp);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sensor_sync_status ON sensor_readings (sync_status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp ON sensor_readings (timestamp);")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_vision_detections_timestamp ON vision_detections (timestamp);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_vision_sync_status ON vision_detections (sync_status);")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_hazard_events_timestamp ON hazard_events (timestamp);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hazard_decision_id ON hazard_events (decision_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hazard_sync_status ON hazard_events (sync_status);")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_missions_code ON missions (mission_code);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_missions_status ON missions (status);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_locations_mission_id ON locations (mission_id);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_mission_logs_mission_id ON mission_logs (mission_id);")

    # Record migration version 1
    now_str = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT OR IGNORE INTO schema_migrations (version, applied_at, description)
        VALUES (1, ?, 'Phase 3 core tables, indexes, and backward-compatible fields')
        """,
        (now_str,),
    )


__all__ = ["run_migrations"]
