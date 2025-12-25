# aiMultiFool v0.1.0

The Premium Linux Terminal-Based Sandbox for Private AI Roleplay. Powered by `llama.cpp` and `Textual`. Chat with local AI models using your favorite SillyTavern character cards with zero lag and full privacy.

*Vibe coded in Antigravity with Gemini 3 Flash using Linux Mint*

## Features

- 🎭 **Character Card Support**: Load SillyTavern PNG cards directly from the sidebar.
- ⚡ **Real-time Metrics**: Live TPS, Token counts, and Context % usage.
- 💾 **Smart Pruning**: Automatically manages context window by trimming old history.
- 💻 **GPU/CPU Auto-Detection**: Optimized layer loading with configuration caching.
- 🎨 **Minimalist TUI**: Pure Textual interface styled via external `.tcss` for fast, clean roleplay aesthetics.
- 🏗️ **Advanced Modular Architecture**: State-of-the-art codebase using Mixins, separate logic/UI modules, and external styling for maximum maintainability.
- 🎭 **Narrative Styles**: Choose from 20 custom presets covering a wide range of tones including Concise, Descriptive, Dramatic, Horror, Whimsical, Erotic, and more.
- 🔧 **Sidebar Controls**: Left Sidebar for Model selection, Context Size, GPU layers, and AI sampling.
- 💬 **Action Sidebar**: Right Sidebar (Action Menu) containing roleplay tools and system prompts. Features a full in-app **Editor** to add, modify, or delete custom actions on the fly.
- ✨ **Dynamic Messaging**: Instant message mounting and rendering with automatic scroll-to-bottom for a fluid roleplay experience.
- 💾 **Settings Persistence**: Your Username, Model, and UI preferences are saved and reloaded automatically.
- ⌨️ **Keyboard Guided**: Fast shortcuts for Rewinding, Stopping, and Sidebars toggle.

## Installation

1. Clone and enter the directory:
   ```bash
   git clone https://github.com/omgboohoo/aimultifool.git
   cd aiMultiFool
   ```

2. Run the launch script:
   ```bash
   chmod +x run.sh
   ./run.sh
   ```

## Requirements

- Python 3.12+
- Linux (Ubuntu/Debian/Mint recommended)
- Windows (Coming Soon)
- Compatible GGUF models (Auto-downloads default if missing)

## Usage

- **Sidebars (Ctrl+B)**: Toggle both Settings/Character selection (left) and Action Menu (right).
- **Stop (Ctrl+S)**: Interrupt the AI while it's typing.
- **Continue (Ctrl+Enter)**: Trigger the AI to continue its thought or respond to an empty prompt.
- **Rewind (Ctrl+Z)**: Remove the last interaction (your prompt and the AI's reply).
- **Restart (Ctrl+R)**: Reset conversation to the start.
- **Clear (Ctrl+Shift+W)**: Wipe chat history completely.
- **Quit (Ctrl+Q)**: Exit application.

Place your `.gguf` files in `models/` and SillyTavern cards in `cards/`.

#### Recommended Models

**Default Model:**
- **L3-8B-Stheno-v3.2-Q4_K_M** - Automatically downloaded if no models are found
  - Size: ~5.2 GB
  - Source: [bartowski/L3-8B-Stheno-v3.2-GGUF](https://huggingface.co/bartowski/L3-8B-Stheno-v3.2-GGUF)

**Recommended 12B Model:**
- **MN-12B-Mag-Mell-R1-Uncensored-i1-GGUF** - High-quality 12B parameter model
  - Recommended quants:
    - `i1-Q4_K_S` (7.2 GB) - Optimal size/speed/quality balance
    - `i1-Q4_K_M` (7.6 GB) - Fast, recommended
    - `i1-Q5_K_M` (8.8 GB) - Higher quality option
    - `i1-Q6_K` (10.2 GB) - Highest quality
  - Source: [mradermacher/MN-12B-Mag-Mell-R1-Uncensored-i1-GGUF](https://huggingface.co/mradermacher/MN-12B-Mag-Mell-R1-Uncensored-i1-GGUF)

## Support the Developer

If you find aiMultiFool useful and want to support its development, you can buy me a coffee! Your support helps keep the project alive and growing.

https://ko-fi.com/aimultifool

## License
GPLv3
