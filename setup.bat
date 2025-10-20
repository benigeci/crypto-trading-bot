@echo off
REM Setup script for first-time installation

echo ================================================================
echo       Cryptocurrency Trading Bot - First Time Setup
echo ================================================================
echo.

REM Change to bot directory
cd /d "%~dp0"

REM Check Python installation
echo [1/6] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.8 or higher from https://www.python.org/downloads/
    pause
    exit /b 1
)

python --version
echo [OK] Python is installed
echo.

REM Create virtual environment
echo [2/6] Creating virtual environment...
if exist "venv" (
    echo [INFO] Virtual environment already exists
) else (
    python -m venv venv
    echo [OK] Virtual environment created
)
echo.

REM Activate virtual environment
echo [3/6] Activating virtual environment...
call venv\Scripts\activate.bat
echo.

REM Upgrade pip
echo [4/6] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo [OK] Pip upgraded
echo.

REM Install dependencies
echo [5/6] Installing dependencies (this may take a few minutes)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] All dependencies installed
echo.

REM Create .env file if it doesn't exist
echo [6/6] Checking configuration...
if not exist ".env" (
    echo [INFO] Creating .env file from template...
    copy .env.example .env >nul
    echo [OK] .env file created - Please edit it with your configuration
) else (
    echo [INFO] .env file already exists
)
echo.

REM Create necessary directories
if not exist "data" mkdir data
if not exist "logs" mkdir logs
echo [OK] Directories created
echo.

echo ================================================================
echo                    Setup Complete!
echo ================================================================
echo.
echo Next Steps:
echo 1. Edit .env file with your Telegram bot token and settings
echo 2. Review config.yaml for trading parameters
echo 3. Run: python test_bot.py (to verify installation)
echo 4. Run: python main.py (to start the bot)
echo.
echo For detailed instructions, see README.md and DEPLOYMENT.md
echo.

pause
