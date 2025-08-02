#!/bin/bash
# Removed call to rotate_logs.sh as file logging is removed

# Removed LOG_DIR, BOT_LOG_FILE, START_LOG_FILE definitions
# Removed mkdir -p "$LOG_DIR"

# Run the Telegram bot directly
python3 telegram_channel_forwarder.py
