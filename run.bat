@echo off
setlocal enabledelayedexpansion

:: Setup script for aiMultiFool console chat app (Windows)

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "VENV_DIR=%SCRIPT_DIR%\venv"

:: Universal Multi-Arch Wheel Configuration
set "WHEEL_NAME=llama_cpp_python-0.3.16-cp312-cp312-win_amd64.whl"
set "WHEEL_URL=https://aimultifool.com/llama_cpp_python-0.3.16-cp312-cp312-win_amd64.whl"
set "WHEEL_DIR=%SCRIPT_DIR%\llama.cpp"
set "WHEEL_PATH=%WHEEL_DIR%\%WHEEL_NAME%"

echo ----------------------------------------------------------------
echo   aiMultiFool Suite - Setup ^& Launch Script v0.1.9 (Windows)
echo ----------------------------------------------------------------

:: Ensure CUDA is in PATH (in case terminal wasn't restarted after CUDA install)
:: CUDA 13.x stores DLLs in bin\x64, older versions use bin directly
if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin\x64" (
    set "PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin\x64;C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v13.1\bin;%PATH%"
) else if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin" (
    set "PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6\bin;%PATH%"
) else if exist "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin" (
    set "PATH=C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4\bin;%PATH%"
)

:: 1. Ensure the llama.cpp directory exists
if not exist "%WHEEL_DIR%" (
    echo [SYSTEM] Creating directory for binaries: %WHEEL_DIR%
    mkdir "%WHEEL_DIR%"
)

:: 2. Check if the wheel exists locally, if not attempt download
if exist "%WHEEL_PATH%" (
    echo [FOUND] Using existing local Multi-Arch wheel: %WHEEL_NAME%
) else (
    echo [MISSING] Universal wheel not found locally.
    echo [NETWORK] Starting download ^(~235MB^) to ensure GPU acceleration...
    echo [SOURCE]  %WHEEL_URL%
    
    :: Try curl first (available on Windows 10+), then PowerShell
    where curl >nul 2>&1
    if !errorlevel! equ 0 (
        curl -L --progress-bar -o "%WHEEL_PATH%" "%WHEEL_URL%"
        if !errorlevel! neq 0 (
            echo [ERROR] Download failed with curl.
            del "%WHEEL_PATH%" 2>nul
        )
    ) else (
        echo [INFO] Using PowerShell for download...
        powershell -Command "& { $ProgressPreference = 'Continue'; Invoke-WebRequest -Uri '%WHEEL_URL%' -OutFile '%WHEEL_PATH%' }"
        if !errorlevel! neq 0 (
            echo [ERROR] Download failed with PowerShell.
            del "%WHEEL_PATH%" 2>nul
        )
    )
    
    if exist "%WHEEL_PATH%" (
        echo [SUCCESS] Multi-Arch wheel downloaded successfully!
    ) else (
        echo [ERROR] Download failed. The app may run slowly without GPU acceleration.
    )
)

:: Find the latest wheel (prefer Windows wheel, fallback to any)
set "WHEEL_FILE="
for %%f in ("%WHEEL_DIR%\llama_cpp_python-*-win_amd64.whl") do set "WHEEL_FILE=%%f"
if not defined WHEEL_FILE (
    for %%f in ("%WHEEL_DIR%\llama_cpp_python-*.whl") do set "WHEEL_FILE=%%f"
)

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
        echo [LAUNCH] Starting aiMultiFool TUI...
        echo.
        python "%SCRIPT_DIR%\aimultifool.py"
        goto :end
    )
)

:: Create virtual environment
echo [STEP 1/4] Creating fresh virtual environment ^(venv^)...
py -m venv "%VENV_DIR%"

:: Activate virtual environment
echo [STEP 2/4] Activating environment...
call "%VENV_DIR%\Scripts\activate.bat"

:: Upgrade pip
echo [STEP 3/4] Upgrading pip to latest version...
python -m pip install -q --upgrade pip

:: Install llama-cpp-python wheel
if defined WHEEL_FILE (
    if exist "!WHEEL_FILE!" (
        echo [STEP 4/4] Installing Multi-Arch CUDA Backend: !WHEEL_FILE!
        pip install -q "!WHEEL_FILE!"
        echo [SUCCESS] CUDA Backend installed.
    ) else (
        goto :fallback_install
    )
) else (
    :fallback_install
    echo [WARNING] No pre-built wheel found. Falling back to generic install ^(CPU only if no toolkit^)...
    set "CMAKE_ARGS=-DGGML_CUDA=on"
    pip install -q llama-cpp-python
)

:: Install other dependencies
echo [FINISHING] Finalizing remaining dependencies...
if exist "%SCRIPT_DIR%\requirements.txt" (
    pip install -q -r "%SCRIPT_DIR%\requirements.txt"
) else (
    pip install -q rich requests tqdm textual
)

echo [DONE] Setup complete! Launching...
echo.
python "%SCRIPT_DIR%\aimultifool.py"

:end
endlocal

