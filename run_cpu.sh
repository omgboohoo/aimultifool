#!/bin/bash

# Setup script for aiMultiFool console chat app (CPU-only mode)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv_cpu"

echo "----------------------------------------------------------------"
echo "  aiMultiFool Suite - CPU-Only Setup & Launch Script v0.1.9"
echo "----------------------------------------------------------------"

# Check if venv already exists
if [ -d "$VENV_DIR" ]; then
    echo "[STATUS] Virtual environment detected."
    echo "[INFO]   It is recommended to reinstall (y) if you just updated to a new version."
    read -p "Do you want to reinstall the environment? [y/N] (Default: n): " choice
    if [[ "$choice" =~ ^[yY]$ ]]; then
        echo "[ACTION] Reinstalling environment..."
        rm -rf "$VENV_DIR"
    else
        echo "[SKIP] Skipping environment setup."
        source "$VENV_DIR/bin/activate"
        echo "[LAUNCH] Starting aiMultiFool TUI (CPU mode)..."
        echo ""
        python "$SCRIPT_DIR/aimultifool.py" --cpu
        exit 0
    fi
fi

# Create virtual environment
echo "[STEP 1/3] Creating fresh virtual environment (venv_cpu)..."
python3 -m venv "$VENV_DIR"

# Activate virtual environment
echo "[STEP 2/3] Activating environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "[STEP 3/3] Upgrading pip to latest version..."
pip install -q --upgrade pip

# Install llama-cpp-python (CPU-only, no CUDA)
echo "[INSTALL] Installing llama-cpp-python (CPU-only)..."
pip install -q llama-cpp-python

# Install other dependencies
echo "[FINISHING] Finalizing remaining dependencies..."
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    pip install -q -r "$SCRIPT_DIR/requirements.txt"
else
    pip install -q rich requests tqdm textual
fi

echo "[DONE] Setup complete! Launching in CPU mode..."
echo ""
python "$SCRIPT_DIR/aimultifool.py" --cpu
