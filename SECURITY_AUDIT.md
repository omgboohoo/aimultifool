# Security & Privacy Audit
**Application**: aiMultiFool v0.1.0  
**Status**: ✅ Fully Private / Offline-Ready

## 1. Executive Summary
aiMultiFool is designed with a "Privacy First" architecture. All Large Language Model (LLM) inference, character processing, and conversation history management occurs strictly on the user's local hardware. No data leaves the machine during operation.

---

## 2. Network Activity Analysis

### ✅ Model Download (User-Initiated)
- **Scope**: Only triggered if the `models/` directory is empty.
- **Action**: Downloads the default GGUF model from Hugging Face via HTTPS.
- **Privacy**: No user-specific data, chat history, or identifiers are transmitted during this request.
- **Control**: User is notified via the TUI when a download starts.

### ✅ Zero Telemetry/Analytics
- No background pings, heartbeat checks, or usage tracking.
- No crash reporting to external servers.
- No update checks without user interaction.

---

## 3. Data Persistence & Storage

### 📁 `model_cache.json` (Local Only)
- **Content**: Technical configuration mappings between model filenames and the optimal number of GPU layers.
- **Privacy**: Contains no personal data or conversation fragments.
- **Risk**: Low. Stores local file paths of model files.

### 📁 `settings.json` (Local Only)
- **Content**: Persists user UI preferences including:
    - Username
    - Preferred Model
    - Context Size
    - GPU Layer settings
    - Narrative Style choice
- **Git Protection**: Both `settings.json` and `action_menu.json` are automatically added to `.gitignore` to prevent accidental sharing of local configuration or persona-specific actions.

### 🧠 In-Memory Conversation
- **Chat History**: Held strictly in system RAM during the session.
- **Persistence**: **Zero**. Chat history is not saved to disk or exported unless manually copied by the user. Closing the application wipes the current session permanently.

---

## 4. Dependencies Review

All core dependencies are industry-standard, open-source libraries:
- **`llama-cpp-python`**: Local C++ bindings for inference.
- **`textual` / `rich`**: TUI framework and console styling (Terminal-only).
- **`requests` / `tqdm`**: Only used for the optional model download phase.
- **`advanced modular architecture`**: Core logic is isolated into specialized Mixins (`logic_mixins.py`, `ui_mixin.py`) and modules, allowing for granular security audits of inference, character handling, and UI event logic.

---

## 5. Privacy Guarantee
aiMultiFool **cannot** see, read, or store your conversations. Your roleplay sessions are entirely your own and exist only as long as the application window is open.
