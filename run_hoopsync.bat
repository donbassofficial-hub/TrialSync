@echo off
REM HoopSync - NBA 2K Statistics Pipeline
REM Windows executable entry point

python hoopsync\main.py %*

if %ERRORLEVEL% NEQ 0 (
    echo Error running HoopSync
    echo Make sure you have installed the required dependencies:
    echo pip install -r requirements.txt
    pause
    exit /b 1
)
