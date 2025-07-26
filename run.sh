#!/bin/bash
bash rotate_logs.sh
# Define log file paths
LOG_DIR="logs"
BOT_LOG_FILE="$LOG_DIR/bot_log.txt"
START_LOG_FILE="$LOG_DIR/start_log.txt"

# Ensure logs directory exists
mkdir -p "$LOG_DIR"

# Log when the bot is triggered
echo "Triggered at $(date)" >> "$START_LOG_FILE"

# Run the Telegram bot and capture all output into the bot log
python3 telegram_channel_forwarder.py >> "$BOT_LOG_FILE" 2>&1
