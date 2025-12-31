# Release Notes

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


