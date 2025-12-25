# Product Requirements Document (PRD)
## aiMultiFool v0.1.0

### Document Information
- **Product Name**: aiMultiFool
- **Version**: 0.1.0
- **Document Version**: 1.3
- **Date**: 2025-12-24
- **Author**: Dan Bailey
- **Status**: Updated

---

## 1. Executive Summary

aiMultiFool is the Premium Linux Terminal-Based Sandbox for Private AI Roleplay. Built with Textual, it enables users to interact with local Large Language Models (LLMs) through a premium terminal interface. It specializes in character-driven roleplay using SillyTavern character cards, prioritizing visual quality, performance metrics, and privacy.

---

## 2. Product Overview

### 2.1 Solution
aiMultiFool provides a Textual-based TUI that:
- Runs LLM inference locally via `llama-cpp-python`.
- Supports SillyTavern character cards (PNG metadata).
- Features a dual-sidebar layout:
    - **Left Sidebar**: Settings (Model, Context, GPU, Style, Sampling).
    - **Right Sidebar**: Action Menu (System Prompts, Card Tools, Scene Tools).
- Displays real-time TPS (Tokens Per Second) and Context % usage.
- Automatically manages context by pruning history when limits are reached.
- Persists user preferences (Username, Model, etc.) across sessions.

---

## 3. Functional Requirements

### 3.1 Core Features
- **TUI Interface**: Multi-pane layout with a scrollable chat area and a toggleable, scrollable sidebar for settings.
- **Model Management**: Selection of GGUF models from a dedicated folder with automatic GPU/CPU layer optimization and caching.
- **Active Controls**: Dedicated buttons and shortcuts for **Stop**, **Continue**, **Rewind**, and **Reset**.
- **Real-time Stats**: Live display of TPS, total tokens, and context saturation percentage in a docked status bar.
- **Character Support**: Extraction of personality and scenario data from SillyTavern PNG cards.
- **Automated Prose Styling**: Choose from **20** distinct narrative styles (e.g., Concise, Dramatic, Erotic, Horror, Whimsical) that automatically inject system instructions to guide the AI's tone.
- **Smart Pruning**: Automatic trimming of conversation history (preserving system prompt) when context exceeds 80% to maintain a steady 60% usage.
- **Generation Parameters**: User-adjustable Temperature, Top-P, Top-K, and Repeat Penalty controls in the sidebar.
- **Persistence**: Automatic saving and loading of user configuration (Username, Model, Context Size, GPU Layers, Style) to `settings.json`.
- **UX Excellence**: Automatic focus return to the chat input after any UI interaction.
- **Action Menu**: Persistent right-hand sidebar for quick execution of roleplay actions. Includes an **Edit Mode** for creating, editing, and deleting custom actions and system prompts in real-time. Actions are automatically sorted alphabetically.
- **Dynamic Variable Injection**: Automatic replacement of template variables (e.g., `{{user}}`) within action prompts to maintain immersion.
- **Dynamic Message Mounting**: Optimized real-time addition of chat messages using specialized widgets and immediate auto-scrolling logic.
- **Codebase Modularization**: Separation of concerns into AI Engine, Character Management, UI Widgets, and Utilities using an advanced Mixin-based architecture.

---

## 4. Technical Architecture

- **Language**: Python 3.12+
- **Framework**: Textual (TUI)
- **Engine**: llama-cpp-python
- **Modules**:
    - `aimultifool.py`: High-level TUI Application orchestration.
    - `logic_mixins.py`: Inference and Action Mixins for modular logic handling.
    - `ui_mixin.py`: Helper Mixin for UI updates and watch methods.
    - `ai_engine.py`: Low-level Model management and tokenization.
    - `character_manager.py`: PNG Metadata extraction.
    - `widgets.py`: Custom UI components (Sidebar, MessageWidget).
    - `utils.py`: Shared utilities, settings, and style prompts.
- **Persistence & Styling**: 
    - `styles.tcss`: External Textual CSS for application styling.
    - `model_cache.json`: Optimized GPU layer counts.
    - `settings.json`: User interface preferences and model selection.
    - `action_menu.json`: Customizable roleplay action data.
