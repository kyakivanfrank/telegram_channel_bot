@echo off
setlocal enabledelayedexpansion

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

:: Step 1: Check and Install Python Dependencies from requirements.txt
echo ==================================================
echo [STEP 1] Checking and Installing Python Dependencies...
==================================================

:: Check if requirements.txt exists
if not exist "requirements.txt" (
  echo ERROR: requirements.txt not found. Cannot install dependencies.
  pause
  exit /b
)

:: Install all dependencies listed in requirements.txt
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
  echo ERROR: Failed to install Python dependencies.
  echo.
  echo Please check the error messages above and ensure you have pip installed and a working internet connection.
  pause
  exit /b
)

echo SUCCESS: All dependencies checked/installed.
echo.

:: Step 2: Validate Configurations...
echo ==================================================
echo [STEP 2] Validating Configurations...
==================================================
:: This output will now go directly to the console
python frank_bot\helpers\validate_config.py
IF %ERRORLEVEL% NEQ 0 (
  echo ERROR: Configuration validation failed.
  echo.
  echo Please check the error messages above for details and fix your .env or proj_config.json.
  pause
  exit /b
)
echo SUCCESS: All configurations validated successfully!
echo.

:: Step 3: Run the Telegram Channel Forwarder Bot...
echo ==================================================
echo [STEP 3] Running Telegram Channel Forwarder Bot...
==================================================
:: This script will now output its logs directly to the console
python frank_bot\telegram_channel_forwarder.py

:: Add a pause at the end to keep the terminal open after execution
pause
