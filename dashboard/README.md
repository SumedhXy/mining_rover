# Mining Rover Dashboard — Frontend Only

## Objective

Build a clean, professional React dashboard for the Mining Rover.

This phase is ONLY the frontend.

The frontend must be designed so that a FastAPI backend can be connected later.

DO NOT build backend functionality in this phase.

---

# Tech Stack

- React
- Vite
- Tailwind CSS
- JavaScript or TypeScript

---

# Main Goal

The dashboard should clearly display:

1. Live camera feed
2. Real-time sensor values
3. Current Decision Engine result
4. Current hazard/severity
5. Current mission status
6. Mission events/logs
7. Online/offline status

The interface must remain clean and professional.

Do NOT overcrowd the dashboard.

---

# Pages

Create only these pages:

## 1. Dashboard

Main real-time monitoring screen.

## 2. Missions

Shows previous and current missions.

## 3. Logs

Shows mission events in chronological order.

## 4. System

Shows basic rover/system status.

---

# Dashboard Layout

Use this visual hierarchy:

### Header

Display:

- Mining Rover
- Current mission ID
- Current time
- System connection status

Example:

Mining Rover                         ● ONLINE
Mission #001                         14:32:08

---

## Main Content

### Left: Live Camera

Large camera/video area.

For now use a placeholder:

    LIVE CAMERA
    Waiting for video stream...

Later the backend/streaming service will provide the actual video URL/stream.

Support displaying:

- YOLO bounding boxes
- Detection class
- Confidence

Example:

    FIRE 91%
    SMOKE 84%

Do NOT implement YOLO in the frontend.

---

### Right: Current Hazard

Large status panel.

Example:

    CURRENT HAZARD

    FIRE DETECTED

    Severity: HIGH
    Confidence: 91%

    Reason:
    Fire + elevated temperature

The values must come from API data later.

For now use mock data.

---

# Real-Time Sensor Section

Create a clean sensor section below the camera/hazard area.

Display only important sensors.

Example:

    TEMPERATURE
    34.5 °C

    HUMIDITY
    61 %

    GAS LEVEL
    0.72

    AIR QUALITY
    GOOD

Use reusable SensorCard components.

Do NOT hard-code the final sensor list into the architecture.

The frontend should be easy to connect to backend data later.

---

# Mission Status

Display:

    Mission #001
    Status: ACTIVE
    Duration: 22 min

Possible status values:

- IDLE
- ACTIVE
- PAUSED
- COMPLETED
- ABORTED

Use mock data initially.

---

# Mission Log

Create a clean event timeline.

Example:

    14:10:32
    Mission started

    14:12:18
    Rock detected

    14:12:21
    Hazard level → LOW

    14:15:32
    Smoke detected

    14:15:34
    Hazard level → MEDIUM

The frontend only displays these events.

Do NOT generate or calculate events.

---

# Missions Page

Display previous missions in a clean table/list.

Example:

    Mission #001
    COMPLETED
    47 min
    4 hazards

    Mission #002
    COMPLETED
    31 min
    2 hazards

Clicking a mission should open its details.

Use mock data.

---

# Logs Page

Display mission events.

Columns/fields:

- Time
- Event type
- Description
- Severity

Example:

| Time | Type | Event | Severity |
|------|------|-------|----------|
| 14:12 | Vision | Rock detected | LOW |
| 14:15 | Vision | Smoke detected | MEDIUM |
| 14:20 | Decision | Hazard HIGH | HIGH |

Add simple filters:

- All
- Vision
- Sensor
- Decision
- Mission
- System

These filters are frontend-only.

---

# System Page

Display simple system information:

    Rover       ● Running
    Backend     ● Connected
    Database    ● Connected
    Network     ● Online

This page is informational only.

---

# Online / Offline UI

The frontend must visually support:

### Online

    ● ONLINE

### Offline

    ● OFFLINE

### Backend unavailable

    ⚠ BACKEND DISCONNECTED

Do not implement synchronization logic.

Do not implement offline database logic.

Only create the UI states.

---

# Backend Integration Contract

The frontend must be written so mock data can later be replaced with API responses.

Create a separate API layer such as:

    src/api/

Example:

    src/api/roverApi.js

Initially return mock data.

Example functions:

    getLatestSensors()
    getLatestVision()
    getLatestDecision()
    getCurrentMission()
    getMissionHistory()
    getMissionLogs()
    getSystemStatus()

Do NOT connect to a real backend yet.

Use mock implementations.

Later these functions will call FastAPI.

---

# Expected Future API Structure

The frontend should be prepared for endpoints such as:

    GET /api/sensors/latest

    GET /api/vision/latest

    GET /api/decision/latest

    GET /api/mission/current

    GET /api/missions

    GET /api/missions/{id}

    GET /api/logs

    GET /api/system/status

These are placeholders only.

Do not build these FastAPI endpoints.

---

# Important Separation

Frontend:

    React
       ↓
    API layer
       ↓
    FastAPI
       ↓
    Backend services

The frontend must NOT:

- Access SQLite
- Implement Decision Engine
- Process sensor data
- Run YOLO
- Control motors
- Implement sync logic
- Generate mission events

The frontend only displays data received from the backend.

---

# Mock Data

Until the backend is connected, create realistic mock data.

Example:

```js
const mockSensors = {
  temperature: 34.5,
  humidity: 61,
  gasLevel: 0.72
};

const mockDecision = {
  hazard: "FIRE",
  severity: "HIGH",
  confidence: 0.91,
  reason: "Fire detected + elevated temperature"
};
```
