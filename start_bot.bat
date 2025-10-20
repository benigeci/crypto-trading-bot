@echo off
REM Crypto Trading Bot Startup Script for Windows

echo ================================================================
echo            Cryptocurrency Trading Bot Launcher
echo ================================================================
echo.

REM Change to bot directory
cd /d "%~dp0"

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup first: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo Please create .env file from .env.example
    pause
    exit /b 1
)

REM Start the bot
echo [INFO] Starting trading bot...
echo.
python main.py

REM Keep window open if bot exits
pause
