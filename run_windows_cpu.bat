@echo off
setlocal enabledelayedexpansion

:: Setup script for aiMultiFool console chat app (CPU-only mode, Windows)

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "VENV_DIR=%SCRIPT_DIR%\venv_cpu"

echo ----------------------------------------------------------------
echo   aiMultiFool Suite - CPU-Only Setup ^& Launch Script v0.1.9 (Windows)
echo ----------------------------------------------------------------

:: Check if venv already exists
if exist "%VENV_DIR%" (
    echo [STATUS] Virtual environment detected.
    echo [INFO]   It is recommended to reinstall ^(y^) if you just updated to a new version.
    set /p "choice=Do you want to reinstall the environment? [y/N] (Default: n): "
    if /i "!choice!"=="y" (
        echo [ACTION] Reinstalling environment...
        rmdir /s /q "%VENV_DIR%"
    ) else (
        echo [SKIP] Skipping environment setup.
        call "%VENV_DIR%\Scripts\activate.bat"
        echo [LAUNCH] Starting aiMultiFool TUI ^(CPU mode^)...
        echo.
        python "%SCRIPT_DIR%\aimultifool.py" --cpu
        goto :end
    )
)

:: Create virtual environment
echo [STEP 1/3] Creating fresh virtual environment ^(venv_cpu^)...
py -m venv "%VENV_DIR%"

:: Activate virtual environment
echo [STEP 2/3] Activating environment...
call "%VENV_DIR%\Scripts\activate.bat"

:: Upgrade pip
echo [STEP 3/3] Upgrading pip to latest version...
python -m pip install -q --upgrade pip

:: Install llama-cpp-python (CPU-only, no CUDA)
echo [INSTALL] Installing llama-cpp-python ^(CPU-only^)...
pip install -q llama-cpp-python

:: Install other dependencies
echo [FINISHING] Finalizing remaining dependencies...
if exist "%SCRIPT_DIR%\requirements.txt" (
    pip install -q -r "%SCRIPT_DIR%\requirements.txt"
) else (
    pip install -q rich requests tqdm textual
)

echo [DONE] Setup complete! Launching in CPU mode...
echo.
python "%SCRIPT_DIR%\aimultifool.py" --cpu

:end
endlocal
