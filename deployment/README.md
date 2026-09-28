# Mining Rover Software — Deployment Guide
## Phase 7A: Raspberry Pi Deployment Preparation

> **Phase 7A prepares the software for Raspberry Pi deployment.
> It does not deploy the software to the Raspberry Pi.**

---

## Table of Contents

1. [Overview](#overview)
2. [Development Environment (Windows/Linux PC)](#a-development-environment)
3. [Raspberry Pi Target Environment](#b-raspberry-pi-target-environment)
4. [Directory Structure](#c-directory-structure)
5. [Python Virtual Environment](#d-python-virtual-environment)
6. [Dependency Installation](#e-dependency-installation)
7. [ARM64 / Raspberry Pi Compatibility Notes](#arm64--raspberry-pi-compatibility-notes)
8. [Configuration](#f-configuration)
9. [Model Placement](#g-model-placement)
10. [Database Location](#h-database-location)
11. [Manual Startup](#i-manual-startup)
12. [Health Checks](#j-health-checks)
13. [Systemd Service](#k-systemd-service)
14. [Logs](#l-logs)
15. [Network / Dashboard Access](#dashboard-access-over-lan)
16. [Security](#security)
17. [Phase 7B — Physical Deployment](#m-what-phase-7b-will-do)

---

## Overview

The Mining Rover software is an **offline-first autonomous monitoring system** designed
to run on a Raspberry Pi 4B (8 GB) without a permanently connected display.

The dashboard is accessed remotely over the local Wi-Fi network from a laptop or tablet.

**Architecture:**
```
Raspberry Pi 4B
  │
  ├── ESP32 Sensor Node (serial/USB)
  │     └── sensors/ — reads gas, temperature, humidity, vibration
  │
  ├── Camera (Pi Camera or USB)
  │     └── vision/ — YOLO inference (fire/hazard detection)
  │
  ├── Decision Engine
  │     └── decision_engine/ — sensor fusion + hazard classification
  │
  ├── SQLite (offline-first persistent storage)
  │     └── database/mining_rover.db
  │
  ├── FastAPI Backend (port 8000)
  │     └── backend/ — REST API for dashboard
  │
  └── Sync Worker (optional, background)
        └── sync/ — uploads records to remote when online
```

---

## A. Development Environment

**Target:** Windows 10/11 or Linux PC.

```bash
# 1. Clone the repository
git clone <repo-url>
cd Mining_Rover_software

# 2. Create virtual environment
python -m venv .venv

# 3a. Activate (Linux/macOS)
source .venv/bin/activate

# 3b. Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# 4. Install runtime + dev dependencies
pip install -r requirements.txt -r requirements-dev.txt

# 5. Copy and configure environment
cp .env.example .env
# Edit .env if needed

# 6. Run the test suite
python -m pytest

# 7. Start the backend (development)
python start_rover.py --health-report
```

Dashboard (separate terminal):
```bash
cd dashboard
npm install
npm run dev
# → http://localhost:3000
```

---

## B. Raspberry Pi Target Environment

| Spec | Value |
|---|---|
| Hardware | Raspberry Pi 4B — 8 GB RAM |
| OS | Raspberry Pi OS 64-bit (Bookworm recommended) |
| Architecture | ARM64 / aarch64 |
| Python | 3.11+ (pre-installed on Bookworm) |
| Display | Not required — headless operation |
| Network | Wi-Fi — dashboard accessed from LAN devices |
| Storage | SD card or USB SSD (SSD recommended for DB performance) |

---

## C. Directory Structure

Recommended layout on the Raspberry Pi:

```
/home/rover/mining_rover/          ← project root (WorkingDirectory)
    .venv/                         ← virtual environment (not committed)
    .env                           ← runtime secrets (not committed)
    config/
        config.yaml                ← main configuration
        config.yaml.example        ← template
    backend/
    database/
        mining_rover.db            ← SQLite database (created automatically)
    decision_engine/
    sensors/
    vision/
        weights/
            best.pt                ← YOLO model weights (copied manually)
    sync/
    logs/                          ← log files (created automatically)
    data/
        images/                    ← captured frames (created automatically)
    deployment/
        mining-rover.service       ← systemd unit template
        deploy_pi.sh               ← deployment script
        check_deployment.py        ← readiness checker
        README.md                  ← this file
    requirements.txt
    requirements-dev.txt
    start_rover.py
```

---

## D. Python Virtual Environment

The application runs in a standard Python virtual environment. Docker is not used.

```bash
# On the Raspberry Pi
cd /home/rover/mining_rover
python3 -m venv .venv
source .venv/bin/activate
```

---

## E. Dependency Installation

### Core runtime (Raspberry Pi production):
```bash
pip install -r requirements.txt
```

### Development + tests (PC only):
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### Dependency summary

| Package | Purpose | Module | ARM64 Note |
|---|---|---|---|
| `fastapi` | REST API framework | `backend/` | ✅ pip wheel works |
| `uvicorn` | ASGI server | `start_rover.py` | ✅ pip wheel works |
| `pydantic` | Data validation | `backend/schemas/` | ✅ pip wheel works |
| `PyYAML` | Config loading | `config/config.py` | ✅ pip wheel works |
| `python-multipart` | File upload (FastAPI) | `backend/` | ✅ pip wheel works |
| `Pillow` | Image I/O for YOLO | `vision/inference/yolo_service.py` | ✅ pip wheel works |
| `ultralytics` | YOLO v8/v11 | `vision/inference/yolo_service.py` | ⚠️ See ARM64 notes |
| `pyserial` | ESP32 serial | `sensors/esp32_receiver.py` | ✅ pip wheel works |
| `pytest` *(dev)* | Test runner | `tests/` | Dev only |
| `httpx` *(dev)* | TestClient | `tests/` | Dev only |

---

## ARM64 / Raspberry Pi Compatibility Notes

> These are known compatibility concerns for ARM64. They must be resolved
> before Phase 7B (physical deployment). **Do not assume `pip install` will
> work for all packages on ARM64 without verification.**

### PyTorch (required by ultralytics)

`pip install torch` from PyPI may not have a compatible ARM64 wheel.

**Recommended approach on Raspberry Pi OS (aarch64):**

```bash
# Option A: Install the PyTorch ARM64 wheel from the official index
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Option B: Use the Raspberry Pi community wheel
# (Check: https://github.com/Qengineering/Install-PyTorch-on-Raspberry-Pi-4)

# Option C: Use ONNX/NCNN export (best performance, no torch required at runtime)
# The project includes a best_ncnn_model — see vision/weights/best_ncnn_model/
```

### OpenCV (cv2)

Use `opencv-python-headless` on a headless Pi (no X display):
```bash
pip install opencv-python-headless
```
Not `opencv-python` (which requires a display server / GUI libs).

### ultralytics

Install **after** torch is working:
```bash
pip install ultralytics
```

### System packages (may be required)

```bash
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    libatlas-base-dev \
    libhdf5-dev \
    libopenblas-dev \
    liblapack-dev \
    libjpeg-dev \
    libopenjp2-7 \
    libv4l-dev \
    v4l-utils \
    i2c-tools
```

---

## F. Configuration

Copy the template and edit for your environment:

```bash
cp .env.example .env
nano .env
```

Key settings:

| Variable | Default | Notes |
|---|---|---|
| `ROVER_DB_PATH` | `./database/mining_rover.db` | SQLite file path |
| `ROVER_BACKEND_HOST` | `0.0.0.0` | Bind to all interfaces for LAN access |
| `ROVER_BACKEND_PORT` | `8000` | FastAPI listen port |
| `ROVER_SYNC_ENABLED` | `true` | Set `false` for air-gapped operation |
| `ROVER_VISION_MODEL` | `./vision/weights/best.pt` | YOLO weights path |
| `ROVER_ALLOWED_ORIGINS` | `*` | CORS — restrict to dashboard IP in production |
| `LOG_LEVEL` | `INFO` | `DEBUG` for troubleshooting |
| `ROVER_SENSOR_PORT` | *(unset)* | `/dev/ttyUSB0` for ESP32 on Pi |

---

## G. Model Placement

Copy your trained YOLO weights to the Pi:

```bash
# From development machine
scp vision/weights/best.pt rover@<PI_IP>:/home/rover/mining_rover/vision/weights/best.pt

# Verify
ls -lh /home/rover/mining_rover/vision/weights/best.pt
```

Without `best.pt`, the system runs in **simulated perception mode** — safe for testing,
but fire/hazard vision detection is disabled.

---

## H. Database Location

The SQLite database is created automatically at:

```
database/mining_rover.db
```

or at the path set in `ROVER_DB_PATH` / `config.yaml`.

**Backup recommendation:** periodically copy the `.db` file off the Pi:
```bash
scp rover@<PI_IP>:/home/rover/mining_rover/database/mining_rover.db ./backup/
```

---

## I. Manual Startup

```bash
# Activate venv
source /home/rover/mining_rover/.venv/bin/activate

cd /home/rover/mining_rover

# Health check only (no server start)
python start_rover.py --check-only

# Full health report + no server start
python start_rover.py --health-report --check-only

# Start server
python start_rover.py

# Custom bind
python start_rover.py --host 0.0.0.0 --port 8000
```

---

## J. Health Checks

```bash
# Python deployment readiness checker (18 named checks)
python deployment/check_deployment.py
python deployment/check_deployment.py --verbose
python deployment/check_deployment.py --json

# Startup script health report
python start_rover.py --health-report --check-only

# Run the full test suite (development only)
python -m pytest
```

---

## K. Systemd Service

The service template is at `deployment/mining-rover.service`.

**Manual installation on Pi (done during Phase 7B):**

```bash
# Substitute the project path and install
sudo sed "s|/home/rover/mining_rover|$(pwd)|g" \
    deployment/mining-rover.service \
    | sudo tee /etc/systemd/system/mining-rover.service

sudo systemctl daemon-reload

# Enable at boot (optional — done by deploy_pi.sh --install --start)
sudo systemctl enable mining-rover

# Start now
sudo systemctl start mining-rover

# Check status
sudo systemctl status mining-rover
```

Or use the automated script:
```bash
./deployment/deploy_pi.sh --install
./deployment/deploy_pi.sh --install --start
```

---

## L. Logs

**Via systemd journal (production):**
```bash
journalctl -u mining-rover -f            # tail live
journalctl -u mining-rover --since today # today's logs
journalctl -u mining-rover -n 100        # last 100 lines
```

**Direct (development / manual run):**
```bash
python start_rover.py 2>&1 | tee logs/rover.log
```

Set `LOG_LEVEL=DEBUG` in `.env` for verbose output during troubleshooting.

---

## Dashboard Access Over LAN

The dashboard is accessed from another device on the same Wi-Fi network.

| Service | URL |
|---|---|
| FastAPI backend | `http://<PI_IP>:8000` |
| API docs | `http://<PI_IP>:8000/docs` |
| Dashboard (dev) | `http://<PI_IP>:3000` |

Find the Pi's IP:
```bash
hostname -I
```

The Pi does **not** need an HDMI display for the dashboard to work.

> **Security:** Do not expose port 8000 to the internet.
> The system is designed for local LAN use only.

---

## Security

- Never commit `.env` (listed in `.gitignore`)
- CORS is open by default (`*`); restrict `ROVER_ALLOWED_ORIGINS` in production
- The systemd service runs as a non-root `rover` user
- No credentials or API keys are hard-coded in the software

---

## M. What Phase 7B Will Do

Phase 7A (this phase) prepares the software. Phase 7B performs physical deployment:

- [ ] SSH into the Raspberry Pi 4B
- [ ] Clone the repository (or `rsync` from development machine)
- [ ] Run `./deployment/deploy_pi.sh --check` to verify readiness
- [ ] Install PyTorch ARM64 wheel (manual step — see ARM64 notes)
- [ ] Run `./deployment/deploy_pi.sh --install` to set up venv + service
- [ ] Copy `best.pt` YOLO weights
- [ ] Edit `/home/rover/mining_rover/.env` for production paths
- [ ] Configure `ROVER_SENSOR_PORT=/dev/ttyUSB0` for ESP32
- [ ] Test hardware: camera, serial, sensor data
- [ ] Run `./deployment/deploy_pi.sh --install --start` to enable the service
- [ ] Verify live dashboard access from another device
- [ ] Document hardware wiring (CAN bus, camera, ESP32 connection)
