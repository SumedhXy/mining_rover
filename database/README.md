# Phase 3 — Mining Rover Local Database & Mission Data Storage

## 1. Objective & Design Principles

The local database layer makes the **Raspberry Pi 4 the local source of truth**. Every observation, sensor reading, visual detection, decision assessment, and mission event is stored locally in SQLite first.

### Core Principles
- **100% Offline-First**: Internet or remote network connectivity is never required to store, query, or manage rover data.
- **Local Source of Truth**: SQLite persists all rover state across reboots. Remote servers are only synchronized downstream when connectivity is available.
- **Reconstructable Observations**: Every mission observation can be reconstructed end-to-end:
  $$\text{Mission} \longrightarrow \text{Location} \longrightarrow \text{Time} \longrightarrow \text{Sensors} \longrightarrow \text{YOLO Detection} \longrightarrow \text{Hazard Assessment} \longrightarrow \text{Logs}$$
- **Atomic Transactions & WAL Mode**: Uses SQLite Write-Ahead Logging (`PRAGMA journal_mode=WAL`) and short, transaction-safe commits to protect against unexpected power outages.
- **Zero Heavy Dependencies**: Uses standard Python `sqlite3`, perfectly suited for low-overhead operation on the Raspberry Pi 4.

---

## 2. System Architecture

```text
       ESP32 Sensor Node
               │
               ▼
       Sensor Data Service
               │
       ┌───────┴───────┐
       ▼               ▼
  Sensor Reading   YOLO Vision
       │               │
       └───────┬───────┘
               ▼
        Decision Engine
               │
               ▼
        Database Service (Repository)
               │
               ▼
         SQLite (mining_rover.db)
               │
       ┌───────┴───────┐
       ▼               ▼
    FastAPI        Sync Queue
       │               │
       ▼               ▼
   Dashboard     Remote Server (when online)
```

The database operates independently of FastAPI, the Decision Engine, and the remote server.

---

## 3. Database File & Storage Organization

- **Database File**: [`database/mining_rover.db`](file:///c:/Users/sumed/Mining_Rover_software/database/mining_rover.db)
- **Image Storage**: Large image binaries are kept on the local filesystem outside SQLite:
  ```text
  data/
  └── missions/
      └── mission_001/
          ├── images/
          │   ├── img_000001.jpg
          │   └── img_000002.jpg
          └── exports/
  ```
  SQLite stores the relative file path in `image_path` (e.g. `data/missions/mission_001/images/img_000001.jpg`).

---

## 4. Database Schema & Tables

### 4.1 `sensor_readings`
Stores continuous environmental telemetry from Phase 1.
```sql
CREATE TABLE sensor_readings (
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
    sync_status TEXT DEFAULT 'pending'
);
```

### 4.2 `vision_detections`
Stores YOLO bounding boxes and image references.
```sql
CREATE TABLE vision_detections (
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
    sync_status TEXT DEFAULT 'pending'
);
```

### 4.3 `hazard_events`
Stores Decision Engine outputs and explainability reasons.
```sql
CREATE TABLE hazard_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    decision_id TEXT UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    mission_id INTEGER,
    location_id INTEGER,
    hazard_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence REAL NOT NULL,
    reasons_json TEXT,
    sensor_evidence_json TEXT,
    vision_evidence_json TEXT,
    source TEXT DEFAULT 'sensor_vision_fusion',
    sync_status TEXT DEFAULT 'pending'
);
```

### 4.4 `missions`
Tracks rover exploration runs.
```sql
CREATE TABLE missions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_code TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL, -- PLANNED, ACTIVE, PAUSED, COMPLETED, ABORTED
    started_at TEXT NOT NULL,
    ended_at TEXT,
    start_location_json TEXT,
    end_location_json TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    sync_status TEXT DEFAULT 'pending'
);
```

### 4.5 `locations`
Records observation points inside the mine (independent of GPS).
```sql
CREATE TABLE locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id INTEGER,
    location_type TEXT, -- LOCAL_POSITION, MINE_MARKER, RFID_TAG, WAYPOINT, UNKNOWN
    x REAL,
    y REAL,
    z REAL,
    label TEXT,
    created_at TEXT NOT NULL
);
```

### 4.6 `mission_logs`
Chronological operational and hazard audit logs.
```sql
CREATE TABLE mission_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mission_id INTEGER,
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL, -- INFO, WARNING, HAZARD, ERROR, CRITICAL
    event_type TEXT NOT NULL, -- MISSION_STARTED, GAS_DETECTED, etc.
    message TEXT NOT NULL,
    metadata_json TEXT
);
```

### 4.7 `system_status`
Health and diagnostic telemetry.
```sql
CREATE TABLE system_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    rover_status TEXT,
    camera_status TEXT,
    sensor_status TEXT,
    database_status TEXT,
    network_status TEXT,
    sync_status TEXT,
    storage_available_mb REAL,
    cpu_temperature_c REAL
);
```

---

## 5. Indexes for Query Performance

The database maintains indexed lookups for dashboard and mission history queries:
- `idx_sensor_timestamp`: Telemetry lookups by time
- `idx_sensor_device_timestamp`: Device-specific telemetry ordering
- `idx_sensor_sync_status`: Sync queue querying
- `idx_vision_detections_timestamp`: Detection chronology
- `idx_hazard_events_timestamp`: Hazard event chronology
- `idx_hazard_decision_id`: Fast lookup by unique decision ID
- `idx_missions_code`: Quick mission lookup
- `idx_missions_status`: Active mission querying
- `idx_mission_logs_mission_id`: Mission log aggregation
- `idx_locations_mission_id`: Spatial mapping per mission

---

## 6. Reconstructed Observation Record

To fulfill the mining exploration requirement, the database provides `get_reconstructed_observation()`:

```python
observation = db.get_reconstructed_observation(decision_id="dec_001")
```

Example result:
```json
{
  "timestamp": "2026-09-28T11:35:10Z",
  "decision_id": "dec_001",
  "mission": {
    "mission_code": "EXP-2026-01",
    "status": "ACTIVE"
  },
  "location": {
    "label": "MINE-SECTOR-A-POINT-04",
    "x": 12.5,
    "y": 45.0,
    "z": -120.0
  },
  "hazard_event": {
    "hazard_type": "fire",
    "severity": "HIGH",
    "confidence": 0.87
  },
  "sensor_reading": {
    "temperature_c": 58.2,
    "pressure_hpa": 997.4,
    "mq4": 0.22,
    "mq135": 0.71
  },
  "vision_detection": {
    "class_name": "fire",
    "confidence": 0.85
  },
  "image_path": "data/missions/mission_001/images/img_000031.jpg",
  "logs": [
    {"level": "HAZARD", "event_type": "FIRE_DETECTED", "message": "Fire confirmed by YOLO + temp"}
  ]
}
```

---

## 7. Migration & Idempotent Initialization

Automatic migration and initialization are managed via [`database/migrations.py`](file:///c:/Users/sumed/Mining_Rover_software/database/migrations.py):
- Automatically creates parent directories.
- Applies table schemas and alters existing tables if new columns are missing.
- Idempotent: Running `db.initialize()` multiple times is safe and fast.

---

## 8. Unit & Integration Testing

All 24 required database capabilities are verified:
```bash
python -m pytest tests/database/
```

Test coverage includes:
1. `test_database_initialization`: WAL mode and timeout verification.
2. `test_table_creation`: Verifies all 8 tables and indexes exist.
3. `test_sensor_insertion`: Normalized Phase 1 telemetry insertion.
4. `test_sensor_retrieval`: Telemetry retrieval with expected values.
5. `test_vision_insertion`: YOLO bounding box and image path insertion.
6. `test_vision_retrieval`: Vision retrieval by class and confidence.
7. `test_hazard_insertion`: Explainable hazard event persistence.
8. `test_hazard_retrieval`: Explainable reasons retrieval.
9. `test_mission_creation`: Mission lifecycle creation.
10. `test_active_mission_retrieval`: Active mission querying.
11. `test_mission_completion`: Mission conclusion and timestamps.
12. `test_mission_logs`: Multi-level audit log recording.
13. `test_location_records`: Mine 3D coordinates and RFID/marker tagging.
14. `test_image_path_association`: External filesystem image reference linking.
15. `test_system_status`: Hardware diagnostics and CPU temperature.
16. `test_sync_status`: Sync queue status transitions and stats.
17. `test_duplicate_protection`: Unique constraint enforcement.
18. `test_restart_persistence`: Data survival across process restart.
19. `test_offline_operation`: Zero network dependencies.
20. `test_transaction_rollback`: Atomic rollback on mid-transaction error.
21. `test_timestamp_queries`: Time-bounded historical filtering.
22. `test_latest_value_queries`: Fast indexed latest-value retrieval.
23. `test_historical_queries`: Bounded limit pagination.
24. `test_migration_safety`: Sequential idempotent initialization runs.
