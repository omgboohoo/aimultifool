# Release Notes

## v0.2.4: Character Stats Analysis
### 📊 New Feature: Character Stats Analysis
- **Stats Button**: Added a new "Stats" button next to the "Emotions" button for analyzing character attributes from recent conversations.
- **Core Stats Tracking**: Analyzes six key character stats (0-100 scale) for each character mentioned:
  - **Trust**: How much the character trusts others
  - **Affection**: Emotional closeness/attachment
  - **Confidence**: Self-assurance/assertiveness
  - **Stress**: Pressure/anxiety level
  - **Interest**: Engagement in the conversation
  - **Arousal**: Sexual/romantic excitement level
- **Streaming Responses**: Stats analysis streams results in real-time, just like emotion analysis, providing instant feedback as stats are generated.
- **Last 3 Conversations**: Analyzes the last 3 user/assistant exchanges (6 messages total) to determine current character stat values.
- **Vector Chat Compatibility**: Works seamlessly with Vector Chat (RAG), filtering out vector context messages to focus on actual conversation content.
- **UI Improvements**: Renamed "Emotion Analysis" button to "Emotions" for a cleaner, more concise interface.

## v0.2.3: Streaming Emotion Analysis & Vector Chat Fixes
### ⚡ Emotion Analysis Improvements
- **Streaming Responses**: Emotion analysis now streams responses in real-time, just like regular AI replies. Users no longer need to wait for the complete analysis - results appear incrementally as they're generated.
- **Simplified Prompt**: Removed unnecessary notes and extra information from emotion analysis output. The prompt now focuses solely on providing concise emotional summaries for each character.
- **Vector Chat Compatibility**: Fixed emotion analysis to properly detect all characters when using Vector Chat (RAG). Vector context messages are now correctly filtered out, ensuring emotion analysis only examines the actual recent conversation, not historical context.

## v0.2.2: Emotion Analysis Optimization & Performance
### ⚡ Performance Improvement: Manual Emotion Analysis
- **On-Demand Emotion Analysis**: Moved emotion analysis from automatic sidebar updates to an on-demand "Emotion Analysis" button in the main action bar. This eliminates the automatic analysis overhead after every AI reply, significantly speeding up normal chat interactions.
- **Faster Chat Experience**: By removing automatic emotion analysis, chat responses now complete faster without waiting for emotion processing. Users can trigger emotion analysis manually when needed via the dedicated button.
- **Improved Chat Window Integration**: Emotion analysis results now appear directly in the main chat window as informational messages, providing better visibility and context without requiring sidebar navigation.
- **Enhanced Control**: Users have full control over when to analyze emotions, allowing them to focus on fast-paced conversations without interruption.

## v0.2.1: Emotion Dynamics & UI Improvements
### 🎭 New Feature: Emotion Dynamics Panel
- **Character Emotion Analysis**: Added a new "Emotion Dynamics" panel at the bottom of the sidebar that automatically analyzes and displays how each character feels after each AI reply.
- **Real-time Updates**: The panel updates automatically after each AI response, providing one-sentence emotional summaries for each character.

## v0.2.0: Unified Direct Integration & Robust Threading
### 🪟 Windows Stability & Threading Improvements
- **Robust Model Loading**: Fixed the intermittent "failed to start load thread" error on Windows by transitioning from subprocess-based loading to a manual thread-and-queue system.
- **Unified Direct Integration**: Windows now uses the same direct `llama_cpp.Llama` integration as Linux, eliminating the overhead of the JSONL protocol and improving token streaming efficiency.
- **Manual Threading Sync**: Implemented reliable manual threading with proper GIL management to ensure the Windows UI remains perfectly responsive during heavy GPU model loading.
- **Improved Performance**: Direct object access reduces latency and improves overall stability for Windows users, especially with larger models.

### 🐧 Linux & Cross-Platform Unification
- **Architectural Parity**: Main chat inference is now unified across all platforms using direct `llama_cpp` bindings with Textual's `@work` (inference) and manual `threading` (loading) decorators.
- **Consistency**: All platforms now benefit from the same high-performance API, ensuring predictable behavior for features like token counting and context pruning.
- **Streamlined Codebase**: Removed complex subprocess lifecycle management for main chat, leading to a more maintainable and less error-prone application.

### 🧠 Vector Chat (RAG)
- **Subprocess Embeddings (Windows)**: Continued use of subprocess isolation for embeddings on Windows to ensure maximum UI stability during long-term memory retrieval.
- **Direct Embeddings (Linux)**: Maintained high-performance direct integration for embeddings on Linux systems.

## v0.1.26: Linux Direct llama_cpp Integration & Performance Improvements
### 🐧 Linux Optimization
- **Direct llama_cpp Integration**: Linux now uses direct `llama_cpp.Llama` objects instead of subprocess/JSONL protocol, eliminating unnecessary complexity and improving performance.
- **Simplified Architecture**: Removed subprocess overhead on Linux - models load and run directly in-process, providing faster response times and simpler code paths.
- **No More JSONL Protocol**: Linux no longer needs JSONL protocol synchronization, eliminating stream draining issues that caused problems with larger models (12B+).
- **Better Stop/Reprompt Performance**: Direct llama_cpp integration means stopping AI speech and reprompting is instant on Linux, especially with larger models.

### 🔧 Technical Improvements
- **Platform-Specific Model Loading**: Automatic detection of platform - Windows uses subprocess (for GIL avoidance), Linux uses direct llama_cpp.
- **Platform-Specific Embeddings**: Linux embeddings now use direct llama_cpp instead of subprocess, matching the main model architecture.
- **Token Counting Fix**: Updated `count_tokens_in_messages()` to handle both SubprocessLlama wrapper (Windows) and direct llama_cpp.Llama (Linux) objects.
- **Stream Handling**: Direct llama_cpp generators work seamlessly without needing complex stream draining logic.

### 🎯 Benefits
- **Faster Performance**: No subprocess communication overhead on Linux
- **Better Reliability**: Eliminates JSONL protocol sync issues that caused problems with 12B models
- **Simpler Code**: Direct Python objects instead of JSON serialization/deserialization
- **Improved UX**: Instant stop/reprompt response, especially noticeable with larger models

## v0.1.25: Platform-Specific Threading Architecture
- **Linux Threading Reinstatement**: Reinstated Textual's `@work` decorator for Linux operations. While this approach can be unreliable under certain conditions, it provides better integration with the Textual framework on Linux systems.
- **Windows Threading Stability**: Windows continues to use the proven subprocess-based threading method, which has demonstrated superior reliability and stability for Windows environments.

## v0.1.24: Subprocess Architecture & Smooth Streaming
- **Subprocess Threading Model**: Linux uses the same robust subprocess-based architecture as Windows, preventing UI freezes and improving overall stability.
- **Buttery Smooth Streaming**: Implemented time-based batching for UI updates. The chat now refreshes every 50ms, eliminating the "jerky" stutter caused by high-frequency layout calculations and regex-based styling.
- **Optimized Status Bar**: Throttled status bar updates to 500ms intervals, reducing overhead while maintaining readability of TPS and context metrics.
- **Streamlined Codebase**: Removed platform-specific branching for core AI operations, moving to a single maintainable cross-platform standard.

## v0.1.23: Parity & Stability
- **Mirror Operation**: Changes to make Windows use mirror Linux operation for consistent cross-platform experience.

## v0.1.22: Initial Windows Release (Strictly Alpha)
### 🪟 Windows Support
- **Cross-Platform Compatibility**: Full Windows 10/11 support with native subprocess-based architecture to prevent UI freezes.
- **Subprocess LLM**: Model loading and inference run in separate processes on Windows, ensuring the UI remains responsive even during heavy GPU operations.
- **Subprocess Embeddings**: Vector Chat embeddings also run in a separate process on Windows, maintaining full RAG functionality without blocking the UI.
- **Windows-Specific UX**: Regenerate button automatically disabled during AI generation on Windows to prevent protocol conflicts.
- **Stream Cleanup**: Improved Stop/Continue handling with proper stream draining to prevent crashes when interrupting generation.

### 🔧 Technical
- Added `llm_subprocess_worker.py`: Separate process worker for model loading and inference on Windows.
- Added `llm_subprocess_client.py`: Client wrapper providing llama_cpp.Llama-compatible API over subprocess protocol.
- Windows event loop policy set to `WindowsSelectorEventLoopPolicy` for better threading compatibility with Textual.
- Manual threading implementation for model loading on Windows, bypassing Textual's `@work` decorator to prevent deadlocks.
- Queue-based communication between worker threads and main thread for reliable state updates.

## v0.1.21: Vector Chat with Optional Encryption
### 🧠 New Feature: Vector Chat (RAG)
- **Long-Term Memory**: Seamlessly integrate local vector databases into your roleplay for persistent long-term memory and knowledge retrieval.
- **Optional Encryption**: Secure your vector database payloads with **AES-256-GCM** encryption, keeping your private data mathematically scrambled on disk.
- **Database Management**: Full suite of tools to create, duplicate, rename, and delete vector databases directly from the new **Vector Chat** modal.
- **Seamless Integration**: Toggle vector chat on/off mid-conversation to enhance characters with external knowledge or historical context.

## v0.1.20: Critical Threading Crash Fix
### 🐛 Critical Bug Fixes
- **Threading Race Condition Fix**: Fixed a critical crash that occurred when trying to talk with AI, manifesting as `[Errno 2] No such file or directory: '/sysdeps/unix/sysv/linux/appll_wait.c'`. This was caused by race conditions in multi-threaded inference operations.
- **Inference Lock Mechanism**: Added a global threading lock to ensure only one inference operation runs at a time, preventing concurrent CUDA/GPU operations that cause system-level threading errors.
- **Improved Stop/Start Handling**: Enhanced the stop generation logic with increased wait times and extra delays to ensure proper lock release before starting new inference operations.
- **Deadlock Prevention**: Lock acquisition now uses a 5-second timeout to prevent deadlocks, with user-friendly warnings if another inference is still running.

### 🔧 Technical
- Added `threading.Lock()` to `InferenceMixin.run_inference()` with timeout-based acquisition.
- Lock is always released in the `finally` block, even if errors occur during inference.
- Increased `action_stop_generation` max waits from 20 to 40 iterations.
- Added 0.15s delay after stopping generation to ensure clean state transitions.

## v0.1.19: Model Settings Persistence in Saved Chats
### 💾 Chat Management Enhancements
- **Model Settings Preservation**: Saved chats now include complete model configuration (model path, context size, GPU layers, and all sampling parameters) alongside conversation history.
- **Automatic Model Restoration**: When loading a saved chat, the app automatically restores the model settings used during that conversation and reloads the model if needed.
- **Backward Compatibility**: Old chat files (messages only) continue to work seamlessly, ensuring no disruption for existing saved conversations.
- **Settings Included**: All model parameters are preserved: selected model, context size, GPU layers, temperature, top P, top K, repeat penalty, and min P.

### 🔧 Technical
- Enhanced chat save format to include `model_settings` dictionary alongside `messages`.
- Updated load logic to handle both legacy format (messages list) and new format (dictionary with messages and settings).
- Automatic model reloading when loaded chat settings differ from current configuration.
- Settings are automatically saved to `settings.json` when loading a chat with different model settings.

## v0.1.18: Enhanced Action Menu & Improved UX
### 🎯 Action Menu Improvements
- **New JSON Format**: Action menu now uses an improved JSON structure for better organization and extensibility.
- **Hover Tooltips**: Added helpful hover tooltips throughout the action menu interface, providing context and guidance for better usability.
- **Expanded Default Actions**: Significantly increased the number of default actions available out of the box, providing users with a richer set of roleplay tools and system prompts.

## v0.1.17: Regenerate Button & Enhanced AI Control
### 🎮 User Experience
- **Regenerate Button**: Added a new "Regenerate" button next to the "Continue" button that allows users to have the AI try the last reply again. The button remains visible even during AI generation, allowing users to stop and regenerate mid-generation.
- **Smart Regeneration**: The regenerate button intelligently handles both completed and in-progress generations, removing partial or complete assistant messages and re-running inference with the same user prompt.

### 🔧 Technical
- Enhanced `action_regenerate` method in `ActionsMixin` to support stopping ongoing generation and cleaning up partial assistant messages from the UI.
- Improved button state management to keep regenerate button visible during generation for better user control.

## v0.1.16: Improved Context Window Pruning & Default Settings
### 🧠 Context Management
- **Smart Pruning Strategy**: Completely redesigned pruning algorithm for better roleplay context preservation. Now preserves system prompt, first 3 exchanges (for early scene setup), and the last message, then deletes messages one by one from the middle until reaching 60% context usage.
- **Pruning Trigger**: Changed from 80% to 85% context usage threshold for more efficient context management.
- **UI Synchronization**: Chat window now automatically rebuilds to match the pruned context window exactly, ensuring perfect synchronization between displayed messages and actual AI context.

### ⚙️ Default Settings
- **Default Context Size**: Changed default context size from 4096 to 8192 tokens for better roleplay experiences.
- **Context Size Options**: Updated model settings modal with improved context size options:
  - Removed 2048 (too small for practical use)
  - Added 65536 option (double 32768) for high-end systems
  - Marked 8192 as "(recommended)" in the dropdown

### 🐛 Bug Fixes
- Fixed context window display mismatch where chat UI didn't reflect pruned messages correctly.
- Fixed aggressive pruning that was removing too many messages (dropping to 19-31% instead of target 60%).

## v0.1.15: Enhanced Parameters UI with Sliders
### 🎛️ UI Improvements
- **Slider Controls**: Replaced text input fields with interactive sliders in the Parameters modal for a more intuitive parameter adjustment experience.
- **Real-time Value Display**: Parameter values update in real-time as sliders are moved, providing immediate visual feedback.
- **Recommended Ranges**: Sliders are pre-configured with recommended min/max values and step increments for optimal LLM parameter tuning:
  - Temperature: 0.0-2.5 (step 0.1)
  - Top P: 0.1-1.0 (step 0.01)
  - Top K: 0-100 (step 1)
  - Repeat Penalty: 0.8-2.0 (step 0.01)
  - Min P: 0.0-1.0 (step 0.01)

### 🔧 Technical
- Integrated `textual-slider` package for native slider widget support.
- Created `ScaledSlider` wrapper to support float values with proper scaling for integer-based sliders.

## v0.1.14: Updated Default Model
### 🤖 Model Changes
- **New Default Model**: Changed default auto-download model from `L3-8B-Stheno-v3.2-Q4_K_M` to `MN-12B-Mag-Mell-R1-Uncensored.i1-Q4_K_S` for improved quality out of the box.
- **Model Documentation**: Updated README to reflect new default model and note that Stheno is available as a smaller, faster option for users with limited resources.

## v0.1.13: Enhanced Theming & UI Refinements
### 🎨 Theming Enhancements
- **Speech Styling Options**: Added configurable speech styling in the Theme menu with three modes: None, Inversed, and Highlight. Speech styling applies to quoted text and dialogue in AI responses, allowing users to customize how character speech is visually distinguished.
- **Real-time Speech Styling**: Speech styling changes apply immediately to existing messages without requiring a restart, providing instant visual feedback.

### 🎯 UI Improvements
- **Model Name in Status Bar**: Status bar now displays the loaded model name (e.g., "L3-8B-Stheno-v3.2-Q4_K_M Ready") instead of generic "Model Ready", making it easier to identify which model is currently active.

## v0.1.12: Enhanced AI Card Editing & JSON Parsing
### 🔧 Character Card Editing Improvements
- **Programmatic Data Section Normalization**: When editing character cards with AI assistance, the metadata structure is now automatically normalized to ensure both top-level fields and a `data` section exist, matching the behavior when creating new cards.
- **Smart Data Section Detection**: If a card only contains a `data` section (no top-level character fields), the AI now acts directly on that section, reducing unnecessary work.
- **Robust JSON Parsing**: Enhanced JSON parsing with automatic cleanup of common formatting issues (trailing commas, etc.) and intelligent fallback extraction of fields even from malformed JSON responses.
- **Better Error Reporting**: When JSON parsing fails, users now see detailed error messages explaining what went wrong and what was attempted, making debugging easier.

### 🐛 Bug Fixes
- Fixed issue where larger AI models would appear to make changes but fail to apply them due to JSON parsing errors.
- Improved handling of multi-line strings and escaped characters in AI-generated JSON responses.
- Added fallback mechanisms to extract character data even when AI returns invalid JSON format.

## v0.1.11: Theme Support & UI Polish
### 🎨 Visual Customization
- **Built-in Theme System**: Added comprehensive theme support with 11 built-in themes including Textual Dark/Light, Catppuccin Latte/Mocha, Dracula, Gruvbox, Monokai, Nord, Solarized Light, Tokyo Night, and Flexoki.
- **Theme Persistence**: Selected theme is saved to settings and persists across app restarts.
- **Consistent Theming**: All UI elements now respect theme colors, including buttons, inputs, modals, and message styling.
- **Enhanced Message Styling**: User messages are now bold, and quoted text in AI responses uses terminal selection highlighting for better readability.

### 🎯 UI Improvements
- **Unified Button Styling**: All buttons now use consistent default styling, matching the selected theme.
- **Status Bar Enhancement**: App name and version now displayed in the status bar for better visibility.
- **Theme-Aware Components**: Removed hardcoded colors throughout the interface to ensure full theme compatibility.

## v0.1.10: Real-Time AI & Enhanced Management
### 🪄 Intelligent Creation
- **AI Assisted Character Card Editing**: The Character Card AI Editor now **streams its thoughts in real-time**, providing instant feedback as it crafts your character's personality and metadata on the fly.
- **Smart Card Templates**: Creating a "New Card" now automatically clones the `aimultifool.png` base and injects a complete V2 template, allowing for immediate AI-assisted editing without starting from scratch.

### 🔒 Security & Management
- **On-Demand Card Encryption**: Secure your character cards with AES-256-GCM encryption via a new "Save as Encrypted" modal prompt. Encrypted cards are locked by default and must be explicitly unlocked to view or play.

## v0.1.9: Speed, Safety & Stats

- **Smart Rewind**: Rewinding now automatically restores the last user message to the input box for rapid correction and resending.
- **Interactive Setup**: `run.sh` now prompts for environment reinstallation on launch with a recommendation to do so after updates, ensuring dependency alignment while maintaining fast startup by default.
- **Lapse-Free Loading**: Optimized the model selection workflow—the modal now closes and locks UI controls before initializing resource-heavy model loading, eliminating visual lag.
- **Performance Metrics**: Integrated **"Peak TPS"** tracking into the status bar, providing real-time visibility into your hardware's maximum generation speed during every interaction.
- **Robust Clipboard**: Added a "Copy" button to the Context Window modal powered by `pyperclip`, providing reliable cross-platform clipboard sync and resolving TUI-specific copy limitations.
- **Roleplay Immersion**: Selection of the "Default" style now intelligently suppresses the generic assistant persona when a character card is active, preventing immersion-breaking character shifts.
- **Transparent Passphrases**: Password and passphrase fields in the "Save Chat" and "Unlock Chat" modals are now visible as you type, allowing for immediate verification and fewer entry errors.

## v0.1.8: Secure Persistence & File Management
- **Secure Chat Management**: Introduced a new **File** menu allowing users to save and load conversation histories.
- **Privacy Armor**: Optional state-of-the-art **AES-256-GCM** encryption for saved chats.
- **Hardened Key Derivation**: Uses **Argon2id** (memory-hard KDF) for deriving encryption keys from passphrases.
- **Model Lifecycle Fixes**: Resolved a bug where successful model downloads were incorrectly reported as failed.
- **Dynamic Model Discovery**: The model selection list now automatically refreshes and populates as soon as a download completes, without requiring a restart.
- **Robust UI Ghosting**: Enhanced "busy state" detection ensures that model-related controls are correctly disabled and provide visual feedback across all modal screens during background processes.

## v0.1.7: Styling & Transparency
- **Expanded Style Library**: More than doubled the available narrative styles to 44 distinct presets, including new "Super Dark", "Degenerate", and "Roleplay" themes.
- **Improved Default Persona**: Replaced the default system prompt with a highly optimized, friendly, and adaptive instruction set.
- **Transparent System Prompts**: Active system prompts and style instructions are now visible directly in the chat window as informational messages (without polluting the AI context).
- **Default Style Priority**: The "Default" style is now pinned to the top of the selection list for easy access.
- **Action Menu Polish**: Improved capitalization and formatting for all default action menu items and prompts.

## v0.1.6
- **UX**: Moved the sidebar into a "Model" modal that launches on startup for a cleaner interface.
- **UX**: Reordered top menu items for better flow (Model, Parameters, Cards, Actions, About).
- **Fix**: Resolved crash when loading settings with invalid/outdated options.
- **Internal**: Refactored logic to support modal-based parameter loading.

## v0.1.5: Workflow & Bug Fixes
- **Action Management Refinement**: 
    - Fixed crash when filtering categories in the Manage Actions modal. 
    - Removed redundant "All Categories" view for cleaner navigation.
    - Added explicit **"Action Type"** selector to toggle between User Actions and System Prompts.
    - Intelligent auto-detection of System Prompts based on category name.
- **Improved Action Sorting**: Action lists now strictly adhere to Category > Name sorting across the entire application.

## v0.1.4: Character & Management Update
- **Character Card Management**: A comprehensive modal for SillyTavern PNG metadata management.
- **Dedicated Parameters Modal**: Centralized AI sampling controls
- **Improved Action Management**: Added modal for action management with global category filter and "Duplicate Action" functionality for faster workflow.
- **UX Refinements**: Optimized UI layouts for smaller terminal windows.

## v0.1.3: Search & Inspection
- **Action Menu Search & Filtering**: Real-time search across action names and prompts with auto-expanding categories.
- **Context Window**: New "Context Window" top menu item to inspect the full JSON context being sent to the AI.
- **Dynamic Character Styling**: Narrative styles (Concise, Dramatic, etc.) now correctly apply to character cards and update instantly during active chat.
- **Improved Focus Logic**: Automatically focuses the user input box after model loading and newly added/edited actions.

## v0.1.2: Portability & CUDA
- **Multi-Arch CUDA Support**: Built-in scripts now generate "Fat Binaries" supporting GTX 10-series through RTX 40-series.
- **Portability Fixes**: Improved `run.sh` and build scripts for better cross-distro compatibility.

## v0.1.1: Quality of Life
- Stability improvements for AI Stop/Restart logic.
- Prevented CUDA errors during rapid interruptions.

## v0.1.0: Initial Release
- Initial release of aiMultiFool.
- Character card support, real-time metrics, and modular architecture.


