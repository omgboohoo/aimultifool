# Product Requirements Document (PRD)
## aiMultiFool v0.1.4

### Document Information
- **Product Name**: aiMultiFool
- **Version**: 0.1.4
- **Document Version**: 1.6
- **Date**: 2025-12-26
- **Author**: Dan Bailey
- **Status**: Updated

---

## 1. Executive Summary

aiMultiFool is the Premium Linux Terminal-Based Sandbox for Private AI Roleplay. Built with the Textual framework, it enables users to interact with local Large Language Models (LLMs) through a sleek, high-performance terminal interface. It specializes in character-driven roleplay using SillyTavern character cards, prioritizing visual quality, privacy, and granular technical control.

---

## 2. Product Overview

### 2.1 Solution
aiMultiFool provides a sophisticated Textual-based TUI that:
- Runs high-speed LLM inference locally via `llama-cpp-python`.
- Supports SillyTavern character cards (PNG metadata extraction).
- Features a multi-pane responsive layout:
    - **Header**: Standard application header.
    - **Top Menu Bar**: High-level tools like the **Debug** context viewer.
    - **Left Sidebar**: Technical settings (Model, Context, GPU Layers, Narrative Style, Sampling parameters).
    - **Right Sidebar**: Dynamic Action Menu with categorized roleplay tools and system prompts.
    - **Main Area**: Scrollable message history with specialized widgets.
- Displays real-time performance metrics (TPS) and context saturation.
- Automatically handles context window pruning to prevent "out of context" errors.
- Fully persists user state (preferences, custom actions, technical settings).

---

## 3. Functional Requirements

### 3.1 Interface & Layout
- **Modular TUI**: A three-column interface (Left Sidebar, Chat, Right Sidebar) that is fully toggleable (**Ctrl+B**).
- **Top Menu Bar**: A compact menu providing global utilities, currently featuring the **Debug** tool.
- **Header & Status Bar**: Branding at the top and a real-time status bar at the bottom for system state (Thinking, Ready, TPS).

### 3.2 AI & Inference
- **GGUF Support**: Native support for GGUF models via `llama.cpp`.
- **GPU Optimization**: Automatic detection of optimal GPU layers with fallback to CPU. Remembers successful layer counts in a local cache for faster subsequent loads.
- **Streaming Inference**: Real-time text generation directly into chat widgets.
- **Smart Pruning**: Automatically analyzes token counts; if context exceeds 80%, it trims middle-history while strictly preserving the System Prompt and latest messages.

### 3.3 Chat & Character Management
- **PNG Metadata**: Extracts character name, personality, description, scenario, and prompts from SillyTavern cards.
- **In-App Card Editor**: Users can toggle "Character Edit Mode" to view and modify SillyTavern PNG metadata directly through a TUI modal.
- **PNG Metadata Injection**: Supports updating original PNG character cards by injecting updated JSON into `zTXt` chunks, maintaining cross-app compatibility.
- **Style Blending**: Users choose from 20 narrative styles. The app dynamically blends the selected style with character instructions into a unified system prompt.
- **Input Logic**: A smart input box that handles sub-second interruptions (typing while AI speaks stops the AI) and automatically manages focus.

### 3.4 Action Menu & Search
- **Categorized Actions**: A right-hand sidebar where actions are grouped into collapsibles (Scene, Character, etc.).
- **Real-time Filter**: A search bar at the top of the Action Menu. Typing updates the list instantly, searching both titles and prompts.
- **Auto-Expansion**: Categories containing search matches expand automatically to reveal results.
- **Edit Mode**: A full CRUD system for actions. Users can add or edit prompts in a modal. Saving an action refreshes the UI and highlights/expands the relevant category.
- **Dynamic Variable Injection**: Replaces `{{user}}` with the user's defined name in all prompts.

### 3.5 Debugging & Inspection
- **Debug Context Viewer**: A high-level tool that opens a JSON representation of the *actual* context window being sent to the LLM, including the compiled system prompt with style instructions.

### 3.6 Setup & Portability
- **run.sh Launcher**: A robust bash script that handles venv creation, dependency management, and automatic download of a **Universal Multi-Architecture CUDA Wheel** to ensure GPU support across various NVIDIA generations (Pascal to Ada).

---

## 4. Technical Architecture

- **Language**: Python 3.12+
- **Framework**: Textual (TUI Framework)
- **Engine**: llama-cpp-python (with custom wheel for CUDA support)
- **Mixins Design Pattern**: The core `AiMultiFoolApp` class inherits from multiple Mixins to keep logic separate:
    - `InferenceMixin`: Handles background threads for model loading and text generation.
    - `ActionsMixin`: Manages chat-related actions like Rewind, Reset, and Stop.
    - `UIMixin`: Dedicated to UI updates, widget mounting, and reactive observers.
- **Modules**:
    - `aimultifool.py`: Entry point and UI composition.
    - `logic_mixins.py`: Functional logic for Inference and Actions.
    - `ui_mixin.py`: UI synchronization and status management.
    - `ai_engine.py`: Core tokenization and model loading logic.
    - `character_manager.py`: PNG card parser and metadata injector (using manual binary chunk handling).
    - `widgets.py`: Custom TUI widgets and Modal screens (Sidebar, AddAction, DebugContext, EditCharacter).
    - `utils.py`: JSON persistent storage and narrative style definitions.
- **Data Schema**:
    - `settings.json`: Stores username, selected model, context size, and sampling parameters.
    - `action_menu.json`: JSON array of objects with `category`, `itemName`, `prompt`, and `isSystem` fields.
    - `model_cache.json`: Maps model paths to successful GPU layer counts.
- **Styling**: `styles.tcss` provides universal styling, using Textual CSS for responsive design and premium "dark mode" aesthetics.

---

## 5. Controls & Shortcuts

- **Ctrl+B**: Toggle Sidebars visibility.
- **Ctrl+S**: Stop AI generation.
- **Ctrl+Enter**: Continue AI or send prompt.
- **Ctrl+Z**: Rewind (Remove last user/assistant interaction).
- **Ctrl+R**: Restart (Full reset to start of conversation).
- **Ctrl+Shift+W**: Clear Chat (Wipe all history).
- **Ctrl+Q**: Quit Application.
