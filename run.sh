#!/bin/bash

# Setup script for aiMultiFool console chat app

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
# Universal Multi-Arch Wheel Configuration
WHEEL_NAME="llama_cpp_python-0.3.16-cp312-cp312-linux_x86_64.whl"
WHEEL_URL="https://aimultifool.com/llama_cpp_python-0.3.16-cp312-cp312-linux_x86_64.whl" # Change this to your actual hosting URL
WHEEL_DIR="$SCRIPT_DIR/llama.cpp"
WHEEL_PATH="$WHEEL_DIR/$WHEEL_NAME"

echo "----------------------------------------------------------------"
echo "  aiMultiFool Suite - Setup & Launch Script v0.1.8"
echo "----------------------------------------------------------------"

# 1. Ensure the llama.cpp directory exists
if [ ! -d "$WHEEL_DIR" ]; then
    echo "[SYSTEM] Creating directory for binaries: $WHEEL_DIR"
    mkdir -p "$WHEEL_DIR"
fi

# 2. Check if the wheel exists locally, if not attempt download
if [ -f "$WHEEL_PATH" ]; then
    echo "[FOUND] Using existing local Multi-Arch wheel: $(basename "$WHEEL_PATH")"
else
    echo "[MISSING] Universal wheel not found locally."
    echo "[NETWORK] Starting download (339MB) to ensure GPU acceleration..."
    echo "[SOURCE]  $WHEEL_URL"
    
    if command -v wget &> /dev/null; then
        if ! wget --show-progress -O "$WHEEL_PATH" "$WHEEL_URL"; then
            echo "[ERROR] Download failed with wget."
            rm -f "$WHEEL_PATH"
        fi
    elif command -v curl &> /dev/null; then
        if ! curl -L -# -o "$WHEEL_PATH" "$WHEEL_URL"; then
            echo "[ERROR] Download failed with curl."
            rm -f "$WHEEL_PATH"
        fi
    else
        echo "[CRITICAL] Neither wget nor curl found. Please install one to auto-download the wheel."
        exit 1
    fi

    if [ -f "$WHEEL_PATH" ]; then
        echo "[SUCCESS] Multi-Arch wheel downloaded successfully!"
    else
        echo "[ERROR] Download failed. The app may run slowly without GPU acceleration."
    fi
fi

# Find the latest wheel
WHEEL_FILE=$(ls "$WHEEL_DIR/"llama_cpp_python-*.whl 2>/dev/null | head -n 1)

# Check if venv already exists
if [ -d "$VENV_DIR" ]; then
    echo "[STATUS] Virtual environment detected."
    read -p "[PROMPT] Recreate environment (fix dependencies)? [y/N]: " -t 5 -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "[CLEANUP] Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        echo "[ACTIVATE] Entering existing environment..."
        source "$VENV_DIR/bin/activate"
        
        echo "[CHECK] Verifying/Updating core requirements..."
        if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
            pip install -q -r "$SCRIPT_DIR/requirements.txt"
        fi
        
        echo "[LAUNCH] Starting aiMultiFool TUI..."
        echo ""
        python "$SCRIPT_DIR/aimultifool.py"
        exit 0
    fi
fi

# Create virtual environment
echo "[STEP 1/4] Creating fresh virtual environment (venv)..."
python3 -m venv "$VENV_DIR"

# Activate virtual environment
echo "[STEP 2/4] Activating environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "[STEP 3/4] Upgrading pip to latest version..."
pip install -q --upgrade pip

# Install llama-cpp-python wheel
if [ -n "$WHEEL_FILE" ] && [ -f "$WHEEL_FILE" ]; then
    echo "[STEP 4/4] Installing Multi-Arch CUDA Backend: $(basename "$WHEEL_FILE")"
    pip install -q "$WHEEL_FILE"
    echo "[SUCCESS] CUDA Backend installed."
else
    echo "[WARNING] No pre-built wheel found. Falling back to generic install (CPU only if no toolkit)..."
    CMAKE_ARGS="-DGGML_CUDA=on" pip install -q llama-cpp-python
fi

# Install other dependencies
echo "[FINISHING] Finalizing remaining dependencies..."
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    pip install -q -r "$SCRIPT_DIR/requirements.txt"
else
    pip install -q rich requests tqdm textual
fi

echo "[DONE] Setup complete! Launching..."
echo ""
python "$SCRIPT_DIR/aimultifool.py"

