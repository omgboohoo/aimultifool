#!/bin/bash

# Build llama-cpp-python with CUDA support for Linux
# Optimized for portability across multiple GPU generations (Fat Binary)

set -e  # Exit on any error

echo "Building aiMultiFool llama-cpp-python with Multi-Arch CUDA support..."
echo "===================================================================="

# Check if we're in the right directory (check for aimultifool.py or similar)
if [ ! -f "aimultifool.py" ] && [ ! -f "../aimultifool.py" ]; then
    echo "Error: Please run this script from the aiMultiFool root directory"
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

echo "3. Setting up Multi-Architecture CUDA build environment..."
# 61 = Pascal (10-series), 75 = Turing (20-series/16-series), 86 = Ampere (30-series), 89 = Ada (40-series)
export CMAKE_ARGS="-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=61;75;86;89"
export FORCE_CMAKE="1"

echo "Using architectures: 6.1, 7.5, 8.6, 8.9"

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

# Determine destination for the wheel in the main project
DEST_DIR="../../llama.cpp"
if [ -d "$DEST_DIR" ]; then
    echo "6. Copying built wheel to project directory..."
    cp dist/llama_cpp_python-*.whl "$DEST_DIR/"
    echo "Wheel copied to $DEST_DIR"
fi

echo "7. Verifying CUDA support..."
python3 -c "from llama_cpp import Llama; print('CUDA Support:', 'CUDA' in Llama.build_info())"

echo ""
echo "Build completed successfully!"
echo "The wheel file is optimized for GTX 10-series through RTX 40-series."
echo "You can now run aiMultiFool on different machines with different NVIDIA GPUs."
