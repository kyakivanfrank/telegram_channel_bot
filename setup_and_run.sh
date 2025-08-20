#!/bin/bash

# --- Script for automated setup and running of the Telegram Channel Forwarder Bot on Linux ---
# This script performs:
# 1. Checks for Python 3 installation.
# 2. Installs 'python3-venv' (essential for virtual environments).
# 3. Installs 'screen' (for persistent execution) if not present.
# 4. Creates and activates a Python virtual environment.
# 5. Installs all Python dependencies from requirements.txt.
# 6. Runs the configuration validation script (helpers/validate_config.py).
# 7. Starts the Telegram bot (telegram_channel_forwarder.py) within a 'screen' session for persistent execution.

# Exit immediately if a command exits with a non-zero status.
set -e

echo "=================================================="
echo "[STEP 0] Checking Python Installation and Essential Tools..."
echo "=================================================="

# Check for Python 3
if ! command -v python3 &> /dev/null
then
    echo "ERROR: Python 3 is not installed. Please install Python 3.x."
    echo "For Ubuntu/Debian: sudo apt install python3 python3-pip -y"
    echo "For Amazon Linux/CentOS: sudo yum install python3 python3-pip -y"
    exit 1
fi
echo "SUCCESS: Python 3 is installed."

# Install python3-venv (crucial for creating virtual environments on modern Ubuntu)
echo "Installing python3-venv..."
if command -v apt &> /dev/null; then
    sudo apt update # Ensure package lists are up to date before installing
    sudo apt install python3-venv -y
elif command -v yum &> /dev/null; then
    sudo yum install python3-venv -y
else
    echo "Warning: Could not determine package manager to install 'python3-venv'. Please install it manually."
    # We will still try to proceed, but venv creation might fail later.
fi
echo "SUCCESS: python3-venv check/installation complete."
echo ""

# Optional: Install screen for persistent execution if not already installed
echo "=================================================="
echo "[STEP 0.5] Checking and Installing 'screen' (for persistent sessions)..."
echo "=================================================="
if ! command -v screen &> /dev/null
then
    echo "Installing 'screen'..."
    # Detect package manager and install screen
    if command -v apt &> /dev/null; then
        sudo apt update && sudo apt install screen -y
    elif command -v yum &> /dev/null; then
        sudo yum install screen -y
    else
        echo "Warning: Could not determine package manager to install 'screen'. Please install it manually."
    fi
else
    echo "'screen' is already installed."
fi
echo "SUCCESS: 'screen' check/installation complete."
echo ""

echo "=================================================="
echo "[STEP 1] Setting Up Virtual Environment and Installing Python Dependencies..."
echo "=================================================="

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment 'venv'..."
    python3 -m venv venv
else
    echo "Virtual environment 'venv' already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if requirements.txt exists
if [ ! -f "requirements.txt" ]; then
    echo "ERROR: requirements.txt not found. Cannot install dependencies."
    deactivate # Deactivate venv before exiting
    exit 1
fi

# Install all dependencies listed in requirements.txt
echo "Installing Python dependencies from requirements.txt..."
# This pip command will use the pip inside the activated virtual environment
pip install -r requirements.txt
if [ $? -ne 0 ]; then # Check the exit status of the last command
    echo "ERROR: Failed to install Python dependencies."
    echo "Please check the error messages above and ensure you have a working internet connection."
    deactivate # Deactivate venv before exiting
    exit 1
fi

echo "SUCCESS: All dependencies checked/installed."
echo ""

echo "=================================================="
echo "[STEP 2] Validating Configurations..."
echo "=================================================="

# Run the configuration validation script
python3 frank_bot/helpers/validate_config.py
if [ $? -ne 0 ]; then
    echo "ERROR: Frank bot configuration validation failed."
    echo "Please check the error messages above for details and fix your .env or proj_config.json."
    deactivate # Deactivate venv before exiting
    exit 1
fi

python3 raymond_bot/helpers/validate_config.py
if [ $? -ne 0 ]; then
    echo "ERROR: Raymond bot configuration validation failed."
    echo "Please check the error messages above for details and fix your .env or proj_config.json."
    deactivate # Deactivate venv before exiting
    exit 1
fi
echo "SUCCESS: All configurations validated successfully!"
echo ""

echo "=================================================="
echo "[STEP 3] Running Telegram Channel Forwarder Bot..."
echo "=================================================="

# Start each bot in its own unique screen session
echo "Starting Frank bot in a new 'screen' session named 'frank_bot'."
screen -dmS frank_bot bash -c "source venv/bin/activate && python3 frank_bot/telegram_channel_forwarder.py"

echo "Starting Raymond bot in a new 'screen' session named 'raymond_bot'."
screen -dmS raymond_bot bash -c "source venv/bin/activate && python3 raymond_bot/telegram_channel_forwarder.py"

echo "Bots started in 'screen' sessions. To re-attach to Frank bot, run: screen -r frank_bot"
echo "To re-attach to Raymond bot, run: screen -r raymond_bot"
echo "To list all screen sessions, run: screen -ls"
echo "To detach, press Ctrl+A then D."
echo "To stop a bot, re-attach to its session and press Ctrl+C."

echo "Setup and run process complete."