@echo off
setlocal enabledelayedexpansion

:: Define log folder and file paths
set "LOGS_DIR=logs"
set "START_LOG_FILE=%LOGS_DIR%\start_log.txt"
set "BOT_LOG_FILE=%LOGS_DIR%\bot_log.txt"

:: Create logs directory if it doesn't exist
if not exist "%LOGS_DIR%" (
  mkdir "%LOGS_DIR%"
)

:: --- Redirect all output of this batch script to START_LOG_FILE ---
:: Delete previous start log file to start fresh for the batch script's output
del "%START_LOG_FILE%" >nul 2>&1
:: Call the main part of the script, redirecting all its output
call :main_script > "%START_LOG_FILE%" 2>&1
goto :eof

:main_script
:: --- All original content of your start.bat goes here ---
:: Ensure that 'python' calls below are NOT followed by '>>' or '>' redirection here,
:: as the Python scripts themselves will handle their own logging to bot_log.txt.

echo ==================================================
echo [STEP 0] Checking Python Installation...
echo ==================================================

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
  echo ERROR: Python is not installed or not added to PATH.
  echo Please install Python 3.x and add it to PATH.
  pause
  exit /b
)
echo SUCCESS: Python is installed.
echo.

:: Step 1: Create virtual environment if missing
if not exist "venv" (
  echo ==================================================
  echo [STEP 1] Creating Python Virtual Environment...
  echo ==================================================
  python -m venv venv
  IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b
  )
)
echo SUCCESS: Virtual environment exists or created.
echo.

:: Step 2: Activate virtual environment
echo ==================================================
echo [STEP 2] Activating Virtual Environment...
echo ==================================================
call venv\Scripts\activate.bat
IF %ERRORLEVEL% NEQ 0 (
  echo ERROR: Failed to activate virtual environment.
  pause
  exit /b
)
echo SUCCESS: Virtual environment activated.
echo.

:: Step 3: Upgrade pip
echo ==================================================
echo [STEP 3] Upgrading pip...
echo ==================================================
python -m pip install --upgrade pip >nul
echo SUCCESS: Pip upgraded.
echo.

:: Step 4: Install required Python packages (Telethon and python-dotenv only)
echo ==================================================
echo [STEP 4] Installing Python Dependencies (Telethon and python-dotenv only)...
echo ==================================================

:: Check and install telethon
python -c "import telethon" >nul 2>&1 || (
  echo Installing Telethon...
  pip install telethon
)

:: Check and install python-dotenv
python -c "import dotenv" >nul 2>&1 || (
  echo Installing python-dotenv...
  pip install python-dotenv
)

:: Check and install pytz
python -c "import pytz" >nul 2>&1 || (
  echo Installing pytz...
  pip install pytz
)

echo SUCCESS: All dependencies checked/installed.
echo.

:: Step 5: Validate configurations
echo ==================================================
echo [STEP 5] Validating Configurations...
echo ==================================================
:: This output will go to start_log.txt because start.bat is redirected
python helpers\validate_config.py
IF %ERRORLEVEL% NEQ 0 (
  echo ERROR: Configuration validation failed.
  echo.
  echo Please check the error messages above for details and fix your .env or proj_config.json.
  pause
  exit /b
)
echo SUCCESS: All configurations validated successfully!
echo.

:: Step 6: Run the Telegram Channel Forwarder Bot
echo ==================================================
echo [STEP 6] Running Telegram Channel Forwarder Bot...
echo ==================================================
:: This script will handle its own logging to bot_log.txt
python telegram_channel_forwarder.py

:: Final pause to keep the console open after the bot exits
pause
:: --- END of main_script content ---