# How to Upgrade aiMultiFool

## Overview

Upgrading is simple — download the latest release and copy the files over your existing installation. Your personal data (models, characters, chats, settings) is preserved automatically.

## Steps

1. **Download the latest release**:
   - [Download aiMultiFool (ZIP)](https://github.com/omgboohoo/aimultifool/archive/refs/heads/main.zip)

2. **Extract and copy over your existing installation**:
   - Extract the ZIP file.
   - Copy/overwrite the extracted files on top of your existing aiMultiFool folder.

3. **Launch as usual**:
   - Linux GPU: `./run_linux_gpu.sh`
   - Linux CPU: `./run_linux_cpu.sh`
   - Windows GPU: `run_windows_gpu.bat`
   - Windows CPU: `run_windows_cpu.bat`

The launch script will automatically update any new dependencies on the next run.

## What's Preserved

Your personal data lives in subfolders that are **not** included in the release, so they won't be overwritten:

- `models/` — your downloaded GGUF model files
- `cards/` — your character card PNGs
- `chats/` — your saved conversations
- `vectors/` — your Qdrant vector storage
- `settings.json` — your app settings
- `action_menu.json` — your customized action menu (if modified)

## Notes

- The `python_portable/` folder and virtual environment will be refreshed automatically by the launch script if needed.
- Check `docs/RELEASE_NOTES.md` after upgrading to see what's new.
