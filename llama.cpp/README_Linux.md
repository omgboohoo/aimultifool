# Building llama-cpp-python with CUDA for Linux

This directory contains scripts to build llama-cpp-python with CUDA support for Linux systems.

## Prerequisites

1. **CUDA Toolkit**: Install the CUDA toolkit
   ```bash
   sudo apt update
   sudo apt install nvidia-cuda-toolkit
   ```

2. **Git**: Make sure git is installed
   ```bash
   sudo apt install git
   ```

3. **Python 3**: Ensure Python 3 is installed with pip

## Building with CUDA Support

Run the build script from the ShitChat root directory:

```bash
./llama.cpp/build_linux.sh
```

This script will:
1. Clone the llama-cpp-python repository
2. Pull all submodules
3. Detect your GPU's compute capability automatically
4. Build the wheel with CUDA support
5. Install the built wheel
6. Verify CUDA support

## GPU Compute Capabilities

The script automatically detects your GPU's compute capability:
- **6.1** (your detected GPU) - RTX 20-series, GTX 16-series
- **7.5** - RTX 20-series (Turing)
- **8.6** - RTX 30-series (Ampere)
- **8.9** - RTX 40-series (Ada Lovelace)

## Running ShitChat

After building, you can run ShitChat with:

```bash
./run.sh
```

The launcher will automatically detect and use the CUDA-enabled wheel if available.

## Troubleshooting

- If CUDA is not detected, the build will fall back to CPU-only
- Make sure your NVIDIA drivers are up to date
- Ensure the CUDA toolkit is properly installed and in your PATH





