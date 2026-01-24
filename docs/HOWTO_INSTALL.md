# How to Install aiMultiFool v0.4.9

Follow these instructions to get **aiMultiFool** up and running on your system.

## 🚀 Installation & Quick Start

> [!NOTE]
> In testing, we have found **Linux** to be the premium **aiMultiFool** experience, while **Windows** tends to be more efficient with GPU VRAM management (offering more layer offloading availability).

---

## 🎮 GPU Mode Installation (Recommended for NVIDIA GPU users)

GPU mode provides accelerated inference using your NVIDIA GPU. This requires CUDA toolkit installation.

### Linux (GPU Mode)

1. **Prerequisites**:
   - **CUDA Toolkit** (Required for GPU acceleration): `sudo apt install nvidia-cuda-toolkit-runtime`
   - **NVIDIA GPU** with compatible drivers
   - *Python 3.12.12 is automatically bundled - no installation required!*

2. **Download and Extract**:
   - [Download aiMultiFool (ZIP)](https://github.com/omgboohoo/aimultifool/archive/refs/heads/main.zip)
   - Extract the ZIP and open the folder (`aimultifool-main`).

3. **Launch**:
   ```bash
   chmod +x run_linux_gpu.sh
   ./run_linux_gpu.sh
   ```

> [!TIP]
> **Automatic Setup**: On first launch, `run_linux_gpu.sh` will automatically:
> - Download and extract **Portable Python 3.12.12** (~50MB)
> - Download a **Multi-Arch Wheel** (~339MB) to enable CUDA support across GTX 10-series through RTX 40-series GPUs

---

### Windows (GPU Mode)

> [!IMPORTANT]
> A compatible CUDA 13.1 runtime is required for GPU mode on Windows.

1. **Prerequisites**:
   - **CUDA Toolkit 13.1**: [Download Here](https://developer.download.nvidia.com/compute/cuda/13.1.0/local_installers/cuda_13.1.0_windows.exe)
     - *(Required for GPU acceleration)*
   - **NVIDIA GPU** with compatible drivers
   - *Python 3.12.12 is automatically bundled - no installation required!*

2. **Download and Extract**:
   - [Download aiMultiFool (ZIP)](https://github.com/omgboohoo/aimultifool/archive/refs/heads/main.zip)
   - Right-click the downloaded file and select **Extract All...**
   - Open the extracted folder (`aimultifool-main`).

3. **Launch**:
   - Double-click `run_windows_gpu.bat`

> [!TIP]
> **Automatic Setup**: On first launch, `run_windows_gpu.bat` will automatically:
> - Download and extract **Portable Python 3.12.12** (~50MB)
> - Download a **Windows Multi-Arch Wheel** (~235MB) to enable CUDA support across GTX 10-series through RTX 40-series GPUs

---

## 💻 CPU Mode Installation (For systems without NVIDIA GPU)

CPU mode runs entirely on your CPU without requiring CUDA toolkit or NVIDIA drivers. This is simpler to set up but will be slower than GPU mode.

### Linux (CPU Mode)

1. **Prerequisites**:
   - *No CUDA toolkit required!*
   - *Python 3.12.12 is automatically bundled - no installation required!*

2. **Download and Extract**:
   - [Download aiMultiFool (ZIP)](https://github.com/omgboohoo/aimultifool/archive/refs/heads/main.zip)
   - Extract the ZIP and open the folder (`aimultifool-main`).

3. **Launch**:
   ```bash
   chmod +x run_linux_cpu.sh
   ./run_linux_cpu.sh
   ```

> [!NOTE]
> **Automatic Setup**: On first launch, `run_linux_cpu.sh` will automatically:
> - Download and extract **Portable Python 3.12.12** (~50MB)
> - Install the CPU-only version of `llama-cpp-python` without any CUDA dependencies
> 
> This is perfect for systems without NVIDIA GPUs or when you want a simpler setup.

---

### Windows (CPU Mode)

1. **Prerequisites**:
   - *No CUDA toolkit required!*
   - *Python 3.12.12 is automatically bundled - no installation required!*

2. **Download and Extract**:
   - [Download aiMultiFool (ZIP)](https://github.com/omgboohoo/aimultifool/archive/refs/heads/main.zip)
   - Right-click the downloaded file and select **Extract All...**
   - Open the extracted folder (`aimultifool-main`).

3. **Launch**:
   - Double-click `run_windows_cpu.bat`

> [!NOTE]
> **Automatic Setup**: On first launch, `run_windows_cpu.bat` will automatically:
> - Download and extract **Portable Python 3.12.12** (~50MB)
> - Install the CPU-only version of `llama-cpp-python` without any CUDA dependencies
> 
> This is perfect for systems without NVIDIA GPUs or when you want a simpler setup.

---

## 🛠️ Requirements Summary

### GPU Mode Requirements
- **Python 3.12.12** (Automatically bundled - no installation required)
- **Operating System**: 
  - **Linux** (Ubuntu/Debian/Mint recommended)
  - **Windows 10/11** (Windows 10+ recommended)
- **CUDA Runtime 13.1+**:
  - **Windows**: [CUDA Toolkit 13.1](https://developer.download.nvidia.com/compute/cuda/13.1.0/local_installers/cuda_13.1.0_windows.exe) is **required** for GPU acceleration.
  - **Linux**: `sudo apt install nvidia-cuda-toolkit-runtime` (Required for GPU acceleration).
- **NVIDIA GPU**: Required for GPU acceleration. GTX 10-series or newer recommended.
- **Models**: GGUF format (Auto-downloads **L3-8B-Stheno-v3.2** as default LLM and **nomic-embed-text-v2-moe** for Vector Chat)

### CPU Mode Requirements
- **Python 3.12.12** (Automatically bundled - no installation required)
- **Operating System**: 
  - **Linux** (Ubuntu/Debian/Mint recommended)
  - **Windows 10/11** (Windows 10+ recommended)
- **No CUDA toolkit required!**
- **No NVIDIA GPU required!**
- **Models**: GGUF format (Auto-downloads **L3-8B-Stheno-v3.2** as default LLM and **nomic-embed-text-v2-moe** for Vector Chat)

---

## 📦 Recommended Models

### 📥 Auto-Downloaded (Standard)
- **Default LLM**: [L3-8B-Stheno-v3.2-Q4_K_M](https://huggingface.co/bartowski/L3-8B-Stheno-v3.2-GGUF/resolve/main/L3-8B-Stheno-v3.2-Q4_K_M.gguf?download=true)
- **Embedding Model**: [nomic-embed-text-v2-moe.Q4_K_M](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe-GGUF/resolve/main/nomic-embed-text-v2-moe.Q4_K_M.gguf?download=true) - Required for **Vector Chat (RAG)** long-term memory.

### 🌟 Optional Alternatives
- **CPU/Low-Spec Option**: [Llama-3.2-3B-Instruct-uncensored-Q4_K_M](https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-uncensored-GGUF/resolve/main/Llama-3.2-3B-Instruct-uncensored-Q4_K_M.gguf?download=true) (Small 3B model, fast on systems without a GPU)
- **High Quality Option**: [MN-12B-Mag-Mell-R1-Uncensored.i1-Q4_K_M](https://huggingface.co/mradermacher/MN-12B-Mag-Mell-R1-Uncensored-i1-GGUF/resolve/main/MN-12B-Mag-Mell-R1-Uncensored.i1-Q4_K_M.gguf?download=true) (Larger 12B model, higher quality)

---

## 🔄 Switching Between GPU and CPU Modes

Each mode uses its own virtual environment (`venv_gpu` or `venv_cpu`) to avoid conflicts:

- **GPU Mode**: Uses `run_linux_gpu.sh` / `run_windows_gpu.bat` → creates `venv_gpu`
- **CPU Mode**: Uses `run_linux_cpu.sh` / `run_windows_cpu.bat` → creates `venv_cpu`

You can have both environments installed simultaneously and switch between them by running the appropriate script.

---

## ❓ Which Mode Should I Use?

- **Use GPU Mode** if:
  - You have an NVIDIA GPU (GTX 10-series or newer)
  - You want faster inference speeds
  - You're comfortable installing CUDA toolkit

- **Use CPU Mode** if:
  - You don't have an NVIDIA GPU
  - You want a simpler installation (no CUDA toolkit)
  - You're okay with slower inference speeds
  - You're on a system where CUDA installation is difficult
