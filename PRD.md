# Product Requirements Document: aiMultiFool v0.1.9

## 1. Executive Summary
aiMultiFool is a premium Linux TUI sandbox for private AI roleplay. Built with **Textual** and **llama.cpp**, it provides a local, high-performance interface for interacting with GGUF models using SillyTavern character cards.

---

## 2. Core Vision
- **Privacy First**: 100% local inference with zero data leakage.
- **Roleplay Optimized**: Deep integration with character cards and sampling presets.
- **Desktop-Class TUI**: A responsive interface with a centralized Chat and a Right Sidebar for Settings and Actions.
- **Technical Transparency**: Real-time metrics and raw context inspection.

---

## 3. Functional Requirements

### 3.1 Interface & Layout
- **Two-Column Layout**: Central Area (Chat) and a Right Sidebar (Settings & Actions). Accessible via a minimalist TUI design.
- **Global Modals**: Dedicated screens for **Character Cards**, **AI Parameters**, and **Action Management**.
- **Real-time Status Bar**: Displays current state (Ready, Thinking, Recording) and live TPS/Context metrics.

### 3.2 AI & Inference
- **GGUF Support**: Native support for GGUF models via `llama.cpp`.
- **GPU Optimization**: Automatic detection of optimal GPU layers with fallback to CPU. Caches successful layer counts for faster loading.
- **Smart Pruning**: Automatically trims middle-history if context exceeds 80%, strictly preserving the System Prompt and latest turns.

### 3.3 Character & Content
- **SillyTavern Integration**: Manual binary chunk handling for PNG metadata extraction and in-app metadata injection.
- **Style Blending**: Users select from 20 narrative styles that are dynamically blended into the character's system instructions.
- **Action Manager**: Searchable sidebar for tools; changes are saved instantly as the user types.
- **Secure File Persistence**: High-grade **AES-256-GCM** encryption with **Argon2id** key derivation for chat history.

---

## 4. Technical Architecture

- **Language**: Python 3.12+
- **Frameworks**: Textual (TUI), llama-cpp-python (Inference).
- **Architecture**: Modular Mixin pattern for logic separation:
    - `InferenceMixin`: Handles background threads for tokenization and generation.
    - `ActionsMixin`: Manages conversation state (Rewind, Reset, Stop).
    - `UIMixin`: Dedicated to widget mounting and reactive UI synchronization.
- **Core Modules**:
    - `aimultifool.py`: Entry point and UI composition.
    - `ai_engine.py`: Core logic for model loading and token streaming.
    - `character_manager.py`: PNG card parser and metadata editor.
    - `widgets.py`: Custom TUI widgets and modal screens.
- **Data Persistence**:
    - `settings.json`: sampling parameters and app preferences.
    - `action_menu.json`: array of categorized roleplay prompts.
    - `model_cache.json`: map of models to validated GPU layer counts.

---

## 5. Keyboard Navigation
| Command | Result |
| :--- | :--- |
| **Ctrl+S** | Stop Generation |
| **Ctrl+R** | Restart Conversation from first message |
| **Ctrl+Z** | Rewind Last Turn |
| **Ctrl+Enter** | Continue AI response |
| **Ctrl+Shift+W** | Wipe Chat History |
| **Ctrl+Q** | Quit Application |


