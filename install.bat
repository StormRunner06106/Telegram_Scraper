@echo off
REM Installation script for GitHub Scraper (Windows)

echo ==========================================
echo   GitHub Scraper - Installation
echo ==========================================
echo.

REM Check Python version
echo Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)
python --version
echo OK: Python found
echo.

REM Install dependencies
echo Installing dependencies...
set /p install_supabase="Install Supabase support? (Y/n): "

if /i "%install_supabase%"=="n" (
    echo Skipping Supabase installation
) else (
    pip install supabase
    if errorlevel 1 (
        echo Warning: Supabase installation failed (optional)
    ) else (
        echo OK: Supabase installed
    )
)
echo.

REM Create .env file
echo Setting up environment...
if not exist .env (
    copy .env.example .env
    echo OK: Created .env file
    echo Warning: Please edit .env with your credentials
) else (
    echo Skipping: .env already exists
)
echo.

REM Run setup test
echo Running setup test...
python test_setup.py
echo.

echo ==========================================
echo   Installation Complete!
echo ==========================================
echo.
echo Next steps:
echo   1. Edit .env with your credentials
echo   2. Run: python setup_supabase.py (optional)
echo   3. Run: python gscraper.py
echo.
echo Documentation:
echo   - README_MAIN.md - Main documentation
echo   - QUICK_REFERENCE.md - Quick commands
echo   - SETUP_GUIDE.md - Detailed setup
echo.
pause
