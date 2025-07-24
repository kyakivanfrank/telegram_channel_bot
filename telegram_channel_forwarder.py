import logging
import json
import os
import sys
import asyncio
from datetime import datetime, time, timedelta
import pytz  # Import pytz for timezone handling
from dotenv import load_dotenv  # Import load_dotenv

# --- CRITICAL PATH FIX FOR REPLIT ---
# Explicitly add Replit's site-packages directory to sys.path
# This ensures Python can find installed libraries like Telethon.
replit_site_packages_path = (
    "/home/runner/workspace/.pythonlibs/lib/python3.12/site-packages"
)
if replit_site_packages_path not in sys.path:
    sys.path.insert(0, replit_site_packages_path)
# --- END CRITICAL PATH FIX ---


# --- DIAGNOSTIC PRINT ---
# Print sys.path at the very beginning to see where Python is looking for modules
logger = logging.getLogger(__name__)  # Initialize logger early for this diagnostic
logger.debug(f"sys.path at script start (after path fix): {sys.path}")
# --- END DIAGNOSTIC PRINT ---


# Load environment variables from .env file at the very beginning
# This is primarily for local development. Replit Secrets handle this online.
load_dotenv()

# Configure logging to output ALL messages (DEBUG level) for debugging
# Also, ensure it prints to console
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.DEBUG,  # Changed to DEBUG for more verbose output
    handlers=[logging.StreamHandler(sys.stdout)],  # Ensure output goes to console
)
# logger is already initialized above

# Define the timezone for Uganda (UTC+3)
UGANDA_TIMEZONE = pytz.timezone(
    "Africa/Nairobi"
)  # Nairobi is UTC+3, common for East Africa
ACTIVE_START_HOUR = 8  # 8:00 AM UTC+3
ACTIVE_END_HOUR = 21  # 9:00 PM (21:00) UTC+3
OPERATION_DURATION_HOURS = (
    13  # The maximum duration the bot should run if started at 8 AM
)

# Global client variable
client = None

# --- Configuration Loading ---
# Load non-sensitive configurations from proj_config.json
CONFIG = {}
try:
    # Use a more direct path for Replit's root directory
    # Replit's workspace root is usually '/home/runner/workspace/'
    replit_root_dir = "/home/runner/workspace/"

    config_path = os.path.join(replit_root_dir, "proj_config.json")

    logger.debug(f"Attempting to load config from: {config_path}")

    with open(config_path, "r") as f:
        CONFIG = json.load(f)
    logger.info("Configuration loaded from proj_config.json.")
except FileNotFoundError:
    logger.critical(
        f"FATAL ERROR: proj_config.json not found at {config_path}. Please ensure it's in the root directory of your Replit project."
    )
    sys.exit(1)
except json.JSONDecodeError:
    logger.critical(
        "FATAL ERROR: Error decoding proj_config.json. Please check the JSON format for syntax errors."
    )
    sys.exit(1)
except KeyError as e:
    logger.critical(
        f"FATAL ERROR: Missing a required key in proj_config.json: {e}. Please check your configuration."
    )
    sys.exit(1)
except Exception as e:
    logger.critical(
        f"FATAL ERROR: An unexpected error occurred during configuration loading: {e}",
        exc_info=True,
    )
    sys.exit(1)


# Load sensitive configurations from environment variables
API_ID = os.getenv("TELETHON_API_ID")
API_HASH = os.getenv("TELETHON_API_HASH")
PHONE_NUMBER = os.getenv("TELETHON_PHONE_NUMBER")
TARGET_CHANNEL_USERNAME = os.getenv(
    "TELETHON_TARGET_CHANNEL"
)  # New env variable for target channel

# Load source channels from proj_config.json
SOURCE_CHANNEL_USERNAMES = CONFIG.get("source_channels", [])


# Validate essential configurations (both env vars and from config file)
if not all([API_ID, API_HASH, PHONE_NUMBER, TARGET_CHANNEL_USERNAME]):
    logger.critical(
        "FATAL ERROR: Critical Telethon configurations (TELETHON_API_ID, TELETHON_API_HASH, TELETHON_PHONE_NUMBER, TELETHON_TARGET_CHANNEL) are missing or empty in environment variables. Please set them securely in Replit Secrets."
    )
    sys.exit(1)

# Ensure source_channels is a non-empty list from proj_config.json
if not isinstance(SOURCE_CHANNEL_USERNAMES, list) or not SOURCE_CHANNEL_USERNAMES:
    logger.critical(
        'FATAL ERROR: \'source_channels\' in proj_config.json must be a non-empty list of channel usernames (e.g., ["@channel1", "@channel2"]).'
    )
    sys.exit(1)

# Convert API_ID to integer
try:
    API_ID = int(API_ID)
except ValueError:
    logger.critical(
        "FATAL ERROR: TELETHON_API_ID environment variable must be an integer."
    )
    sys.exit(1)


# Initialize Telethon client (global)
# Use a direct path for the sessions folder within Replit's root
session_file_path = os.path.join(replit_root_dir, "sessions", "telethon_session")
from telethon import TelegramClient, events  # Moved import here for diagnostic purposes
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
)  # Moved import here for diagnostic purposes
from telethon.errors import (
    SessionPasswordNeededError,
    FloodWaitError,
    AuthKeyUnregisteredError,
    ChannelPrivateError,
    UserNotParticipantError,
)  # Moved import here for diagnostic purposes

client = TelegramClient(session_file_path, API_ID, API_HASH)
logger.debug(f"Telethon client initialized with session file: {session_file_path}")


async def main():
    logger.info("Starting Telethon client...")

    current_uganda_time = datetime.now(UGANDA_TIMEZONE)
    logger.info(
        f"Current Uganda time: {current_uganda_time.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"
    )

    # Check if current time is within active hours
    if not (ACTIVE_START_HOUR <= current_uganda_time.hour < ACTIVE_END_HOUR):
        logger.info(
            f"Current time {current_uganda_time.strftime('%H:%M')} is outside active hours ({ACTIVE_START_HOUR}:00-{ACTIVE_END_HOUR}:00 UTC+3). Exiting gracefully."
        )
        sys.exit(0)  # Exit if not in active window

    try:
        await client.start(phone=PHONE_NUMBER)
        logger.info("Telethon client connected successfully!")
    except SessionPasswordNeededError:
        logger.critical(
            "FATAL ERROR: Two-factor authentication (2FA) is enabled for your account. Please run the script manually once to log in and enter your 2FA password."
        )
        logger.critical(
            f"Example: python -m telethon.sync --session {session_file_path} --phone {PHONE_NUMBER}"
        )  # Suggest manual login with session path
        sys.exit(1)
    except FloodWaitError as e:
        logger.critical(
            f"FATAL ERROR: Telethon is being rate-limited by Telegram. Please wait {e.seconds} seconds before trying again. This usually happens due to too many login attempts or requests."
        )
        sys.exit(1)
    except AuthKeyUnregisteredError:
        logger.critical(
            "FATAL ERROR: Your authorization key is invalid. This usually means you need to log in again. Delete 'telethon_session.session' and restart the script."
        )
        sys.exit(1)
    except Exception as e:
        logger.critical(
            f"FATAL ERROR: An unexpected error occurred during Telethon client connection: {e}",
            exc_info=True,
        )
        sys.exit(1)

    # Resolve target channel entity
    target_channel_entity = None
    try:
        target_channel_entity = await client.get_entity(TARGET_CHANNEL_USERNAME)
        logger.info(
            f"Target channel resolved: {target_channel_entity.title} ({TARGET_CHANNEL_USERNAME})"
        )
    except Exception as e:
        logger.critical(
            f"FATAL ERROR: Could not resolve target channel '{TARGET_CHANNEL_USERNAME}'. Please check the username/ID and ensure your account can access it: {e}"
        )
        sys.exit(1)

    # Resolve source channel entities
    source_channel_entities = []
    for source_username in SOURCE_CHANNEL_USERNAMES:
        try:
            entity = await client.get_entity(source_username)
            source_channel_entities.append(entity)
            logger.info(f"Source channel resolved: {entity.title} ({source_username})")
        except ChannelPrivateError:
            logger.error(
                f"ERROR: Source channel '{source_username}' is private. Your account must be a member of private channels to access them. Skipping."
            )
        except UserNotParticipantError:
            logger.error(
                f"ERROR: Your account is not a participant in channel '{source_username}'. Please join it first. Skipping."
            )
        except Exception as e:
            logger.error(
                f"ERROR: Could not resolve source channel '{source_username}'. Skipping this channel. Error: {e}"
            )
            continue

    if not source_channel_entities:
        logger.critical(
            "FATAL ERROR: No valid source channels could be resolved. Please ensure your source_channels list in proj_config.json contains valid, accessible channels. Exiting."
        )
        sys.exit(1)

    @client.on(events.NewMessage(chats=source_channel_entities))
    async def handler(event):
        # Only forward messages that are not from the bot itself or other forwarded messages
        # and are not commands or service messages.
        # Check event.message.message for text content, or event.message.media for media.
        if (
            (event.message.text or event.message.media)
            and not event.message.via_bot_id
            and not event.message.fwd_from
        ):
            logger.info(
                f"New message from {event.chat.title}: {event.message.text[:50] if event.message.text else 'Media Message'}..."
            )

            # Forward text messages
            if event.message.text:
                try:
                    await client.send_message(target_channel_entity, event.message.text)
                    logger.info(
                        f"Forwarded text message from {event.chat.title} to {target_channel_entity.title}."
                    )
                except Exception as e:
                    logger.error(
                        f"Error forwarding text message from {event.chat.title}: {e}"
                    )

            # Forward media (photos and documents)
            if event.message.media:
                try:
                    if isinstance(event.message.media, MessageMediaPhoto):
                        await client.send_file(
                            target_channel_entity,
                            event.message.media,
                            caption=event.message.message,
                        )
                        logger.info(
                            f"Forwarded photo from {event.chat.title} to {target_channel_entity.title}."
                        )
                    elif isinstance(event.message.media, MessageMediaDocument):
                        await client.send_file(
                            target_channel_entity,
                            event.message.media,
                            caption=event.message.message,
                        )
                        logger.info(
                            f"Forwarded document from {event.chat.title} to {target_channel_entity.title}."
                        )
                    else:
                        logger.warning(
                            f"Unsupported media type from {event.chat.title}: {type(event.message.media)}. Message: {event.message.text[:50] if event.message.text else 'No text'}"
                        )
                except Exception as e:
                    logger.error(f"Error forwarding media from {event.chat.title}: {e}")
        elif event.message.fwd_from:
            logger.debug(f"Ignored forwarded message from {event.chat.title}.")
        else:
            logger.debug(
                f"Ignored non-text/non-media message (e.g., service message, command) from {event.chat.title}."
            )

    logger.info(
        f"Telethon client running. Listening for new messages for up to {OPERATION_DURATION_HOURS} hours..."
    )

    # Calculate the exact end time
    end_time = current_uganda_time + timedelta(hours=OPERATION_DURATION_HOURS)
    logger.info(f"Scheduled end time (UTC+3): {end_time.strftime('%H:%M:%S')}")

    try:
        # Run until disconnected or timeout
        await asyncio.wait_for(
            client.run_until_disconnected(),
            timeout=(end_time - current_uganda_time).total_seconds(),
        )
    except asyncio.TimeoutError:
        logger.info(
            f"Operation duration of {OPERATION_DURATION_HOURS} hours reached. Disconnecting client."
        )
    except Exception as e:
        logger.error(
            f"An error occurred while listening for messages: {e}", exc_info=True
        )
    finally:
        if client and client.is_connected():
            logger.info("Disconnecting Telethon client.")
            await client.disconnect()
        logger.info("Telethon client disconnected. Script exiting.")
        sys.exit(0)  # Explicitly exit after operation duration or error


if __name__ == "__main__":
    try:
        # Create the sessions directory if it doesn't exist
        # Use a direct path for the sessions folder within Replit's root
        sessions_dir = os.path.join(replit_root_dir, "sessions")
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir)
            logger.info(f"Created sessions directory: {sessions_dir}")

        asyncio.run(main())  # Run the main function
    except Exception as e:
        logger.critical(
            f"CRITICAL APPLICATION ERROR: Telethon bot encountered an unhandled exception during startup or main execution: {e}",
            exc_info=True,
        )
    finally:
        # Ensure client is disconnected even if main() exits via sys.exit(0)
        # This block might not always execute if sys.exit is called earlier,
        # but it's good practice for general cleanup.
        if client and client.is_connected():
            logger.info("Final cleanup: Disconnecting client.")
            client.disconnect()
        logger.info("Application exiting.")
