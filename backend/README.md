# Phase 4 — FastAPI Backend & Local API Layer

The FastAPI backend serves as the **offline-first local API gateway** running directly on the Raspberry Pi 4 (or local workstation) between the rover's core modules (Sensor Acquisition, YOLO Vision, Decision Engine, and SQLite) and the operator dashboard.

---

## 1. System Architecture

```text
ESP32 Sensor Node
        │
        ▼
Sensor Data Service
        │
        ▼
SQLite ◄──────── YOLO Vision
  │                 │
  │                 ▼
  │          Decision Engine
  │                 │
  └─────────────────┘
        │
        ▼
   FastAPI Backend
        │
        ├── /api/health
        ├── /api/sensors/latest & /history
        ├── /api/vision/latest, /history, /camera/stream
        ├── /api/decisions/latest & /history
        ├── /api/mission/current & /missions
        ├── /api/logs
        ├── /api/locations & /{location_id}
        ├── /api/observations/latest
        ├── /api/system/status
        └── /api/sync/status & /trigger
                │
                ▼
      Dashboard (React / Vite)
```

### Architectural Separation
* **Sensor Service**: Collects telemetry.
* **YOLO Vision**: Observes hazards and optical landmarks.
* **Decision Engine**: Interprets multi-modal data and arbitrates hazards.
* **SQLite Database**: Remembers local state (Source of Truth).
* **FastAPI Backend**: Exposes clean REST & MJPEG streaming endpoints.
* **Dashboard**: Displays UI telemetry.
* **Sync Service**: Transfers pending records when connectivity is available.
* **Safety Boundary**: FastAPI **never controls motors, drive, or movement**.

---

## 2. Endpoints Overview

| Endpoint | Method | Description |
|---|---|---|
| `/` | `GET` | API identity, status, and offline mode indicator. |
| `/api/health` | `GET` | Offline health check verifying SQLite connectivity. |
| `/api/sensors/latest` | `GET` | Current telemetry for temperature, humidity, pressure, MQ-4, MQ-135. |
| `/api/sensors/history` | `GET` | Historical telemetry records from SQLite with pagination & time filters. |
| `/api/vision/latest` | `GET` | Latest YOLO detections with bounding boxes and confidence. |
| `/api/vision/history` | `GET` | Historical YOLO detections from SQLite. |
| `/api/vision/camera/stream` | `GET` | Live MJPEG camera video stream (fails gracefully with 503 if unavailable). |
| `/api/decisions/latest` | `GET` | Latest Decision Engine arbitration result without recalculation. |
| `/api/decisions/history` | `GET` | Historical hazard decisions filtered by severity or hazard type. |
| `/api/mission/current` | `GET` | Active exploration mission (returns `{"mission": null}` if none). |
| `/api/missions` | `GET` | List of historical missions with status and time filtering. |
| `/api/logs` | `GET` | Mission and telemetry activity logs with level and event filters. |
| `/api/locations` | `GET` | Stored mine marker locations and coordinates. |
| `/api/locations/{id}` | `GET` | Location marker details and associated hazard observations. |
| `/api/observations/latest` | `GET` | Reconstructed observation correlating telemetry, vision, decision, location, and mission. |
| `/api/system/status` | `GET` | Rover hardware/software status (CPU temp, disk storage, database health). |
| `/api/sync/status` | `GET` | Network reachability and pending synchronization records count. |
| `/api/sync/trigger` | `POST` | Non-blocking trigger for immediate synchronization cycle. |

---

## 3. Configuration & Raspberry Pi 4 Compatibility

The backend uses standard environment variables and `pathlib.Path`:

* `ROVER_BACKEND_HOST`: Host interface (default `0.0.0.0`).
* `ROVER_BACKEND_PORT`: Port number (default `8000`).
* `ROVER_DB_PATH`: Path to SQLite database (default `database/mining_rover.db`).
* `ROVER_SYNC_URL`: Remote synchronization endpoint.
* `ROVER_ALLOWED_ORIGINS`: Allowed CORS origins (e.g. `*` or dashboard IP).

---

## 4. Running the Backend

### Local Run
```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

### Full Rover Launch
```bash
python start_rover.py
```

### Running Test Suite
```bash
python -m pytest tests/backend/test_phase4_api.py
```
