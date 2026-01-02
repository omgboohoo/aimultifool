# aiMultiFool v0.1.21

**The Premium Linux Terminal-Based Sandbox for Private AI Roleplay.** 
Powered by `llama.cpp` and `Textual`. Chat with local AI models using your favorite SillyTavern character cards with zero lag and full privacy.

*Vibe coded in Antigravity and Cursor using Linux Mint*

---

## ✨ Features

Looking for a detailed guide? Check out the **[USER_GUIDE.md](./USER_GUIDE.md)** for a comprehensive walkthrough.

### 🎭 Character & Content
- **Character Card Support**: Load SillyTavern PNG cards directly from the top menu.
- **AI-Assisted Editing**: Built-in **Metadata Editor** with **real-time streaming AI assistance** for generating and modifying character data without leaving the app.
    > *Tip: Use a small 8B parameter model for responsive AI editing. Larger models may loop with JSON data.*
- **Narrative Styles**: Choose from **44 custom presets** covering a wide range of tones.
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
- **Context Window Viewer**: Inspect the raw JSON context and system prompts being sent to the LLM.

---

## 🚀 Installation & Quick Start

1. **Clone and Enter**:
   ```bash
   git clone https://github.com/omgboohoo/aimultifool.git
   cd aiMultiFool
   ```

2. **Launch**:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

> [!TIP]
> **GPU Acceleration**: On first launch, `run.sh` will automatically download a **Universal Multi-Arch Wheel** (~339MB) to enable CUDA support across GTX 10-series through RTX 40-series GPUs.

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

- **Python 3.12+**
- **Linux** (Ubuntu/Debian/Mint recommended)
- **NVIDIA GPU** (Optional) - Requires Drivers and CUDA Runtime:
  ```bash
  sudo apt install nvidia-cuda-toolkit-runtime
  ```
- **Models**: GGUF format (Auto-downloads **MN-12B-Mag-Mell-R1** as default LLM and **nomic-embed-text-v2-moe** for Vector Chat)

---

## 📦 Recommended Models

- **Default LLM**: [MN-12B-Mag-Mell-R1-Uncensored.i1-Q4_K_S](https://huggingface.co/mradermacher/MN-12B-Mag-Mell-R1-Uncensored-i1-GGUF) (Auto-downloaded)
- **Embedding Model**: [nomic-embed-text-v2-moe.Q4_K_M](https://huggingface.co/nomic-ai/nomic-embed-text-v2-moe-GGUF) (Auto-downloaded) - Required for **Vector Chat (RAG)** long-term memory.
- **Smaller Option**: [L3-8B-Stheno-v3.2-Q4_K_M](https://huggingface.co/bartowski/L3-8B-Stheno-v3.2-GGUF) (~5.2 GB) - Faster, lower memory usage
- **High Quality**: [MN-12B-Mag-Mell-R1-Uncensored.i1-Q4_K_M](https://huggingface.co/mradermacher/MN-12B-Mag-Mell-R1-Uncensored-i1-GGUF) (Higher quality variant)

---

## ❤️ Support & Community

- ☕ **Support**: [Buy me a coffee on Ko-fi](https://ko-fi.com/aimultifool)
- 💬 **Discord**: [Join our community](https://discord.com/invite/J5vzhbmk35)

**License**: GPLv3

