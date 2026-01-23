#!/bin/bash

# Setup script for aiMultiFool console chat app (CPU-only mode)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv_cpu"
PYTHON_PORTABLE_DIR="$SCRIPT_DIR/python_portable"
PYTHON_PORTABLE_TAR="cpython-3.12.12+20260114-x86_64-unknown-linux-gnu-install_only.tar.gz"
PYTHON_PORTABLE_URL="https://aimultifool.com/$PYTHON_PORTABLE_TAR"
PYTHON_PORTABLE_TAR_PATH="$PYTHON_PORTABLE_DIR/$PYTHON_PORTABLE_TAR"
PYTHON_CMD="python3"

echo "----------------------------------------------------------------"
echo "  aiMultiFool Suite - CPU-Only Setup & Launch Script v0.1.9"
echo "----------------------------------------------------------------"

# 0. Setup Portable Python
if [ ! -f "$PYTHON_PORTABLE_DIR/bin/python3" ]; then
    echo "[PYTHON] Portable Python not found. Setting up..."
    
    # Create python_portable directory
    mkdir -p "$PYTHON_PORTABLE_DIR"
    
    # Download portable Python if tar doesn't exist
    if [ ! -f "$PYTHON_PORTABLE_TAR_PATH" ]; then
        echo "[NETWORK] Downloading portable Python 3.12 (~50MB)..."
        echo "[SOURCE]  $PYTHON_PORTABLE_URL"
        
        if command -v wget &> /dev/null; then
            if ! wget --show-progress -O "$PYTHON_PORTABLE_TAR_PATH" "$PYTHON_PORTABLE_URL"; then
                echo "[ERROR] Download failed with wget."
                rm -f "$PYTHON_PORTABLE_TAR_PATH"
                echo "[FALLBACK] Will use system Python instead."
            fi
        elif command -v curl &> /dev/null; then
            if ! curl -L -# -o "$PYTHON_PORTABLE_TAR_PATH" "$PYTHON_PORTABLE_URL"; then
                echo "[ERROR] Download failed with curl."
                rm -f "$PYTHON_PORTABLE_TAR_PATH"
                echo "[FALLBACK] Will use system Python instead."
            fi
        else
            echo "[WARNING] Neither wget nor curl found. Will use system Python."
        fi
    fi
    
    # Extract portable Python if tar exists
    if [ -f "$PYTHON_PORTABLE_TAR_PATH" ]; then
        echo "[EXTRACT] Extracting portable Python..."
        tar -xzf "$PYTHON_PORTABLE_TAR_PATH" -C "$PYTHON_PORTABLE_DIR" --strip-components=1
        if [ -f "$PYTHON_PORTABLE_DIR/bin/python3" ]; then
            PYTHON_CMD="$PYTHON_PORTABLE_DIR/bin/python3"
            echo "[SUCCESS] Portable Python ready!"
        else
            echo "[WARNING] Extraction may have failed. Using system Python."
        fi
    fi
else
    PYTHON_CMD="$PYTHON_PORTABLE_DIR/bin/python3"
    echo "[PYTHON] Using portable Python: $PYTHON_CMD"
fi

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
"$PYTHON_CMD" -m venv "$VENV_DIR"

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
