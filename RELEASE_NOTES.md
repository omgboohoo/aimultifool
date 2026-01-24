# Release Notes

## v0.4.9: User Text Color Customization & Model Cache Removal
### 🎨 New Feature: User Text Color Selection
- **Customizable User Text Color**: Added a "User Text Color" dropdown in the Theme Settings modal, allowing users to customize the color of their messages in the chat window.
- **Color Options**: Choose from White, Green, Yellow, Blue, Cyan, Magenta, Red, Orange, Purple, or Pink.
- **Persistent Settings**: User text color preference is saved to `settings.json` and persists across app restarts.
- **Default Color**: Defaults to green if no setting is saved.
- **Always Bold**: User messages remain bold regardless of color selection.

### 🔧 Technical Improvements
- **Removed Model Cache**: Completely removed the `model_cache.json` system to eliminate race condition risks when running multiple instances.
- **Simplified GPU Layer Fallback**: GPU layer selection now always starts from the user's manually chosen layer count and works down automatically if needed.
- **Improved Fallback Steps**: GPU layer fallback now steps down by 4 layers at a time (e.g., 40 → 36 → 32 → 28...)

## v0.4.8: AI-Powered Message Suggestions & Auto Mode
### 💡 New Feature: Suggest Button
- **AI Message Suggestions**: Added a "Suggest" button next to the Rewind button that generates AI-powered message suggestions for the user in the current roleplay context.
- **Smart Context Awareness**: Suggestions are generated based on the full conversation history, ensuring they fit naturally into the ongoing roleplay.
- **Random Seed Variety**: Each suggestion uses a random seed, ensuring different suggestions each time you press the button.
- **Seamless Integration**: Generated suggestions are automatically populated into the chat input box with the cursor positioned at the end, ready to edit or send.
- **User Control**: Users can press Suggest multiple times to get different suggestions, edit them as needed, or send them directly.

### 🤖 New Feature: Auto Mode
- **Automatic Story Evolution**: Added an "Auto" button that continuously generates user message suggestions and automatically submits them, allowing the story to evolve automatically without manual intervention.
- **Continuous Cycle**: Auto mode generates a suggestion, submits it to the AI, waits for the AI response, then generates another suggestion in an endless cycle.
- **Stop Control**: Auto mode only stops when the user presses the Stop button, giving full control over when to pause the automatic story progression.
- **Random Seed Variety**: Each auto-generated suggestion uses a random seed, ensuring varied and natural story progression.
- **Vector Chat Integration**: Auto mode is especially great for vector chat (RAG) as it automatically builds a vector database by generating and storing conversation exchanges continuously, creating a rich knowledge base for future roleplay sessions.
- **Dream-Like Perpetuating State**: Combine Auto mode with Vector Chat to create a dream-like perpetuating state where the AI continuously generates and stores interconnected content, building rich, evolving narratives that reference and build upon previous exchanges stored in the vector database.
- **UI Lockdown**: During auto mode, all buttons except Stop are disabled, and the action menu, style selector, and username field are also disabled to prevent interference.

### 🔧 Technical Improvements
- **Thread-Safe Generation**: Suggestion generation runs in a separate worker thread with proper locking to prevent race conditions.
- **Proper State Management**: Suggest and Auto buttons follow the same disable logic as other action buttons (disabled when AI is generating).
- **Clean Text Processing**: Suggestions are automatically cleaned of formatting artifacts like quotes and user name prefixes.
- **Auto Mode State Management**: Comprehensive UI state management ensures all interactive elements are properly disabled during auto mode to prevent conflicts.

## v0.4.7: Random Seed Management for Chat Variety
### 🎲 New Feature: Automatic Seed Management
- **Random Seed Generation**: Each new chat session now automatically generates a fresh random seed, ensuring different outputs even with identical prompts.
- **Seed on New Chat**: Clicking "Restart" or "New" (Clear Chat) generates a new random seed for the session.
- **Seed on Regenerate**: The "Regenerate" button now generates a new seed each time, ensuring varied regenerations without model reload.
- **Seed on Card Load**: Loading a character card (or reloading the same card) generates a new random seed, ensuring variety in character interactions.
- **Seed in AI Card Editor**: Each message sent to the AI card editor generates a new seed, providing varied AI responses for character card editing.
- **No Model Reload Required**: Previously, users had to reload the model to get different outputs with the same prompt. Now seeds are managed automatically without the performance cost of model reloading.
- **Cross-Backend Support**: Seed management works with both local llama.cpp inference and Ollama API inference.

### 🔧 Technical Improvements
- **Seed Parameter**: Added seed parameter support to `create_chat_completion` calls in both local and Ollama inference modes.
- **Automatic Initialization**: Seed is automatically initialized with a random value on app startup.
- **Session-Based Seeds**: Each chat session maintains its own seed, ensuring consistency within a conversation while allowing variety between sessions.
- **Comprehensive Seed Coverage**: Seeds are now generated for all AI interaction points: new chats, regenerations, card loading, and AI card editor messages.

## v0.4.6: Portable Python Bundling & Simplified Installation
### 🐍 Portable Python Integration
- **Automatic Python 3.12.12 Bundling**: All launch scripts now automatically download and use portable Python 3.12.12, eliminating the need for users to install Python separately.
- **Zero Configuration**: Users no longer need to worry about Python installation, PATH configuration, or version compatibility issues.
- **Cross-Platform Support**: 
  - **Linux**: Downloads `cpython-3.12.12+20260114-x86_64-unknown-linux-gnu-install_only.tar.gz` (~50MB)
  - **Windows**: Downloads `cpython-3.12.12+20260114-x86_64-pc-windows-msvc-install_only_stripped.tar.gz` (~50MB)
- **Smart Fallback**: If portable Python download fails, scripts gracefully fall back to system Python.
- **One-Time Download**: Portable Python is cached in `python_portable/` directory and reused on subsequent launches.

### 🎨 UI Enhancements
- **Python Version Display**: Status bar now shows the running Python version (e.g., "Python 3.12.12 | aiMultiFool v0.4.6") in the bottom-right corner.
- **Version Visibility**: Users can easily verify which Python version is running the application.

### 🔧 Technical Improvements
- **Unified Launch Scripts**: All 4 launch scripts (`run_linux_gpu.sh`, `run_linux_cpu.sh`, `run_windows_gpu.bat`, `run_windows_cpu.bat`) now include portable Python setup logic.
- **Automatic Extraction**: Scripts automatically extract the portable Python archive after download.
- **Venv Integration**: Portable Python is used to create virtual environments, ensuring consistent Python version across all installations.
- **Git Ignore**: Added `python_portable/` to `.gitignore` to keep repository clean.

### 📚 Documentation Updates
- **Simplified Installation**: Updated README.md and HOWTO_INSTALL.md to reflect that Python installation is no longer required.
- **Version Updates**: All documentation files updated to v0.4.6.

## v0.4.5: Scenarios Category & Enhanced Roleplay Features
### 🎭 New Feature: Scenarios Category
- **52 Engaging Scenarios**: Added a comprehensive "Scenarios" category to the action menu with 52 diverse roleplay scenarios covering adventure, fantasy, sci-fi, horror, thriller, and erotic genres.
- **User Protagonist**: All scenarios use `{{user}}` placeholder that automatically replaces with the user's name, making them the protagonist of every story.
- **40 Preset Scenarios**: Curated roleplay scenarios including:
  - **Adventure & Sci-Fi**: Last Stand on Mars, Space Station Sabotage, Cyberpunk Heist, Parallel Universe Portal, Lost City of Atlantis
  - **Fantasy & Magic**: Dragon's Last Egg, Ancient Curse Awakens, Urban Fantasy Awakening, Vampire's Masquerade, Steampunk Revolution
  - **Thriller & Mystery**: Corporate Conspiracy, Haunted Mansion Mystery, Noir Detective Case, Psychological Thriller, Post-Apocalyptic Courier
  - **Action & Survival**: Time Loop Paradox, Superhero Origin, Wild West Showdown, Survival Island, Zombie Outbreak Patient Zero, Medieval Tournament Champion
  - **Romance & Erotic**: Forbidden Affair, Sensual Masquerade, Power Exchange, Tempting Roommate, Office Fantasy, Vampire's Seduction, Beach Encounter, Training Session, Stranger in the Bar, Neighbor's Secret, Fantasy Fulfillment, Reunion Passion, Sensual Massage, Dangerous Liaison, Awakening, Forced Proximity, Tempting Teacher, Midnight Encounter, Complete Surrender
- **12 Random Scenario Generators**: Dynamic scenario generators that create unique roleplay scenarios on demand:
  - Adventure, Fantasy, Sci-Fi, Horror, Mystery, Romance, Survival, Superhero, Historical, Modern Drama, Erotic, Completely Random
- **Always Replace User**: Fixed `{{user}}` replacement to work regardless of character card loading status, ensuring scenarios work perfectly in all contexts.

### 🔧 Technical Improvements
- **Universal User Replacement**: Updated action menu handler to always replace `{{user}}` with the username, not just when character cards are loaded.
- **Roleplay Clarity**: All scenarios explicitly state "This is a roleplay scenario where..." to ensure clear context for the AI.

## v0.4.4: GPU/CPU Mode Separation & Simplified Installation
### 🎮 GPU/CPU Mode Separation
- **Separate Run Scripts**: Added dedicated `run_linux_gpu.sh`/`run_windows_gpu.bat` and `run_linux_cpu.sh`/`run_windows_cpu.bat` scripts for GPU and CPU modes respectively.
- **Independent Virtual Environments**: Each mode uses its own virtual environment (`venv_gpu` or `venv_cpu`) to prevent dependency conflicts.
- **CPU Mode Simplification**: CPU mode no longer requires CUDA toolkit installation, making it perfect for systems without NVIDIA GPUs.
- **CPU Mode Flag**: Added `--cpu` command-line flag to disable GPU layers control in CPU mode.

### 🔧 Technical Improvements
- **CPU Mode Detection**: App automatically detects CPU mode and hides GPU layers control in Model Settings modal.
- **GPU Layers Default**: GPU mode now defaults to -1 (all GPU layers) instead of 0 (CPU only).
- **Settings Management**: GPU layers automatically reset to -1 when switching from CPU mode to GPU mode.

### 📚 Documentation Updates
- **Updated Installation Guides**: Both README.md and HOWTO_INSTALL.md now include separate sections for GPU and CPU installation.
- **Clear Requirements**: Requirements are now clearly separated into GPU Mode and CPU Mode sections.
- **Installation Simplification**: CPU mode installation instructions omit CUDA toolkit requirements.

## v0.4.3: Action Management Enhancements & Export/Import & Games Category
### 🎯 Action Menu Management Improvements
- **Batch Editing**: Action menu edits are now batched - changes are only saved when clicking "Apply". The "Cancel" button discards all edits and restores the original state.
- **Export/Import**: Export all actions or category-specific actions to JSON files, and import actions with automatic duplicate detection.
- **Category Management**: Delete entire categories of actions with confirmation dialogs.
- **Modal Layout**: Most modals are now laid out with right side buttons for improved consistency and user experience.

### 🎮 New Feature: Games Category
- **Games Category**: Added a new "Games" category to the action menu with 21 interactive games to play with AI, including Would You Rather, Truth or Dare, Two Truths and a Lie, Never Have I Ever, 20 Questions, Story Building Game, Word Association, Riddles, Trivia Challenge, and more.

## v0.4.2: RLM Chat Removal & Code Cleanup
### 🧹 Code Cleanup: Removed RLM Chat Feature
- **RLM Chat Removal**: Removed RLM Chat feature from the application. Vector Chat (RAG) provides similar functionality with better performance and simpler implementation.
- **Code Simplification**: Removed `RLMMixin` class and all RLM-related code from `logic_mixins.py`, reducing codebase complexity.
- **UI Cleanup**: Removed RLM Chat button from the top menu bar and all related UI components (`RLMChatScreen`, `RLMInspectScreen`).
- **Documentation Updates**: Updated PRD.md, README.md, and SECURITY_AUDIT.md to reflect the removal of RLM Chat functionality.
- **CSS Cleanup**: Removed all RLM-related CSS styles from `styles.tcss`.

### 📝 Technical Changes
- **Mixin Removal**: Removed `RLMMixin` from `AiMultiFoolApp` class inheritance.
- **Import Cleanup**: Removed `RLMMixin` and `RLMChatScreen` imports from `aimultifool.py` and `widgets.py`.
- **State Management**: Removed RLM-related reactive properties (`rlm_chat_name`, `enable_rlm_chat`, `rlm_password`) from the app.
- **Inference Pipeline**: Removed RLM context retrieval and saving code from the inference pipeline.

## v0.4.1: Improved RLM Implementation with Intelligent Search
### 🧠 Enhanced RLM Chat: MIT-Inspired Recursive Querying
- **LLM-Generated Search Queries**: RLM Chat now uses the language model itself to generate optimized search queries based on user input, implementing the recursive querying approach from MIT's RLM research.
- **Multi-Strategy Search**: Implemented sophisticated search combining keyword matching, semantic similarity (when embeddings available), and temporal relevance scoring.
- **Intelligent Context Retrieval**: The model analyzes user queries and generates targeted search queries to find the most relevant conversation history, then executes searches using prewritten Python functions for safety and reliability.
- **Improved Relevance Scoring**: Messages are scored using keyword match counts, recency bonuses, and semantic similarity (when available) to prioritize the most relevant context.
- **Better Performance**: Optimized search strategies sample from recent, middle, and old sections of conversation history to balance relevance and efficiency.

### 🔧 Technical Improvements
- **Recursive Query Generation**: `query_rlm_context()` now uses LLM to generate search queries before executing searches, aligning with MIT RLM approach.
- **Prewritten Search Functions**: Added `_search_rlm_store()` method with multiple search strategies executed safely via prewritten Python code.
- **Semantic Integration**: When embedding models are available, RLM Chat uses semantic similarity alongside keyword matching for better context retrieval.
- **Manual Cosine Similarity**: Implemented cosine similarity calculation without numpy dependency for semantic search scoring.
- **Deduplication**: Results are deduplicated while preserving order to avoid redundant context in prompts.

### 📚 Documentation Updates
- **RLM Implementation Details**: Updated documentation to reflect the improved recursive querying implementation.
- **Search Strategy Documentation**: Added details about multi-strategy search approach in RLM Chat.

## v0.4.0: RLM Chat & Enhanced Context Management
### 🧠 New Feature: RLM Chat (Recursive Language Models)
- **RLM Chat Support**: Added support for Recursive Language Models, enabling management of very long conversations by storing complete conversation history externally and querying it recursively.
- **Complete History Preservation**: RLM Chat stores full conversation history in external JSON files, ensuring nothing is ever lost even in extended roleplay sessions.
- **Optional Encryption**: RLM context stores support optional **AES-256-GCM** encryption with **Argon2id** key derivation, keeping your complete conversation history secure on disk.
- **RLM Chat Management**: Full suite of tools to create, duplicate, rename, delete, and inspect RLM context stores directly from the new **RLM Chat** modal.
- **Seamless Integration**: Toggle RLM Chat on/off mid-conversation to enhance characters with complete historical context beyond the standard context window.
- **Password Protection**: Encrypted RLM chats require password validation before loading, ensuring secure access to your conversation history.
- **Storage Location**: RLM context stores are saved to `rlmcontexts/{chat_name}/` directory with `context.json` containing the full message history.

### 🔧 Technical Improvements
- **RLM Context Management**: Implemented `RLMMixin` with methods for initializing, saving, and closing RLM context stores.
- **Encryption Support**: RLM context stores use the same AES-256-GCM encryption system as Vector Chat and saved chats.
- **Password Validation**: Added robust password validation system for encrypted RLM chats with verification file support.
- **Context Store Lifecycle**: Proper lifecycle management ensures RLM context stores are saved automatically when switching chats or closing the app.

### 📚 Documentation Updates
- **RLM Chat Documentation**: Added comprehensive RLM Chat information to README, including feature description and encryption details.
- **Comparison Guide**: Updated `RAG_VS_RLM.md` with detailed comparison between Vector Chat (RAG) and RLM Chat approaches.
- **Storage Path Correction**: Updated all references from `rlm_contexts` to `rlmcontexts` to match actual folder structure.

## v0.3.0: Ollama Inference Support & Enhanced Quick Start
### 🚀 New Feature: Ollama Inference Mode
- **Ollama Integration**: Added support for using Ollama-managed models alongside local GGUF models, providing flexibility in model management and deployment.
- **Seamless Switching**: Toggle between Local and Ollama inference modes directly from the Model settings screen.
- **Ollama Model Detection**: Automatic detection of available Ollama models and connection status.
- **Unified Interface**: Ollama models work seamlessly with all existing features including Vector Chat, character cards, and action menus.

### 📚 Documentation Improvements
- **Quick Start Guide**: Added comprehensive Quick Start section to README with step-by-step instructions for both Local and Ollama inference modes.
- **Model Download Instructions**: Clear instructions for downloading required models in both modes:
  - Local mode: Use the built-in "Download Models" button
  - Ollama mode: Terminal commands for downloading required models

## v0.2.6: Card Management Enhancements & UI Improvements
### 🎴 Enhanced Card Management Workflow
- **Improved Duplication Behavior**: When duplicating a card, all cards are now deselected and metadata display is cleared, providing a cleaner workflow.
- **Save Changes Button Logic**: The "Save Changes" button is now only enabled when metadata has been manually edited or AI has finished editing, preventing unnecessary save operations.
- **Unsaved Changes Protection**: Rename and Duplicate buttons are now disabled when there are unsaved changes, ensuring data integrity.
- **New Card Protection**: For newly created cards, Rename, Play, and Duplicate buttons are disabled until the card has been edited, preventing operations on empty template cards.
- **AI Editing State Management**: All buttons (except play buttons) are disabled while AI is editing metadata, preventing conflicts during the editing process.
- **Play Button Safety**: Play buttons remain disabled for newly created cards until they are saved, ensuring only complete cards can be used for roleplay.
- **Auto-Deselection After Save**: After saving a card, it is automatically deselected to provide clear visual feedback that the operation completed successfully.

### 🎨 UI Refinements
- **Button Label Update**: The "Clear" button on the main UI has been renamed to "New" for better clarity and consistency.

## v0.2.5: Unified Action Menu System
### 🎯 Major UI Refinement: Flexible Action Menu
- **Removed Dedicated Buttons**: Removed the dedicated "Emotions" and "Stats" buttons in favor of a unified, flexible action menu system.
- **Action Menu Integration**: Emotion analysis and character stats analysis are now accessible through the action menu's "Analysis" category, alongside other analysis tools like relationship mapping, power dynamics, and character motivations.
- **Improved Organization**: All roleplay tools are now organized by category in the action sidebar, making it easier to discover and use features without cluttering the main interface.
- **Enhanced Flexibility**: Users can customize, duplicate, and create their own actions through the Action Manager, providing unlimited extensibility for roleplay workflows.
- **Cleaner Interface**: The removal of dedicated buttons creates a cleaner, more streamlined main interface while maintaining full functionality through the comprehensive action menu.

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


