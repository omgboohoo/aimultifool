# Building llama-cpp-python with CUDA for Windows

This directory contains scripts to build a portable, multi-architecture `llama-cpp-python` wheel for Windows systems.

## Prerequisites

1. **CUDA Toolkit**: Install the CUDA toolkit from NVIDIA
   - Download from: https://developer.nvidia.com/cuda-downloads
   - Make sure `nvcc` is available in your PATH after installation
   - Verify installation: `nvcc --version`

2. **Git**: Make sure git is installed
   - Download from: https://git-scm.com/download/win
   - Verify installation: `git --version`

3. **Python 3**: Ensure Python 3 is installed with pip
   - Download from: https://www.python.org/downloads/
   - Verify installation: `python --version`

4. **Visual Studio Build Tools** (usually installed with CUDA, but may be required separately)
   - The CUDA toolkit typically includes the necessary build tools
   - If you encounter build errors, install Visual Studio Build Tools: https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022

## Building with Multi-Arch CUDA Support

Run the build script from the **aiMultiFool** root directory:

```cmd
llama.cpp\build_windows.bat
```

Or from the llama.cpp directory:

```cmd
cd llama.cpp
build_windows.bat
```

This script will:
1. Clone the `llama-cpp-python` repository.
2. Pull all submodules (including `llama.cpp`).
3. Build a **Fat Binary** supporting multiple GPU architectures:
   - **7.5 (Turing)**: RTX 2000 series, GTX 1600 series
   - **8.6 (Ampere)**: RTX 3000 series (e.g., RTX 3060 Ti, 3090)
   - **8.9 (Ada Lovelace)**: RTX 4000 series (e.g., RTX 4070, 4090)
   - **10.0 (Blackwell)**: RTX 5000 series (e.g., RTX 5070, 5090)
4. Build the `.whl` file and copy it to the `llama.cpp/` project folder.
5. Install the wheel to your current virtual environment (if one is active).
6. Verify CUDA support.

> **Note:** CUDA 13.x dropped support for Pascal (GTX 10-series). If you have a GTX 10-series GPU, you'll need to use an older CUDA version or run in CPU mode.

## Running aiMultiFool

After building, you can run the app with:

```cmd
python aimultifool.py
```

The app will automatically detect and use the CUDA-enabled wheel. Because this build is "Multi-Arch," you can share the resulting `.whl` file across different Windows machines with different NVIDIA GPUs (from the 10-series to 40-series) and it will work without crashing.

## GPU Acceleration

The app uses GPU acceleration by default when a CUDA-enabled wheel is installed. You can configure the number of GPU layers in the app settings:
- `-1` = Auto-detect (tries to use all layers, falls back if needed)
- `0` = CPU only
- `N` = Use N layers on GPU

## Troubleshooting

- **CUDA not detected**: The build will fall back to CPU-only if CUDA is not available. Make sure:
  - NVIDIA drivers are up to date
  - CUDA toolkit is properly installed
  - `nvcc` is in your PATH (restart command prompt after installing CUDA)
  
- **Build errors**: 
  - Ensure Visual Studio Build Tools are installed
  - Make sure you have enough disk space (build requires several GB)
  - Check that all prerequisites are installed correctly
  - If using Visual Studio 2024+, the build script automatically adds `-allow-unsupported-compiler`

- **Import errors after installation**:
  - Make sure you're using the same Python environment where you installed the wheel
  - Try reinstalling: `pip install llama.cpp\llama_cpp_python-*.whl --force-reinstall`

- **GPU not being used**:
  - Verify CUDA support: `py -c "from llama_cpp import Llama; print('CUDA Support:', 'CUDA' in Llama.build_info())"`
  - Check that your GPU is supported (GTX 16-series or newer with CUDA 13.x)
  - Ensure GPU layers setting is not set to 0 in the app

