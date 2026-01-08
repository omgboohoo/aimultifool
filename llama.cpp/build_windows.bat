@echo off
setlocal enabledelayedexpansion

:: Build llama-cpp-python with CUDA support for Windows
:: Optimized for portability across multiple GPU generations (Fat Binary)

echo Building aiMultiFool llama-cpp-python with Multi-Arch CUDA support...
echo ====================================================================

:: Check if we're in the right directory (check for aimultifool.py or similar)
if exist "aimultifool.py" (
    set "ROOT_DIR=%CD%"
) else if exist "..\aimultifool.py" (
    cd ..
    set "ROOT_DIR=%CD%"
) else (
    echo Error: Please run this script from the aiMultiFool root directory
    echo        or from the llama.cpp subdirectory.
    exit /b 1
)

echo Working from: %ROOT_DIR%

:: Check if CUDA is available
where nvcc >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: CUDA toolkit ^(nvcc^) not found. Please install CUDA toolkit first.
    echo You can download it from: https://developer.nvidia.com/cuda-downloads
    echo After installation, make sure nvcc is in your PATH ^(restart your terminal^).
    exit /b 1
)

echo CUDA toolkit found:
nvcc --version | findstr /C:"release"

:: Check if git is available
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: git not found. Please install git first.
    echo You can download it from: https://git-scm.com/download/win
    exit /b 1
)

:: Set up Visual Studio environment for Ninja builds
echo Setting up Visual Studio build environment...
set "VSWHERE=%ProgramFiles(x86)%\Microsoft Visual Studio\Installer\vswhere.exe"
if exist "%VSWHERE%" (
    for /f "usebackq tokens=*" %%i in (`"%VSWHERE%" -latest -requires Microsoft.VisualStudio.Workload.NativeDesktop -property installationPath`) do set "VS_PATH=%%i"
)
if not defined VS_PATH (
    :: Fallback to common paths
    if exist "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat" (
        set "VCVARS=C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsall.bat"
    ) else if exist "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" (
        set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat"
    ) else if exist "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat" (
        set "VCVARS=C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvarsall.bat"
    )
) else (
    set "VCVARS=%VS_PATH%\VC\Auxiliary\Build\vcvarsall.bat"
)

if defined VCVARS (
    echo Initializing Visual Studio environment from: %VCVARS%
    call "%VCVARS%" x64
) else (
    echo Warning: Could not find Visual Studio vcvarsall.bat
    echo Build may fail. Please install Visual Studio Build Tools.
)

:: Create build directory
set "BUILD_DIR=llama_cpp_build"
if exist "%BUILD_DIR%" (
    echo Removing existing build directory...
    rmdir /s /q "%BUILD_DIR%"
)

mkdir "%BUILD_DIR%"
cd "%BUILD_DIR%"

echo.
echo 1. Cloning llama-cpp-python repository...
git clone https://github.com/abetlen/llama-cpp-python.git
if %errorlevel% neq 0 (
    echo Error: Failed to clone repository
    exit /b 1
)
cd llama-cpp-python

echo.
echo 2. Pulling submodules...
git submodule update --init --recursive
if %errorlevel% neq 0 (
    echo Error: Failed to update submodules
    exit /b 1
)

echo.
echo 3. Setting up Multi-Architecture CUDA build environment...
:: CUDA 13.x dropped Pascal support. Supported architectures:
:: 75 = Turing (RTX 20-series, GTX 16-series), 86 = Ampere (RTX 30-series), 89 = Ada (RTX 40-series), 100 = Blackwell (RTX 50-series)
:: Using Ninja generator for better CUDA compatibility
:: Adding -allow-unsupported-compiler for newer Visual Studio versions
set "CMAKE_GENERATOR=Ninja"
set "CMAKE_ARGS=-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=75;86;89;100 -DCMAKE_CUDA_FLAGS=-allow-unsupported-compiler"
set "FORCE_CMAKE=1"

echo Using architectures: 7.5 ^(Turing^), 8.6 ^(Ampere^), 8.9 ^(Ada^), 10.0 ^(Blackwell^)

echo.
echo 4. Building the wheel...
py -m pip wheel . --wheel-dir dist
if %errorlevel% neq 0 (
    echo Error: Failed to build wheel
    exit /b 1
)

:: Check if we're in a virtual environment and install
echo.
echo 5. Installing the built wheel...
if defined VIRTUAL_ENV (
    echo Virtual environment detected: %VIRTUAL_ENV%
    for %%f in (dist\llama_cpp_python-*.whl) do (
        py -m pip install "%%f" --force-reinstall
    )
) else (
    echo No virtual environment detected. Wheel built successfully but not installed.
    echo The wheel file is located in: %CD%\dist\
    echo You can install it later with: py -m pip install dist\llama_cpp_python-*.whl
)

:: Copy wheel to project llama.cpp folder
set "DEST_DIR=%ROOT_DIR%\llama.cpp"
if exist "%DEST_DIR%" (
    echo.
    echo 6. Copying built wheel to project directory...
    for %%f in (dist\llama_cpp_python-*.whl) do (
        copy "%%f" "%DEST_DIR%\"
    )
    echo Wheel copied to %DEST_DIR%
)

echo.
echo 7. Verifying CUDA support...
py -c "from llama_cpp import Llama; print('CUDA Support:', 'CUDA' in Llama.build_info())"

echo.
echo ====================================================================
echo Build completed successfully!
echo The wheel file is optimized for GTX 16-series through RTX 50-series.
echo You can now run aiMultiFool on different machines with different NVIDIA GPUs.
echo ====================================================================

:: Return to original directory
cd "%ROOT_DIR%"

endlocal
