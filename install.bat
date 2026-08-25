@echo off
REM HoopSync Installation Script for Windows

echo 🏀 HoopSync Installation
echo =======================
echo.

REM Check Python version
echo Checking Python version...
python --version
if %ERRORLEVEL% NEQ 0 (
    echo ❌ Python is not installed. Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo ✅ Python found
echo.

REM Create virtual environment (optional but recommended)
echo Creating virtual environment...
python -m venv venv
if %ERRORLEVEL% NEQ 0 (
    echo ⚠️  Could not create virtual environment, continuing with system Python...
) else (
    echo ✅ Virtual environment created
    
    REM Activate virtual environment
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
    echo ✅ Virtual environment activated
)

echo.
echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo ✅ Dependencies installed
echo.

REM Create necessary directories
echo Creating directories...
if not exist "data" mkdir data
if not exist "logs" mkdir logs
if not exist "models\templates" mkdir models\templates
echo ✅ Directories created
echo.

echo 🎉 Installation complete!
echo.
echo To run HoopSync:
echo   run_hoopsync.bat --help
echo.
echo Or with Python directly:
echo   python -m hoopsync.main --help
echo.
echo For first-time setup, test video capture:
echo   python -m hoopsync.main --test-capture
echo.
pause
