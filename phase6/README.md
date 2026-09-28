# Phase 6 — Deployment + Offline/Online Sync

## 1. Objective

Deploy the complete Mining Rover software as an **offline-first system**.

The rover must continue operating when there is:

- No internet
- No connection to a remote server
- Intermittent network connectivity

Internet/network connectivity should only provide additional capabilities such as:

- Remote synchronization
- Remote monitoring
- Backup
- Access to historical data from another system

The core rover system must never depend on the internet to operate.

---

# 2. Final System Architecture

The complete local system is:

```text
                    MINING ROVER
                         |
        +----------------+----------------+
        |                                 |
   Vision / YOLO                    Sensor Service
        |                                 |
        +---------------+-----------------+
                        |
                        v
                Decision Engine
                        |
                        v
                 Local SQLite DB
                        |
                        v
                  FastAPI Backend
                        |
                        v
                 Local Dashboard
```

Network synchronization is an additional layer:

```text
                 LOCAL ROVER
                     |
                SQLite Database
                     |
                 Sync Queue
                     |
              Network Available?
                /            \
              NO              YES
              |                |
       Continue locally    Sync pending data
                               |
                               v
                         Remote Server
```

---

# 3. Core Requirement

## Offline-first

The following components MUST work without internet:

* Sensor Data Service
* Vision/YOLO inference
* Decision Engine
* SQLite database
* FastAPI backend
* Dashboard
* Mission logging
* Real-time local monitoring

The system must NOT:

```text
wait for internet
require cloud APIs
stop sensor collection
stop decision making
stop database storage
```

when connectivity is lost.

---

# 4. Online Mode

When network connectivity is available:

```text
Sensors
   |
Vision
   |
Decision Engine
   |
SQLite
   |
FastAPI
   |
Dashboard
   |
Sync Service
   |
Remote Server
```

The system should:

1. Continue normal local operation.
2. Detect network availability.
3. Send pending records to the remote server.
4. Mark successfully synchronized records.
5. Continue collecting new data.
6. Synchronize new records in the background.

Synchronization must NOT block:

* Sensor collection
* YOLO inference
* Decision engine
* Database writes
* Dashboard updates

---

# 5. Offline Mode

When network connectivity is unavailable:

```text
Sensors
   |
Vision
   |
Decision Engine
   |
SQLite
   |
FastAPI
   |
Dashboard
```

The system continues normally.

All new data is stored locally.

Examples:

```text
Gas readings
Temperature
Humidity
Smoke detection
Fire detection
Rockfall detection
Hard-hat detection
Hazard severity
Decision results
Mission status
System events
```

Nothing should be lost simply because the network is unavailable.

---

# 6. Sync Queue

The system must maintain a synchronization state for records.

Example:

```text
sync_status

PENDING
SYNCING
SYNCED
FAILED
```

Recommended database concept:

```text
id
record_type
record_id
created_at
sync_status
retry_count
last_sync_attempt
last_error
```

Example:

```text
id: 1023
record_type: sensor_reading
record_id: 4567
sync_status: PENDING
retry_count: 0
```

When the network returns:

```text
PENDING
   ↓
SYNCING
   ↓
Remote upload successful
   ↓
SYNCED
```

If upload fails:

```text
SYNCING
   ↓
FAILED
   ↓
retry later
```

---

# 7. Retry Strategy

The synchronization service should retry failed uploads.

Do NOT continuously retry without delay.

Use a simple backoff strategy:

```text
1st attempt → immediately
2nd attempt → after delay
3rd attempt → longer delay
4th attempt → longer delay
...
```

The retry mechanism must prevent the sync service from consuming excessive CPU/network resources.

---

# 8. Duplicate Protection

Synchronization must be safe against duplicate uploads.

Every synchronized record should have a unique identifier.

Example:

```text
event_id
mission_id
sensor_reading_id
detection_id
```

The remote system should be able to recognize:

```text
"This record has already been synchronized."
```

and avoid creating duplicates.

---

# 9. Local Database Rules

SQLite remains the **source of truth for the rover**.

Important rule:

```text
Network failure
      ↓
Do NOT delete local data
```

Local data should remain available even after successful synchronization unless a separate retention policy is implemented.

The sync process should only update synchronization metadata.

---

# 10. Dashboard Requirements

The dashboard must work locally.

It should display:

### Real-time information

```text
Gas Levels
Temperature
Humidity
Smoke
Fire
Rockfall
Hard Hat
Hazard Severity
Decision Engine Result
Mission Status
```

### Live feed

Display the rover's camera/vision feed when available.

### Mission log

Show what is currently happening.

Example:

```text
MISSION ACTIVE

10:42:13
Rover entered Zone B

10:42:18
Gas level increased

10:42:19
YOLO detected smoke

10:42:20
Decision Engine:
HIGH HAZARD

10:42:21
Event stored locally
```

---

# 11. Online/Offline Status

The dashboard should clearly show system connectivity.

Example:

```text
● ONLINE
```

or

```text
● OFFLINE
```

The status should describe connectivity to the remote synchronization service.

Do NOT imply that the rover itself has stopped working when the remote network is unavailable.

Example:

```text
OFFLINE

Local operation: ACTIVE
Data storage: ACTIVE
Decision engine: ACTIVE
Sync queue: 124 records pending
```

This is preferable to simply showing:

```text
OFFLINE
```

because the rover is still operational.

---

# 12. Sync Status on Dashboard

Display a small synchronization indicator.

Example:

```text
Network: ONLINE
Sync: SYNCED
```

or:

```text
Network: OFFLINE
Sync: 128 records pending
```

or:

```text
Network: ONLINE
Syncing: 24 records
```

Keep this information secondary.

The main dashboard should remain focused on:

* Safety
* Sensor values
* Detection results
* Decision result
* Mission status

---

# 13. FastAPI Integration

FastAPI should expose local APIs for the dashboard.

Example:

```text
GET /api/sensors/latest
GET /api/detections/latest
GET /api/decision/latest
GET /api/mission/current
GET /api/logs
GET /api/system/status
GET /api/sync/status
```

Example system status:

```json
{
  "network": "offline",
  "local_database": "healthy",
  "sensor_service": "running",
  "vision_service": "running",
  "decision_engine": "running",
  "sync_pending": 128
}
```

The dashboard should continue working even when:

```text
network = offline
```

because it communicates with the local FastAPI backend.

---

# 14. Sync Service

Create:

```text
sync/
├── sync_service.py
├── queue_manager.py
├── network_monitor.py
├── retry_manager.py
└── README.md
```

Responsibilities:

### network_monitor.py

Determine whether the remote synchronization endpoint is reachable.

### queue_manager.py

Find records waiting for synchronization.

### sync_service.py

Upload pending records.

### retry_manager.py

Handle failed synchronization attempts.

---

# 15. Deployment Structure

Final software structure should look approximately like:

```text
Mining_Rover_software/
│
├── vision/
│   ├── training/
│   ├── inference/
│   └── weights/
│       └── best.pt
│
├── sensors/
│   ├── sensor_service.py
│   └── ...
│
├── decision_engine/
│   ├── decision_engine.py
│   └── ...
│
├── database/
│   ├── database.py
│   ├── models.py
│   └── rover.db
│
├── backend/
│   ├── main.py
│   ├── routes/
│   └── services/
│
├── dashboard/
│   ├── src/
│   ├── package.json
│   └── ...
│
├── sync/
│   ├── sync_service.py
│   ├── queue_manager.py
│   ├── network_monitor.py
│   └── retry_manager.py
│
├── config/
│   └── config.yaml
│
├── logs/
│
├── requirements.txt
└── README.md
```

---

# 16. Configuration

Do not hard-code deployment settings throughout the code.

Use a central configuration file/environment variables.

Example:

```yaml
database:
  path: "./database/rover.db"

backend:
  host: "0.0.0.0"
  port: 8000

sync:
  enabled: true
  server_url: ""
  retry_interval: 30

vision:
  model: "./vision/weights/best.pt"
```

The rover must still work if:

```yaml
sync:
  enabled: false
```

---

# 17. Startup

Create a single startup mechanism for the complete rover software.

Example:

```text
start_rover
     |
     +── Sensor Service
     |
     +── Vision Service
     |
     +── Decision Engine
     |
     +── FastAPI
     |
     +── Sync Service
     |
     └── Dashboard
```

The startup system should verify that required services are running.

---

# 18. Failure Handling

The rover must handle individual component failures gracefully.

Example:

### Network failure

```text
Network unavailable
        ↓
Sync paused
        ↓
Local operation continues
```

### Remote server unavailable

```text
Remote server unavailable
        ↓
Records remain pending
        ↓
Retry later
```

### Dashboard unavailable

```text
Dashboard stopped
        ↓
Sensor + vision + decision + database continue
```

### Sync service unavailable

```text
Sync stopped
        ↓
Data continues accumulating locally
```

No synchronization failure should cause the core rover processing pipeline to stop.

---

# 19. Logging

Maintain system logs for:

```text
Service started
Service stopped
Network connected
Network disconnected
Sync started
Sync completed
Sync failed
Database errors
Sensor errors
Vision errors
Decision engine errors
```

Example:

```text
[10:42:01] Sensor service started
[10:42:02] Vision service started
[10:42:03] Database initialized
[10:42:15] Network unavailable
[10:42:15] Offline mode active
[10:42:20] Detection stored locally
[10:42:21] Decision stored locally
[10:48:32] Network restored
[10:48:35] Sync started
[10:48:41] 128 records synchronized
```

---

# 20. Testing Requirements

Phase 6 is not complete until the following scenarios are tested.

## Test 1 — Normal online operation

```text
Network: ONLINE

Sensors → Database → Dashboard
Vision → Database → Dashboard
Decision → Database → Dashboard
Sync → Remote Server
```

Expected:

```text
All systems operational
```

---

## Test 2 — Network disconnect

Start the rover while online.

Then disconnect the network.

Expected:

```text
Sensors: RUNNING
Vision: RUNNING
Decision: RUNNING
Database: RUNNING
Dashboard: RUNNING
Sync: PAUSED
```

New records must continue entering SQLite.

---

## Test 3 — Network restoration

Reconnect the network.

Expected:

```text
Sync service detects network
        ↓
Pending records uploaded
        ↓
Records marked SYNCED
```

No duplicate records should be created.

---

## Test 4 — Remote server unavailable

Network exists but remote server is unavailable.

Expected:

```text
Local system: RUNNING
Sync: FAILED/RETRYING
Local data: SAFE
```

---

## Test 5 — Long offline mission

Run the rover in offline mode for an extended period.

Verify:

```text
Sensor data continues
Vision continues
Decision engine continues
Database continues
Dashboard continues
Logs continue
```

After reconnecting:

```text
All pending data is synchronized.
```

---

# 21. Performance Requirements

The sync process must not significantly affect:

* Sensor sampling
* Vision inference
* Decision engine
* Dashboard responsiveness

Synchronization should run asynchronously/background.

Core processing has higher priority than synchronization.

---

# 22. Security

Do not expose the local database directly to the network.

Only expose required FastAPI endpoints.

Remote synchronization should use authenticated communication when a remote server is introduced.

Never hard-code:

```text
API keys
passwords
tokens
credentials
```

inside the repository.

---

# 23. Completion Criteria

Phase 6 is complete when:

* [ ] Complete rover software runs locally.
* [ ] Rover operates without internet.
* [ ] Sensor data is stored locally.
* [ ] YOLO inference works locally.
* [ ] Decision engine works locally.
* [ ] Dashboard works locally.
* [ ] Mission logs work locally.
* [ ] Network status is detected.
* [ ] Sync queue stores pending records.
* [ ] Pending records synchronize when network returns.
* [ ] Failed synchronization retries.
* [ ] Duplicate synchronization is prevented.
* [ ] Network failure does not stop rover operation.
* [ ] Long offline operation has been tested.
* [ ] Online → offline → online transition has been tested.

---

# 24. Most Important Design Principle

The final architecture must follow:

```text
             OFFLINE-FIRST
                  |
        +---------+---------+
        |                   |
   CORE SYSTEM          SYNC SYSTEM
        |                   |
   Works offline       Requires network
        |                   |
   SQLite              Remote server
        |
   Dashboard
        |
   Rover continues working
```

### Golden rule

> **The network is optional. Local operation is mandatory.**

The rover should never stop collecting, processing, deciding, storing, or displaying data simply because the internet disappears.
