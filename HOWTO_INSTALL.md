# How to Install aiMultiFool

Follow these instructions to get **aiMultiFool** up and running on your system.

## 🚀 Installation & Quick Start

> [!NOTE]
> In testing, we have found **Linux** to be the premium **aiMultiFool** experience, while **Windows** tends to be more efficient with GPU VRAM management (offering more layer offloading availability).

---

### Linux

1. **Prerequisites**:
   - **Python 3.12** is strictly required.
   - **CUDA Toolkit** (Optional but recommended for GPU acceleration): `sudo apt install nvidia-cuda-toolkit-runtime`

2. **Download and Extract**:
   - [Download aiMultiFool (ZIP)](https://github.com/omgboohoo/aimultifool/archive/refs/heads/main.zip)
   - Extract the ZIP and open the folder (`aimultifool-main`).

3. **Launch**:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

---

### Windows

> [!IMPORTANT]
> Python 3.12 and a compatible CUDA 13.1 runtime are required on Windows.
> This is due to the pre-built `llama.cpp` wheels used by the application and applies even for CPU-only systems.

1. **Prerequisites**:
   - **Python 3.12.10**: [Download Here](https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe)
     - *DURING INSTALLATION: You **MUST** check the box that says **"Add python.exe to PATH"***
   - **CUDA Toolkit 13.1**: [Download Here](https://developer.download.nvidia.com/compute/cuda/13.1.0/local_installers/cuda_13.1.0_windows.exe)
     - *(Required even for CPU-only usage)*

2. **Download and Extract**:
   - [Download aiMultiFool (ZIP)](https://github.com/omgboohoo/aimultifool/archive/refs/heads/main.zip)
   - Right-click the downloaded file and select **Extract All...**
   - Open the extracted folder (`aimultifool-main`).

3. **Launch**:
   - Double-click `run.bat`

> [!TIP]
> **GPU Acceleration**: On first launch, `run.bat` will automatically download a **Windows Multi-Arch Wheel** (~235MB) to enable CUDA support across GTX 10-series through RTX 40-series GPUs.

---

## 🛠️ Requirements

- **Python 3.12+** (Version **3.12.x** is highly recommended for compatibility with pre-built GPU wheels)
- **Operating System**: 
  - **Linux** (Ubuntu/Debian/Mint recommended)
  - **Windows 10/11** (Windows 10+ recommended)
- **CUDA Runtime 13.1+**:
  - **Windows**: [CUDA Toolkit 13.1](https://developer.download.nvidia.com/compute/cuda/13.1.0/local_installers/cuda_13.1.0_windows.exe) is **strictly mandatory** for the app to launch.
  - **Linux**: `sudo apt install nvidia-cuda-toolkit-runtime` (Required for GPU acceleration).
- **NVIDIA GPU**: (Optional) Required for GPU acceleration. GTX 10-series or newer recommended.
- **Models**: GGUF format (Auto-downloads **L3-8B-Stheno-v3.2** as default LLM and **nomic-embed-text-v2-moe** for Vector Chat)

---

## 📦 Recommended Models

### 📥 Auto-Downloaded (Standard)
- **Default LLM**: [L3-8B-Stheno-v3.2-Q4_K_M](https://huggingface.co/bartowski/L3-8B-Stheno-v3.2-GGUF/resolve/main/L3-8B-Stheno-v3.2-Q4_K_M.gguf?download=true)
- **Embedding Model**: [nomic-embed-text-v2-moe.Q4_K_M](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe-GGUF/resolve/main/nomic-embed-text-v2-moe.Q4_K_M.gguf?download=true) - Required for **Vector Chat (RAG)** long-term memory.

### 🌟 Optional Alternatives
- **CPU/Low-Spec Option**: [Llama-3.2-3B-Instruct-uncensored-Q4_K_M](https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-uncensored-GGUF/resolve/main/Llama-3.2-3B-Instruct-uncensored-Q4_K_M.gguf?download=true) (Small 3B model, fast on systems without a GPU)
- **High Quality Option**: [MN-12B-Mag-Mell-R1-Uncensored.i1-Q4_K_M](https://huggingface.co/mradermacher/MN-12B-Mag-Mell-R1-Uncensored-i1-GGUF/resolve/main/MN-12B-Mag-Mell-R1-Uncensored.i1-Q4_K_M.gguf?download=true) (Larger 12B model, higher quality)
