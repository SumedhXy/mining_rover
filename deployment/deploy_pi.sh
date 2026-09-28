#!/usr/bin/env bash
# =============================================================================
# Mining Rover Software — Raspberry Pi Deployment Script
# Phase 7A — Deploy from project directory to a Raspberry Pi 4
# =============================================================================
#
# USAGE:
#   ./deployment/deploy_pi.sh --check          # Validate system readiness only
#   ./deployment/deploy_pi.sh --install        # Full installation
#   ./deployment/deploy_pi.sh --install --start  # Install AND enable service
#
# IMPORTANT:
#   This script must be run ON the Raspberry Pi (not on a development PC).
#   It assumes you have already cloned/copied the project to the Pi.
#   Run from the PROJECT ROOT directory:
#       cd /home/rover/mining_rover
#       ./deployment/deploy_pi.sh --check
#
# =============================================================================

set -euo pipefail

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

pass() { echo -e "  ${GREEN}[PASS]${RESET} $1"; }
fail() { echo -e "  ${RED}[FAIL]${RESET} $1"; FAILURES=$((FAILURES + 1)); }
warn() { echo -e "  ${YELLOW}[WARN]${RESET} $1"; }
info() { echo -e "  ${CYAN}[INFO]${RESET} $1"; }
step() { echo -e "\n${BOLD}══ $1${RESET}"; }

FAILURES=0
MODE_CHECK=false
MODE_INSTALL=false
MODE_START=false

# ── Argument parsing ──────────────────────────────────────────────────────────
for arg in "$@"; do
    case "$arg" in
        --check)   MODE_CHECK=true ;;
        --install) MODE_INSTALL=true ;;
        --start)   MODE_START=true ;;
        --help|-h)
            echo "Usage: $0 [--check] [--install] [--start]"
            echo "  --check    Validate system readiness (no changes made)"
            echo "  --install  Perform full deployment installation"
            echo "  --start    Enable & start the systemd service after install"
            exit 0 ;;
        *)
            echo "Unknown argument: $arg" >&2
            exit 1 ;;
    esac
done

# Default to --check if no mode specified
if [ "$MODE_CHECK" = false ] && [ "$MODE_INSTALL" = false ]; then
    MODE_CHECK=true
fi

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}=================================================================${RESET}"
echo -e "${BOLD}   Mining Rover — Raspberry Pi Deployment Script (Phase 7A)${RESET}"
echo -e "${BOLD}=================================================================${RESET}"
echo ""

# ── 1. Platform validation ────────────────────────────────────────────────────
step "1. Platform Validation"

if [ "$(uname -s)" != "Linux" ]; then
    fail "Not running on Linux (detected: $(uname -s)). This script is for Raspberry Pi OS."
    exit 1
fi
pass "Linux OS detected"

ARCH=$(uname -m)
info "Architecture: $ARCH"
if [ "$ARCH" != "aarch64" ] && [ "$ARCH" != "armv7l" ]; then
    warn "Expected aarch64 (Raspberry Pi 4 64-bit) or armv7l (32-bit). Got: $ARCH"
    warn "ARM64 compatibility notes apply — see deployment/README.md."
else
    pass "ARM architecture detected: $ARCH"
fi

# Detect if running on actual Pi hardware
if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    pass "Raspberry Pi hardware confirmed"
else
    warn "Could not confirm Raspberry Pi hardware from /proc/cpuinfo"
fi

# ── 2. Python version ─────────────────────────────────────────────────────────
step "2. Python Version"

PYTHON_BIN=""
for candidate in python3.12 python3.11 python3.10 python3; do
    if command -v "$candidate" &>/dev/null; then
        PYTHON_BIN="$candidate"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    fail "No suitable Python interpreter found. Install Python 3.10+."
    exit 1
fi

PY_VERSION=$("$PYTHON_BIN" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
    fail "Python $PY_VERSION detected. Minimum required: 3.10. Install a newer version."
else
    pass "Python $PY_VERSION ($PYTHON_BIN)"
fi

# ── 3. Project directory ──────────────────────────────────────────────────────
step "3. Project Directory"

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
info "Project root: $PROJECT_DIR"

REQUIRED_FILES=(
    "start_rover.py"
    "requirements.txt"
    "config/config.yaml"
    "backend/main.py"
    "database/database.py"
    "decision_engine/engine.py"
    "sync/sync_service.py"
)

for f in "${REQUIRED_FILES[@]}"; do
    if [ -f "$PROJECT_DIR/$f" ]; then
        pass "Found: $f"
    else
        fail "Missing required file: $f"
    fi
done

# ── 4. Virtual environment ────────────────────────────────────────────────────
step "4. Virtual Environment"

VENV_DIR="$PROJECT_DIR/.venv"

if [ -d "$VENV_DIR" ]; then
    pass "Virtual environment exists: $VENV_DIR"
elif [ "$MODE_INSTALL" = true ]; then
    info "Creating virtual environment at $VENV_DIR ..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
    pass "Virtual environment created"
else
    warn "Virtual environment not found at $VENV_DIR"
    warn "Run with --install to create it, or manually: $PYTHON_BIN -m venv .venv"
fi

VENV_PYTHON="$VENV_DIR/bin/python"
if [ -f "$VENV_PYTHON" ]; then
    pass "venv Python: $($VENV_PYTHON --version)"
fi

# ── 5. Dependency installation ────────────────────────────────────────────────
step "5. Dependencies"

if [ "$MODE_INSTALL" = true ] && [ -f "$VENV_PYTHON" ]; then
    info "Upgrading pip ..."
    "$VENV_PYTHON" -m pip install --upgrade pip --quiet

    # ── ARM64 PyTorch pre-install check ─────────────────────────────────────
    # torch pulled by ultralytics may not have an ARM64 wheel on PyPI.
    # The Pi-recommended approach is to install the PyTorch ARM64 wheel first
    # before pulling ultralytics, to avoid pip resolving an incompatible wheel.
    if [ "$ARCH" = "aarch64" ]; then
        warn "ARM64 detected: PyTorch may require a manual install step."
        warn "See deployment/README.md → 'ARM64 PyTorch Installation'."
        warn "Attempting standard pip install; this may fail for torch on Pi."
    fi

    info "Installing core runtime dependencies from requirements.txt ..."
    "$VENV_PYTHON" -m pip install -r "$PROJECT_DIR/requirements.txt" || {
        fail "pip install failed. Review ARM64 compatibility notes."
        fail "See: deployment/README.md → ARM64 section."
        exit 1
    }
    pass "Core dependencies installed"

elif [ -f "$VENV_PYTHON" ]; then
    # Check-only: verify key imports
    IMPORT_CHECKS=(fastapi uvicorn pydantic yaml PIL ultralytics serial)
    for pkg in "${IMPORT_CHECKS[@]}"; do
        if "$VENV_PYTHON" -c "import $pkg" 2>/dev/null; then
            pass "Import OK: $pkg"
        else
            fail "Import FAILED: $pkg (not installed in venv)"
        fi
    done
fi

# ── 6. Required directories ───────────────────────────────────────────────────
step "6. Required Directories"

DATA_DIRS=(
    "$PROJECT_DIR/database"
    "$PROJECT_DIR/logs"
    "$PROJECT_DIR/data"
    "$PROJECT_DIR/data/images"
    "$PROJECT_DIR/vision/weights"
)

for d in "${DATA_DIRS[@]}"; do
    if [ -d "$d" ]; then
        pass "Directory exists: $d"
    elif [ "$MODE_INSTALL" = true ]; then
        mkdir -p "$d"
        pass "Created: $d"
    else
        warn "Missing directory (will be created on --install): $d"
    fi
done

# ── 7. Configuration ──────────────────────────────────────────────────────────
step "7. Configuration"

CONFIG_FILE="$PROJECT_DIR/config/config.yaml"
if [ -f "$CONFIG_FILE" ]; then
    pass "config/config.yaml present"
else
    fail "config/config.yaml missing"
fi

ENV_FILE="$PROJECT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    pass ".env file present"
else
    warn ".env not found. Copy .env.example → .env and customize before running."
    if [ "$MODE_INSTALL" = true ]; then
        if [ -f "$PROJECT_DIR/.env.example" ]; then
            cp "$PROJECT_DIR/.env.example" "$ENV_FILE"
            warn "Copied .env.example → .env. Review and edit before starting the service."
        fi
    fi
fi

# ── 8. Database initialization ────────────────────────────────────────────────
step "8. Database Initialization"

if [ -f "$VENV_PYTHON" ] && [ "$MODE_INSTALL" = true ]; then
    info "Running startup check to initialize database ..."
    cd "$PROJECT_DIR"
    "$VENV_PYTHON" start_rover.py --check-only && pass "Database initialized via --check-only" \
        || fail "Startup check failed — review output above"
elif [ -f "$PROJECT_DIR/database/mining_rover.db" ]; then
    pass "Database file exists: database/mining_rover.db"
else
    warn "Database not yet initialized. Run: python start_rover.py --check-only"
fi

# ── 9. Vision model ───────────────────────────────────────────────────────────
step "9. Vision Model"

MODEL_PATH="$PROJECT_DIR/vision/weights/best.pt"
if [ -f "$MODEL_PATH" ]; then
    MODEL_SIZE=$(du -sh "$MODEL_PATH" | cut -f1)
    pass "YOLO weights found: vision/weights/best.pt ($MODEL_SIZE)"
else
    warn "YOLO weights NOT found at vision/weights/best.pt"
    warn "Copy your trained best.pt to: $MODEL_PATH"
    warn "Without weights, vision runs in simulated mode."
fi

# ── 10. Startup check ─────────────────────────────────────────────────────────
step "10. Startup Verification"

if [ -f "$VENV_PYTHON" ]; then
    cd "$PROJECT_DIR"
    info "Running: python start_rover.py --check-only"
    if "$VENV_PYTHON" start_rover.py --check-only; then
        pass "Startup check passed"
    else
        fail "Startup check FAILED"
    fi
else
    warn "Skipping startup check — virtual environment not ready"
fi

# ── 11. Systemd service installation ──────────────────────────────────────────
step "11. Systemd Service"

SERVICE_SRC="$PROJECT_DIR/deployment/mining-rover.service"
SERVICE_DST="/etc/systemd/system/mining-rover.service"

if [ "$MODE_INSTALL" = true ]; then
    if [ -f "$SERVICE_SRC" ]; then
        # Substitute actual project path into the service file
        info "Installing systemd service to $SERVICE_DST ..."
        sed "s|/home/rover/mining_rover|$PROJECT_DIR|g" "$SERVICE_SRC" | sudo tee "$SERVICE_DST" > /dev/null
        sudo systemctl daemon-reload
        pass "Service installed: $SERVICE_DST"
        info "Service is installed but NOT enabled/started by default."
        info "To enable at boot: sudo systemctl enable mining-rover"
        info "To start now:      sudo systemctl start mining-rover"
        info "To view logs:      journalctl -u mining-rover -f"

        if [ "$MODE_START" = true ]; then
            sudo systemctl enable mining-rover
            sudo systemctl start mining-rover
            pass "Service enabled and started"
        fi
    else
        fail "Service template not found: $SERVICE_SRC"
    fi
else
    if [ -f "$SERVICE_SRC" ]; then
        pass "Systemd service template present: deployment/mining-rover.service"
    else
        fail "Systemd service template missing: deployment/mining-rover.service"
    fi
fi

# ── Final Summary ─────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}=================================================================${RESET}"
if [ "$FAILURES" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}  Deployment Readiness: PASS (0 failures)${RESET}"
else
    echo -e "${RED}${BOLD}  Deployment Readiness: FAIL ($FAILURES failure(s) detected)${RESET}"
fi
echo -e "${BOLD}=================================================================${RESET}"
echo ""

if [ "$FAILURES" -gt 0 ]; then
    echo "Resolve the issues above before proceeding with physical deployment."
    exit 1
fi

if [ "$MODE_CHECK" = true ] && [ "$MODE_INSTALL" = false ]; then
    echo "Run with --install to perform the actual deployment."
fi

exit 0
