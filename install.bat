@echo off
REM Installation script for GitHub Location Scraper (Windows)

echo ==========================================
echo   GitHub Location Scraper - Installation
echo ==========================================

python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3.10 or newer is required.
    exit /b 1
)

echo Installing project dependencies...
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

if not exist .env (
    copy .env.example .env >nul
    echo Created .env. Add your GitHub token before running the scraper.
) else (
    echo Existing .env retained.
)

python check_env.py

echo.
echo Installation complete. See README.md, then run: python gscraper.py
