# Release Notes

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
