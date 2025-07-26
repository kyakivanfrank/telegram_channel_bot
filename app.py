# app.py
import os
import sys
import threading
import asyncio
from datetime import datetime
import pytz
import logging
from flask import Flask, render_template, request, jsonify

# Add the project root to sys.path for proper imports
# This is crucial for Flask to find helpers and telegram_channel_forwarder
replit_root_dir = os.getcwd()
if replit_root_dir not in sys.path:
    sys.path.insert(0, replit_root_dir)

# Import components from your existing bot script
# We'll import specific parts to control execution
try:
    from telegram_channel_forwarder import (
        main as run_telegram_bot,  # Rename main to avoid conflict and be explicit
        client,
        logger,
        UGANDA_TIMEZONE_STR,
        ACTIVE_START_HOUR,
        ACTIVE_END_HOUR,
        BOT_TITLE,
        BOT_LOG_FILE_PATH,  # Import the path for log display
    )
except ImportError as e:
    print(
        f"FATAL: Could not import bot components from telegram_channel_forwarder.py: {e}",
        file=sys.stderr,
    )
    sys.exit(1)

# Ensure logging is set up for app.py if it's not already
# It's good practice to have Flask logging to console/Replit output
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
app_logger = logging.getLogger(__name__)

app = Flask(__name__)

# This will hold the bot's running thread
bot_thread: threading.Thread = None
bot_running_flag = False


def run_bot_in_thread():
    """
    Function to run the asynchronous Telegram bot in a separate thread.
    This allows the Flask server to remain responsive.
    """
    global bot_running_flag
    app_logger.info("Attempting to run Telegram bot asynchronously...")
    bot_running_flag = True
    try:
        # Check active hours here before running the bot
        current_uganda_time = datetime.now(pytz.timezone(UGANDA_TIMEZONE_STR)).time()
        if not (ACTIVE_START_HOUR <= current_uganda_time.hour < ACTIVE_END_HOUR):
            message = f"{BOT_TITLE} not started: current time {current_uganda_time.strftime('%H:%M')} is outside active hours ({ACTIVE_START_HOUR}:00 - {ACTIVE_END_HOUR}:00)."
            app_logger.info(message)
            # You might want to send a notification here too, but need an active client
            # If client is already connected from a previous run or manual login, send notification
            # if client and client.is_connected():
            #     asyncio.run(notify_telegram(client, message))
            return

        asyncio.run(run_telegram_bot())  # Call the renamed main function
        app_logger.info("Telegram bot execution completed.")
    except Exception as e:
        app_logger.critical(f"Error running Telegram bot in thread: {e}", exc_info=True)
    finally:
        bot_running_flag = False
        app_logger.info("Bot thread finished. Ensuring client is disconnected.")
        if client and client.is_connected():
            asyncio.run(client.disconnect())  # Ensure disconnection after bot finishes


@app.route("/")
def index():
    """Serves the static index.html file."""
    return render_template("index.html")


@app.route("/trigger-bot", methods=["GET", "POST"])
def trigger_bot():
    """
    Endpoint to trigger the bot.
    It will start the bot in a new thread if it's not already running.
    """
    global bot_thread, bot_running_flag

    if bot_running_flag and bot_thread and bot_thread.is_alive():
        app_logger.info("Trigger request received, but bot is already running.")
        return jsonify({"status": "info", "message": "Bot is already running."}), 200
    else:
        # Clean up old thread reference if it's no longer alive
        if bot_thread and not bot_thread.is_alive():
            app_logger.info(
                "Old bot thread found, but it's no longer alive. Starting a new one."
            )
            bot_thread = None

        app_logger.info("Trigger request received. Attempting to start bot thread.")
        bot_thread = threading.Thread(target=run_bot_in_thread)
        bot_thread.daemon = (
            True  # Allow the main program to exit even if the thread is running
        )
        bot_thread.start()
        return (
            jsonify(
                {"status": "success", "message": "Bot started/restarted successfully!"}
            ),
            200,
        )


@app.route("/bot-status")
def bot_status():
    """Provides the current status of the bot."""
    global bot_running_flag
    status_message = (
        "Running"
        if bot_running_flag and bot_thread and bot_thread.is_alive()
        else "Stopped"
    )
    return jsonify({"status": status_message, "is_running": bot_running_flag})


@app.route("/get-logs")
def get_logs():
    """Serves the bot's log file."""
    try:
        if os.path.exists(BOT_LOG_FILE_PATH):
            with open(BOT_LOG_FILE_PATH, "r", encoding="utf-8") as f:
                logs = f.read()
            return (
                "<pre>" + logs + "</pre>",
                200,
                {"Content-Type": "text/html; charset=utf-8"},
            )
        else:
            return "Bot log file not found.", 404
    except Exception as e:
        app_logger.error(f"Error reading bot logs: {e}")
        return f"Error reading logs: {e}", 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))  # Use Replit's default PORT env var
    app_logger.info(f"Flask app starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)  # debug=True only for local dev
