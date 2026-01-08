# Building llama-cpp-python with CUDA for Linux

This directory contains scripts to build a portable, multi-architecture `llama-cpp-python` wheel for Linux systems.

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

## Building with Multi-Arch CUDA Support

Run the build script from the **aiMultiFool** root directory:

```bash
./llama.cpp/build_linux.sh
```

This script will:
1. Clone the `llama-cpp-python` repository.
2. Pull all submodules (including `llama.cpp`).
3. Build a **Fat Binary** supporting multiple GPU architectures:
   - **6.1 (Pascal)**: GTX 1000 series (e.g., GTX 1070, 1080 Ti)
   - **7.5 (Turing)**: RTX 2000 series, GTX 1600 series
   - **8.6 (Ampere)**: RTX 3000 series (e.g., RTX 3060 Ti, 3090)
   - **8.9 (Ada Lovelace)**: RTX 4000 series (e.g., RTX 4070, 4090)
4. Build the `.whl` file and copy it to the `llama.cpp/` project folder.
5. Install the wheel to your current virtual environment.
6. Verify CUDA support.

## Running aiMultiFool

After building, you can run the app with:

```bash
./run.sh
```

The launcher will automatically detect and use the CUDA-enabled wheel. Because this build is "Multi-Arch," you can share the resulting `.whl` file across different Linux machines with different NVIDIA GPUs (from the 10-series to 40-series) and it will work without crashing.

## Troubleshooting

- If CUDA is not detected, the build will fall back to CPU-only.
- Make sure your NVIDIA drivers are up to date.
- Ensure the CUDA toolkit is properly installed and `nvcc` is in your PATH.
- If you switch machine types frequently, deleting the `venv` folder and runing `./run.sh` will ensure the correct wheel is re-indexed.





