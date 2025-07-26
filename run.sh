#!/bin/bash
bash rotate_logs.sh
# Define log file paths
LOG_DIR="logs"
BOT_LOG_FILE="$LOG_DIR/bot_log.txt"
START_LOG_FILE="$LOG_DIR/start_log.txt"

# Ensure logs directory exists
mkdir -p "$LOG_DIR"

# Log when the Replit container starts up via run.sh
echo "Replit container starting up via run.sh at $(date)" >> "$START_LOG_FILE"

# Run the Flask application
# The Flask app will then manage the bot's lifecycle
python3 app.py >> "$START_LOG_FILE" 2>&1