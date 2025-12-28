# Security & Privacy Audit
**Application**: aiMultiFool v0.1.9  
**Status**: ✅ Fully Private / Offline-Ready

## 1. Executive Summary
aiMultiFool is designed with a "Privacy First" architecture. All Large Language Model (LLM) inference, character processing, and conversation history management occurs strictly on the user's local hardware. No data leaves the machine during operation.

---

## 2. Network Activity Analysis

### ✅ Model Download (User-Initiated)
- **Scope**: Only triggered if the `models/` directory is empty.
- **Action**: Downloads the default GGUF model (`L3-8B-Stheno`) from Hugging Face via HTTPS.
- **Privacy**: No user-specific data, chat history, or identifiers are transmitted.

### ✅ Binary Delivery (First Launch)
- **Action**: The `run.sh` script downloads a Universal Multi-Arch CUDA Wheel (~339MB) from `aimultifool.com`.
- **Purpose**: Strictly for delivering the pre-compiled `llama-cpp-python` backend to ensure GPU acceleration.
- **Privacy**: This is a direct file download with no telemetry attached.

### ✅ External Integration (Links)
- **Action**: Clicking community links (Discord, Ko-fi, Website) opens the target URL in your **system's default web browser**.
- **Control**: The app itself does not possess an internal web engine and does not track click-through rates.

### ✅ Zero Telemetry/Analytics
- No background pings, heartbeat checks, or usage tracking.
- No crash reporting to external servers.
- No update checks without user interaction.

---

## 3. Data Persistence & Storage

### 📁 Technical Config (Local Only)
- **`model_cache.json`**: Maps model paths to successful GPU layer counts to speed up loading.
- **`settings.json`**: Persists UI preferences (Username, Context Size, Sampling Params).
- **`action_menu.json`**: Stores your custom roleplay prompts.
- **Git Protection**: These files are automatically ignored by Git to prevent accidental sharing of local settings.

### 🎭 Character Metadata (Local Only)
- **Metadata Editing**: The built-in character editor operates strictly on local PNG files.
- **In-App Processing**: Metadata extraction and injection handle binary `zTXt/tEXt` chunks locally using standard Python libraries.

### 📁 Conversation Persistence (Encrypted)
- Chats can be optionally saved to the `chats/` directory.
- **Encryption**: Optional high-grade **AES-256-GCM** authenticated encryption.
- **KDF**: Uses **Argon2id** (64MB memory cost, 3 iterations) to derive keys from user passphrases.
- **Privacy**: Without the passphrase, sessions are cryptographically inaccessible. Decryption occurs strictly in system RAM.

---

## 4. Dependencies Review
- **`llama-cpp-python`**: Local C++ bindings for inference.
- **`textual` / `rich`**: TUI framework (Terminal-only).
- **`requests`**: Only used for initiated model downloads.
- **`advanced modular architecture`**: Logic is isolated into Mixins, allowing for transparent auditing of how data flows between the UI and the AI engine.

---

## 5. Privacy Guarantee
aiMultiFool **cannot** see, read, or store your conversations. Your roleplay sessions are entirely your own and exist only as long as the application window is open.

