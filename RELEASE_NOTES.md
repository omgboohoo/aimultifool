# Release Notes

## v0.1.4

- **Character Card Metadata Editor**: A brand new feature to view and modify SillyTavern PNG metadata directly within the app.
- **Improved Card Interaction**: Includes a toggle-able "Edit Mode" for character cards. When active, clicking a card opens the editor instead of loading the character.
- **Manual PNG Chunk Manipulation**: The app now handles `zTXt` chunk injection manually, ensuring character card compatibility without bloated dependencies.
- **UI Enhancements**: Added "Enter/Exit Edit Mode" button to the sidebar for a streamlined editing workflow.

## v0.1.3

- **Action Menu Search & Filtering**: Real-time search across action names and prompts with auto-expanding categories.
- **Debug Context Viewer**: New "Debug" top menu item to inspect the full JSON context being sent to the AI.
- **Dynamic Character Styling**: Styles (Concise, Dramatic, etc.) now correctly apply to character cards and update instantly during active chat.
- **Improved Focus Logic**: Automatically focuses the user input box after model loading and newly added/edited actions.
- **UI Refinements**: New top menu bar, reordered bottom action buttons, and smarter button disabling logic when no model is loaded.

## v0.1.2

- **Multi-Arch CUDA Support**: Built-in scripts now generate "Fat Binaries" supporting GTX 10-series (Pascal), RTX 20-series (Turing), RTX 30-series (Ampere), and RTX 40-series (Ada Lovelace). This fixes crashes when moving the app between different GPU generations.
- **Portability Fixes**: Improved `run.sh` and build scripts for better cross-distro compatibility.
- **UI Refinements**: Unified branding and versioning across all modules.

## v0.1.1

- Stability improvements for AI Stop/Restart logic.
- Prevented CUDA errors during rapid interruptions.

## v0.1.0

- Initial release of aiMultiFool.
- Character card support, real-time metrics, and modular architecture.
