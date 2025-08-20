#!/bin/bash
# Removed call to rotate_logs.sh as file logging is removed

# Removed LOG_DIR, BOT_LOG_FILE, START_LOG_FILE definitions
# Removed mkdir -p "$LOG_DIR"

# Run the Telegram bots directly in the background
python3 frank_bot/telegram_channel_forwarder.py &
python3 raymond_bot/telegram_channel_forwarder.py &

# Wait for all background jobs to finish (optional, but good practice)
wait