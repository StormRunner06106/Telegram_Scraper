@echo off
REM GScraper launcher for Windows

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Run gscraper
python gscraper.py

pause
