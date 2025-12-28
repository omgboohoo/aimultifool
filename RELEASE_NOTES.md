# Release Notes
 
## v0.1.9: Speed, Safety & Stats
- **Smart Rewind**: Rewinding now automatically restores the last user message to the input box for rapid correction and resending.
- **Streamlined Launch**: `run.sh` now intelligently skips the venv setup and recreation prompts if a virtual environment is already present, ensuring the fastest possible startup.
- **Lapse-Free Loading**: Optimized the model selection workflow—the modal now closes and locks UI controls before initializing resource-heavy model loading, eliminating visual lag.
- **Performance Metrics**: Integrated **"Peak TPS"** tracking into the status bar, providing real-time visibility into your hardware's maximum generation speed during every interaction.

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


