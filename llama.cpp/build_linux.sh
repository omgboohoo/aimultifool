#!/bin/bash

# Build llama-cpp-python with CUDA support for Linux
# Based on the Windows instructions but adapted for Linux

set -e  # Exit on any error

echo "Building llama-cpp-python with CUDA support for Linux..."
echo "========================================================"

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Please run this script from the ShitChat root directory"
    exit 1
fi

# Check if CUDA is available
if ! command -v nvcc &> /dev/null; then
    echo "Error: CUDA toolkit (nvcc) not found. Please install CUDA toolkit first."
    echo "You can install it with: sudo apt install nvidia-cuda-toolkit"
    exit 1
fi

# Check if git is available
if ! command -v git &> /dev/null; then
    echo "Error: git not found. Please install git first."
    exit 1
fi

# Create build directory
BUILD_DIR="llama_cpp_build"
if [ -d "$BUILD_DIR" ]; then
    echo "Removing existing build directory..."
    rm -rf "$BUILD_DIR"
fi

mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

echo "1. Cloning llama-cpp-python repository..."
git clone https://github.com/abetlen/llama-cpp-python.git
cd llama-cpp-python

echo "2. Pulling submodules..."
git submodule update --init --recursive

echo "3. Setting up CUDA build environment..."
# Get GPU compute capability
COMPUTE_CAP=$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader,nounits | head -1)
# Convert to integer (e.g., 6.1 -> 61)
COMPUTE_CAP_INT=$(echo "$COMPUTE_CAP" | sed 's/\.//')

echo "Detected GPU compute capability: $COMPUTE_CAP (using $COMPUTE_CAP_INT)"

# Set CUDA build flags for Linux
export CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=$COMPUTE_CAP_INT"
export FORCE_CMAKE="1"

echo "4. Building the wheel..."
python3 -m pip wheel . --wheel-dir dist

echo "5. Installing the built wheel..."
# Install to the current virtual environment if it exists, otherwise skip installation
if [[ "$VIRTUAL_ENV" != "" ]]; then
    pip install dist/llama_cpp_python-*.whl --force-reinstall
else
    echo "No virtual environment detected. Wheel built successfully but not installed."
    echo "The wheel file is located at: $(pwd)/dist/llama_cpp_python-*.whl"
    echo "You can install it later with: pip install dist/llama_cpp_python-*.whl"
fi

echo "6. Verifying CUDA support..."
python3 -c "from llama_cpp import Llama; print('CUDA Support:', 'CUDA' in Llama.build_info())"

echo ""
echo "Build completed successfully!"
echo "The wheel file is located in: $(pwd)/dist/"
echo "You can now use the updated run.sh script to launch ShitChat with CUDA support."
