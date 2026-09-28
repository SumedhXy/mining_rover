# Contributing to Mining Rover Software

Thank you for your interest in contributing to the **Mining Rover Autonomous Monitoring System**!

This project is built for high-reliability, offline-first autonomous underground operations on Raspberry Pi 4B and ESP32 hardware.

---

## 🏛️ Architecture & Ground Rules

1. **Hazard Intelligence Boundary:**
   - The Decision Engine (`decision_engine/`) evaluates multi-modal sensor and vision inputs to classify hazards, calculate severity, and assign confidence.
   - **CRITICAL:** The Decision Engine does **not** directly command hardware motors, steering, or actuator controls.
2. **Offline-First Principle:**
   - All critical telemetry, hazard events, and mission logs must be persisted in SQLite before any network transmission is attempted.
   - The system must function 100% autonomously without active internet connectivity.
3. **Hardware Independence & Portability:**
   - Never hardcode Windows-specific (`C:\`) or Linux-specific paths; always use `pathlib.Path`.
   - Never commit `.env`, SQLite databases, or private credentials.

---

## 🚀 Development Setup

### 1. Clone & Set Up Python Environment

```bash
# Clone the repository
git clone https://github.com/your-org/Mining_Rover_software.git
cd Mining_Rover_software

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
# .venv\Scripts\Activate.ps1   # Windows PowerShell

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

### 3. Run Test Suite

```bash
# Run all unit and integration tests
python -m pytest

# Run the complete functional acceptance testing matrix
python scripts/acceptance_test_runner.py
```

### 4. Start the Development Stack

```bash
# Terminal 1: Backend API Gateway
python start_rover.py --health-report

# Terminal 2: Mission Control Dashboard
cd dashboard
npm install
npm run dev
```

---

## 🧪 Testing Guidelines

- Every new feature, endpoint, or sensor parser must include automated tests in `tests/`.
- Maintain 100% passing status across the existing 193+ pytest suite.
- Verify edge cases: missing sensor packets, corrupted serial frames, camera disconnects, and offline buffering.

---

## 📝 Pull Request Checklist

- [ ] `python -m pytest` passes with 0 failures.
- [ ] Code follows PEP 8 standards with type hints.
- [ ] No hardcoded paths or environment secrets are introduced.
- [ ] Any new API endpoint is documented with Pydantic schemas in `backend/schemas/`.
- [ ] Pull request description clearly explains the changes and references any related issue.
