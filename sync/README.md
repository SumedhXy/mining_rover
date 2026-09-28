# Mining Rover Synchronization Subsystem

The **Synchronization Subsystem** (`sync/`) is an offline-first data replication service that uploads locally collected CAN bus sensor readings, YOLO vision detections, and Decision Engine hazard assessments from the rover's SQLite database to an authorized remote server whenever network connectivity becomes available.

---

## Architectural Principles

1. **Local Operation is Mandatory; Network is Optional**:
   The rover never waits for remote network confirmation. Sensor collection, model inference, decision making, local SQLite logging, and the dashboard operate continuously without any network dependencies.
2. **Atomic State Updates**:
   Records in SQLite maintain sync flags (`synced = 0` for pending, `synced = 1` for synchronized). Only upon confirmed HTTP 200/201 response from the remote endpoint are local records updated.
3. **Duplicate Protection (Idempotency)**:
   Every record transmitted is tagged with a composite deterministic `unique_id` (e.g. `sensor_12_2026-09-27T10:30:15+05:30`). The remote synchronization server uses this key to ignore duplicated uploads across retries.
4. **Exponential Backoff & Jitter**:
   Failed upload attempts automatically engage a non-blocking exponential backoff delay to prevent connection storms or excessive CPU/network consumption.

---

## Subsystem Structure

```text
sync/
├── network_monitor.py   # Probes endpoint reachability with strict timeouts & override hooks
├── queue_manager.py     # Pulls pending records from SQLite; manages in-flight batches
├── retry_manager.py     # Exponential backoff calculations with randomized jitter
├── sync_service.py      # Background worker coordinating monitoring, upload, & updates
└── README.md            # Subsystem specification & documentation
```

---

## Component Roles

### `network_monitor.py`
Determines whether the remote synchronization endpoint or uplink is reachable.
- Uses rapid HTTP HEAD/GET probes and fallback socket connections.
- Exposes `is_online() -> bool` and callback listeners for state transitions.
- Supports `set_override(True/False)` for unit testing and offline simulation drills.

### `retry_manager.py`
Calculates progressive delays for failed synchronization attempts:
$$\text{delay} = \min(\text{max\_delay}, \text{base\_delay} \times \text{multiplier}^{(\text{attempt} - 1)}) \pm \text{jitter}$$
- Prevents immediate repeated failures from wasting battery or compute resources.
- Automatically resets backoff once an upload succeeds.

### `queue_manager.py`
Interacts with the `database.database.SQLiteDatabase` layer:
- Batches pending records (`sensor_readings`, `vision_detections`, `hazard_events`).
- Filters out records currently held in backoff delay.
- Atomically marks confirmed records as `SYNCED`.

### `sync_service.py`
The top-level orchestrator:
- Can run as a non-blocking daemon thread (`start()` / `stop()`) or via manual trigger (`sync_cycle()`).
- Packages records into a JSON envelope:
  ```json
  {
    "rover_id": "mining_rover_01",
    "timestamp": "2026-09-28T01:00:00Z",
    "batch_size": 25,
    "records": [ ... ]
  }
  ```
- Exposes real-time sync metrics via `get_status()`.

---

## API Endpoints (`/api/sync`)

- `GET /api/sync/status`: Real-time queue, network reachability, and sync status.
- `POST /api/sync/trigger`: Immediately invoke a synchronization cycle.
- `POST /api/sync/receive`: Remote receiver endpoint with duplicate detection for testing and dual-system simulation.
