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

:: Step 4: Install required Python packages (Telethon only):: Step 4: Install required Python packages (Telethon and python-dotenv only)
echo ==================================================
echo [STEP 4] Installing Python Dependencies (Telethon and python-dotenv only)...
echo ==================================================

:: Check and install telethon
python -c "import telethon" >nul 2>&1 || (
  echo 📦 Installing Telethon...
  pip install telethon
)

:: Check and install python-dotenv
python -c "import dotenv" >nul 2>&1 || (
  echo 📦 Installing python-dotenv...
  pip install python-dotenv
)

echo ✅ Python dependencies checked.
echo.