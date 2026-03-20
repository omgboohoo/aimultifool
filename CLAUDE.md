# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

aiMultiFool is a cross-platform terminal-based AI roleplay sandbox powered by `llama-cpp-python` and `Textual`. It runs local GGUF models with SillyTavern-compatible character cards, optional Ollama backend, vector memory (Qdrant), and AES-256-GCM encryption.

## Running the Application

```bash
# Linux GPU (CUDA)
./run_linux_gpu.sh

# Linux CPU-only
./run_linux_cpu.sh

# CPU mode flag (passed to aimultifool.py)
python aimultifool.py --cpu
```

Launch scripts auto-bootstrap: download portable Python 3.12, create venv, install deps from `requirements.txt`, then start the app. There is no separate build step.

## Architecture

**Mixin-based monolith** — the main app class composes all behavior via inheritance:

```
AiMultiFoolApp(App, InferenceMixin, ActionsMixin, UIMixin, VectorMixin)
```

### Core Files

| File | Role |
|---|---|
| `aimultifool.py` | Entry point, Textual App class, UI composition, event handlers, reactive state |
| `logic_mixins.py` | `InferenceMixin` (model loading, streaming inference, context pruning), `ActionsMixin` (stop/continue/rewind/regenerate/suggest/auto), `VectorMixin` (Qdrant RAG operations, subprocess embeddings on Windows) |
| `ui_mixin.py` | `UIMixin` — DOM helpers: `add_message()`, `full_sync_chat_ui()`, safe UI/backend sync |
| `widgets.py` | All modal screens (Model, Parameters, Characters, Actions, Chat, Vector, Theme, Context) and custom widgets (MessageWidget, ScaledSlider, etc.) |
| `ai_engine.py` | `count_tokens_in_messages()`, `prune_messages_if_needed()`, model discovery (`get_models`, `get_ollama_models`) |
| `ollama_client.py` | HTTP wrapper mimicking the `llama_cpp.Llama` interface for seamless backend switching |
| `character_manager.py` | PNG tEXt/zTXt chunk I/O for SillyTavern v2 character cards (pure stdlib) |
| `utils.py` | AES-256-GCM encryption (Argon2id KDF), clipboard, settings/action-menu JSON I/O |
| `styles.tcss` | Textual CSS for the entire UI |

### Key Patterns

- **Dual inference backends**: Local `llama_cpp.Llama` and `OllamaClient` expose the same interface (`create_chat_completion` with streaming). Switching doesn't require restart.
- **Threading for model loading**: Heavy `Llama()` init runs in a `threading.Thread` with `Queue` to avoid blocking the Textual event loop. Inference uses Textual's `@work(exclusive=True, thread=True)`.
- **Global `_inference_lock`**: Prevents concurrent inference calls.
- **Reactive state**: Textual reactive properties (`messages`, `selected_model`, `is_loading`, etc.) drive UI updates via `watch_*` methods.
- **Smart context pruning**: Preserves system prompt (index 0), first 3 exchanges (1-6), and last message; prunes middle messages at 85% capacity targeting 60%.
- **Streaming tokens**: Both backends stream; `MessageWidget` updates in real-time with live TPS calculation.

### Data Files

- `settings.json` — persisted app settings (model path, inference params, theme, etc.)
- `action_menu.json` — roleplay action presets with categories; defaults in `action_menu_defaults.py`
- `models/` — GGUF model files; `cards/` — character PNGs; `chats/` — saved conversations; `vectors/` — Qdrant storage

### Dependency Graph

```
aimultifool.py → logic_mixins, ui_mixin, widgets, utils, character_manager, ai_engine
logic_mixins.py → ai_engine, character_manager, utils, widgets, ollama_client, qdrant_client
widgets.py → utils, character_manager, textual, textual_slider
```

## Development Notes

- Python 3.12+ required. Portable Python is bundled in `python_portable/`.
- No test suite exists — changes should be manually verified by running the app.
- `devtools/control_ollama.py` manages the Ollama service; `devtools/inspect_vectors.py` inspects Qdrant collections.
- Qdrant telemetry is disabled via env var `QDRANT__TELEMETRY_DISABLED=true` (set in `widgets.py`).
- Encryption uses AES-256-GCM with Argon2id (64MB memory, 3 iterations, 4 lanes). Applied optionally to character cards, chats, and vector payloads.
- Windows-specific: subprocess-based embeddings (`llm_subprocess_client.py` / `llm_subprocess_worker.py`) to keep UI responsive.
