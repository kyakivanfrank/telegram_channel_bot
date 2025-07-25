@echo off
setlocal enabledelayedexpansion

echo ==================================================
echo [STEP 0] Checking Python Installation...
echo ==================================================

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
  echo ❌ Python is not installed or not added to PATH.
  echo 🔧 Please install Python 3.x and add it to PATH.
  pause
  exit /b
)
echo ✅ Python is installed.
echo.

:: Step 1: Create virtual environment if missing
if not exist "venv" (
  echo ==================================================
  echo [STEP 1] Creating Python Virtual Environment...
  echo ==================================================
  python -m venv venv
  IF %ERRORLEVEL% NEQ 0 (
    echo ❌ Failed to create virtual environment.
    pause
    exit /b
  )
)
echo ✅ Virtual environment exists or created.
echo.

:: Step 2: Activate virtual environment
echo ==================================================
echo [STEP 2] Activating Virtual Environment...
echo ==================================================
call venv\Scripts\activate.bat
IF %ERRORLEVEL% NEQ 0 (
  echo ❌ Failed to activate virtual environment.
  pause
  exit /b
)
echo ✅ Virtual environment activated.
echo.

:: Step 3: Upgrade pip
echo ==================================================
echo [STEP 3] Upgrading pip...
echo ==================================================
python -m pip install --upgrade pip >nul
echo ✅ Pip upgraded.
echo.

:: Step 4: Install required Python packages from requirements.txt
echo ==================================================
echo [STEP 4] Installing Python Dependencies from requirements.txt...
echo ==================================================
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
  echo ❌ Failed to install Python dependencies from requirements.txt.
  echo.
  echo Please check the error messages above for details.
  pause
  exit /b
)
echo ✅ All Python dependencies installed.
echo.

:: Step 5: Validate configurations
echo ==================================================
echo [STEP 5] Validating Configurations...
echo ==================================================
python helpers\validate_config.py
IF %ERRORLEVEL% NEQ 0 (
  echo ❌ Configuration validation failed.
  echo.
  echo Please check the error messages above for details and fix your .env or proj_config.json.
  pause
  exit /b
)
echo ✅ All configurations validated successfully!
echo.
:: Step 6: Run the Telegram Channel Forwarder Bot
echo ==================================================
echo [STEP 6] Running Telegram Channel Forwarder Bot...
echo ==================================================
:: Output from the bot will be redirected to bot_log.txt as configured in the Python script.
:: This command will run the script, and the batch file will wait for it to finish.
python telegram_channel_forwarder.py
IF %ERRORLEVEL% NEQ 0 (
  echo ❌ Bot exited with errors. Check bot_log.txt for details.
  echo.
  pause
  exit /b
)
echo ✅ Operation finished or bot exited gracefully.
echo.
pause