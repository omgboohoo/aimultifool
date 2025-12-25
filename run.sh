#!/bin/bash

# Setup script for aiMultiFool console chat app

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/venv"
WHEEL_FILE="$SCRIPT_DIR/llama.cpp/llama_cpp_python-0.3.16-cp312-cp312-linux_x86_64.whl"

echo "Setting up aiMultiFool..."

# Check if venv already exists
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment already exists."
    read -p "Do you want to recreate it? [y/N]: " -n 1 -r
    echo
    # Default to N (no) if user just presses Enter
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing virtual environment..."
        rm -rf "$VENV_DIR"
    else
        echo "Using existing virtual environment."
        source "$VENV_DIR/bin/activate"
        echo "Virtual environment activated!"
        
        # Ensure dependencies are up to date
        echo "Checking/Updating dependencies..."
        if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
            pip install -q -r "$SCRIPT_DIR/requirements.txt"
        fi
        
        echo ""
        echo "Starting chat app..."
        echo ""
        python "$SCRIPT_DIR/aimultifool.py"
        exit 0
    fi
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install llama-cpp-python wheel
if [ -f "$WHEEL_FILE" ]; then
    echo "Installing llama-cpp-python from wheel..."
    pip install "$WHEEL_FILE"
else
    echo "Warning: Wheel file not found at $WHEEL_FILE"
    echo "Falling back to pip install llama-cpp-python..."
    pip install llama-cpp-python
fi

# Install other dependencies
echo "Installing dependencies..."
if [ -f "$SCRIPT_DIR/requirements.txt" ]; then
    pip install -r "$SCRIPT_DIR/requirements.txt"
else
    pip install rich requests tqdm textual
fi

echo ""
echo "Setup complete!"
echo ""
echo "Starting chat app..."
echo ""
python "$SCRIPT_DIR/aimultifool.py"

