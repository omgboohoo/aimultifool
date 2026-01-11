# aiMultiFool v0.2.1

**The Premium Cross-Platform Terminal-Based Sandbox for Private AI Roleplay.** 
Powered by `llama.cpp` and `Textual`. Chat with local AI models using your favorite SillyTavern character cards with zero lag and full privacy.

*Vibe coded in Antigravity and Cursor using Linux Mint*

---

## ✨ Features

### 🎭 Character & Content
- **Character Card Support**: Load SillyTavern PNG cards directly from the top menu.
- **AI-Assisted Editing**: Built-in **Metadata Editor** with **real-time streaming AI assistance** for generating and modifying character data without leaving the app.
    > *Tip: Use a small model like **Llama-3.2-3B-Instruct-uncensored-Q4_K_M** for responsive AI editing.*
- **Narrative Styles**: Choose from **45 custom presets** covering a wide range of tones.
- **On-Demand Encryption**: Secure individual character cards with **AES-256-GCM** encryption.
- **Vector Chat (RAG)**: Enhance roleplay with long-term memory via local vector databases. Supports optional **AES-256-GCM** encryption for database payloads. Duplicate, rename, and manage multiple knowledge bases with ease.

### ⚡ AI & Performance
- **Real-time Metrics**: Live TPS, Token counts, and Context % usage.
- **Smart Pruning**: Automatically manages context window by trimming middle-history while preserving the System Prompt, first 3 exchanges (for early roleplay context), and the last message. Deletes messages one by one from the middle until reaching 60% context usage. Triggers at 85% context usage. Chat window automatically syncs to match the pruned context exactly.
- **GPU/CPU Auto-Detection**: Optimized layer loading with configuration caching for faster subsequent loads.
- **Advanced Parameters**: Precise control over Temperature, Top P, Top K, Repeat Penalty, and **Min P**.

### 🔒 Privacy & Security
- **Secure Chats**: **File** menu to save and load conversation histories with optional **AES-256-GCM** encryption and **Argon2id** key derivation.
- **Transparent Passphrases**: Password fields are visible by default to prevent entry errors.
- **Private Roleplay**: 100% local inference with zero data leakage.

### 🛠️ Interface & Tools
- **Minimalist TUI**: Pure Textual interface styled via external `.tcss` for fast, clean roleplay aesthetics.
- **Theme Support**: Choose from 11 built-in themes including Textual Dark/Light, Catppuccin, Dracula, Gruvbox, Monokai, Nord, Solarized, Tokyo Night, and Flexoki. Themes apply consistently across the entire interface.
- **Action Sidebar**: Right Sidebar containing roleplay tools and system prompts.
- **Action Manager**: Full in-app manager with real-time search and category filtering.
- **Emotion Dynamics**: Automatic character emotion analysis displayed in a dedicated sidebar panel, showing how each character feels after each AI reply.
- **Context Window Viewer**: Inspect the raw JSON context and system prompts being sent to the LLM. Accessible via the About screen.

---

## 🚀 Installation & Quick Start

> [!NOTE]
> In testing, we have found **Linux** to be the premium **aiMultiFool** experience, while **Windows** tends to be more efficient with GPU VRAM management (offering more layer offloading availability).

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

> [!NOTE]
> **GPU Acceleration**: On first launch, `run.sh` will automatically download a **Linux Multi-Arch Wheel** (~339MB) to enable CUDA support across GTX 10-series through RTX 40-series GPUs.

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

> [!NOTE]
> **GPU Acceleration**: On first launch, `run.bat` will automatically download a **Windows Multi-Arch Wheel** (~235MB) to enable CUDA support across GTX 10-series through RTX 40-series GPUs.
> 


---

## ⌨️ Essential Shortcuts

| Shortcut | Action |
| :--- | :--- |
| **Ctrl+S** | Stop AI generation |
| **Ctrl+Enter** | Trigger AI "Continue" |
| **Ctrl+Z** | Rewind (Undo last user/assistant interaction) |
| **Ctrl+R** | Restart conversation from the beginning |
| **Ctrl+Shift+W** | Clear chat history completely |
| **Ctrl+Q** | Quit Application |

---

## 🧠 Understanding Sampling (Chaos Mode)

If you've ever set **Temperature** to 2.0 and noticed the AI still sounds perfectly sane, it's because of the **Sampling Order**. Parameters act like a series of filters (or "Bouncers").

1. **The Bouncers (Top P / Top K)**: These act first. If Top P is 0.9 and Top K is 40, they "execute" 99.9% of possible word choices before the dice are even rolled. Usually, only a few "safe" words remain.
2. **The Dice (Temperature)**: Temperature then tries to "scramble" the remaining choices. But if the Bouncers only left a few boring words, Temperature has nothing to work with.

### To Induce Chaos:
1. Open the **Parameters** modal (top menu).
2. Set **Top P** to `1.0` and **Top K** to `0` (stands down the bouncers).
3. Set **Temperature** to `1.8` or higher.
4. Set **Min P** to `0.05` for "smart" chaos.

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

---

## ❤️ Support & Community

- ☕ **Support**: [Buy me a coffee on Ko-fi](https://ko-fi.com/aimultifool)
- 💬 **Discord**: [Join our community](https://discord.com/invite/J5vzhbmk35)

**License**: GPLv3

