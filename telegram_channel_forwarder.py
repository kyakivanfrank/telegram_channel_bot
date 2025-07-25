import logging
import json
import os
import sys
import asyncio
from datetime import datetime, time, timedelta
import pytz
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import (
    UserAlreadyParticipantError,
    InviteHashExpiredError,
    ChatIdInvalidError,
    ChannelPrivateError,
    UserNotParticipantError,
    AuthKeyError,  # Added for more specific auth error handling
    SessionPasswordNeededError,  # Added for 2FA handling
    RPCError,  # General Telethon RPC error
)

# --- CRITICAL PATH FIX FOR REPLIT ---
# Define Replit's root directory dynamically based on current working directory.
# This makes the script portable to both local environments and Replit.
replit_root_dir = os.getcwd()

# Explicitly add Replit's site-packages directory to sys.path if it exists.
# This ensures Python can find installed libraries like Telethon in Replit's specific setup.
replit_site_packages_path = os.path.join(
    replit_root_dir, ".pythonlibs", "lib", "python3.12", "site-packages"
)
if (
    os.path.exists(replit_site_packages_path)
    and replit_site_packages_path not in sys.path
):
    sys.path.insert(0, replit_site_packages_path)
# --- END CRITICAL PATH FIX ---

# --- LOG FILE REDIRECTION ---
# Define log file path relative to the dynamic root directory
LOG_FILE_PATH = os.path.join(replit_root_dir, "bot_log.txt")

# Create log directory if it doesn't exist (harmless if it already does)
log_dir = os.path.dirname(LOG_FILE_PATH)
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Redirect stdout and stderr to the log file
# This prevents excessive output being sent back to the cron job,
# which causes "output too large" errors.
# 'a' for append, buffering=1 for line-buffering
sys.stdout = open(LOG_FILE_PATH, "a", buffering=1, encoding="utf-8")
sys.stderr = sys.stdout  # Redirect stderr to the same log file

# --- DIAGNOSTIC PRINT (will now go to log file) ---
print(
    f"[{datetime.now().isoformat()}] Script started. Logs redirected to {LOG_FILE_PATH}"
)

# --- Initialize Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],  # Direct logs to the redirected stdout
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# --- Configuration Loading from proj_config.json ---
CONFIG_PATH = os.path.join(replit_root_dir, "proj_config.json")
CONFIG = {}
try:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            CONFIG = json.load(f)
        logger.info(f"Configuration loaded from {CONFIG_PATH}.")
    else:
        logger.warning(f"Warning: {CONFIG_PATH} not found. Using default/empty config.")
except json.JSONDecodeError:
    logger.critical(
        f"FATAL ERROR: Could not parse {CONFIG_PATH}. It might be malformed JSON. Exiting."
    )
    sys.exit(1)
except Exception as e:
    logger.critical(
        f"FATAL ERROR: An unexpected error occurred while loading {CONFIG_PATH}: {e}. Exiting.",
        exc_info=True,
    )
    sys.exit(1)

# --- General Bot Settings from CONFIG ---
BOT_TITLE = CONFIG.get("title", "Telegram Channel Forwarder Bot")
BOT_SHORTNAME = CONFIG.get("shortname", "ForwarderBot")
UGANDA_TIMEZONE_STR = CONFIG.get("timezone", "Africa/Kampala")
ACTIVE_START_HOUR = CONFIG.get("active_start_hour", 6)  # Default 6 AM
ACTIVE_END_HOUR = CONFIG.get("active_end_hour", 20)  # Default 8 PM (20:00)
OPERATION_DURATION_HOURS = CONFIG.get(
    "operation_duration_hours", 23
)  # Default 23 hours

# --- Telethon API Credentials from Environment Variables ---
API_ID = os.getenv("TELETHON_API_ID")
API_HASH = os.getenv("TELETHON_API_HASH")
PHONE_NUMBER = os.getenv("TELETHON_PHONE_NUMBER")

if not all([API_ID, API_HASH, PHONE_NUMBER]):
    logger.critical(
        "FATAL ERROR: TELETHON_API_ID, TELETHON_API_HASH, or TELETHON_PHONE_NUMBER not found in .env. Exiting."
    )
    sys.exit(1)

try:
    API_ID = int(API_ID)
except ValueError:
    logger.critical("FATAL ERROR: TELETHON_API_ID must be an integer. Exiting.")
    sys.exit(1)


# --- NEW: Helper function for parsing and validating channel config strings ---
def _parse_channel_env_var(env_var_name):
    """
    Parses a JSON string from an environment variable for channel configuration,
    and performs basic validation.
    """
    channel_config_str = os.getenv(env_var_name)
    if not channel_config_str:
        logger.critical(
            f"FATAL ERROR: Environment variable '{env_var_name}' is missing or empty in .env. Exiting."
        )
        sys.exit(1)

    try:
        channel_data = json.loads(channel_config_str)
    except json.JSONDecodeError:
        logger.critical(
            f"FATAL ERROR: '{env_var_name}' is not a valid JSON string: '{channel_config_str}'. Please check your .env format. Exiting."
        )
        sys.exit(1)
    except Exception as e:
        logger.critical(
            f"FATAL ERROR: An unexpected error occurred parsing '{env_var_name}': {e}. Exiting.",
            exc_info=True,
        )
        sys.exit(1)

    # Convert simple string (if allowed by json.loads, which it won't be if it's not quoted)
    # This block is mainly for robustness, though current usage expects JSON object.
    if isinstance(channel_data, str):
        channel_data = {"username": channel_data, "title": channel_data}

    # Basic validation for required fields
    identifier_present = channel_data.get("username") or channel_data.get("id")
    if not identifier_present:
        logger.critical(
            f"FATAL ERROR: '{env_var_name}' JSON is missing 'username' or 'id'. Please provide at least one. Exiting."
        )
        sys.exit(1)

    # Ensure title is present for logging clarity
    if not channel_data.get("title"):
        channel_data["title"] = channel_data.get("username") or str(
            channel_data.get("id")
        )
        logger.warning(
            f"Warning: '{env_var_name}' JSON is missing 'title'. Using '{channel_data['title']}' for logging."
        )

    # Validate private channel specifics
    if channel_data.get("type") == "private":
        if not channel_data.get("invite_hash") and not channel_data.get("id"):
            logger.critical(
                f"FATAL ERROR: Private channel '{env_var_name}' is missing 'invite_hash' or 'id'. For private channels, either an 'invite_hash' (to join) or an 'id' (if already a member) is required. Exiting."
            )
            sys.exit(1)

    return channel_data


# --- Use the new helper function for configuration loading ---
try:
    TARGET_CHANNEL_CONFIG = _parse_channel_env_var("TELETHON_TARGET_CHANNEL_CONFIG")
    logger.info(
        f"Target channel config loaded: {TARGET_CHANNEL_CONFIG.get('title', 'N/A')}"
    )
except SystemExit:  # Catch SystemExit if _parse_channel_env_var already exited
    raise  # Re-raise to ensure the script truly exits

SOURCE_CHANNEL_CONFIGS = []
for i in range(1, 100):  # Assuming max 99 source channels (can adjust)
    env_var_name = f"TELETHON_SOURCE_CHANNEL_{i}"
    source_channel_str = os.getenv(env_var_name)
    if (
        source_channel_str is None
    ):  # None means the env var doesn't exist, so no more sources
        break

    try:
        # Use the helper function; it will handle critical errors and sys.exit(1) if parsing fails
        source_config = _parse_channel_env_var(env_var_name)
        SOURCE_CHANNEL_CONFIGS.append(source_config)
        logger.info(
            f"Source channel '{env_var_name}' config loaded: {source_config.get('title', 'N/A')}"
        )
    except (
        SystemExit
    ):  # Catch SystemExit raised by _parse_channel_env_var for a specific source
        # If a specific source channel config is malformed, _parse_channel_env_var will exit the script.
        # This try-except is mainly for clarity that the loop won't continue if a previous source caused an exit.
        raise  # Re-raise to ensure the script exits
    except Exception as e:
        logger.error(
            f"ERROR: An unexpected issue occurred while processing '{env_var_name}': {e}. Skipping this channel.",
            exc_info=True,
        )
        continue  # Continue to next source if there's a non-fatal parsing error

if not SOURCE_CHANNEL_CONFIGS:
    logger.critical(
        "FATAL ERROR: No valid source channel configurations found in .env (e.g., TELETHON_SOURCE_CHANNEL_1). At least one source channel is required. Exiting."
    )
    sys.exit(1)

# Initialize client outside main to make it accessible for cleanup in finally block
# Use a direct path for the sessions folder within the resolved root
session_file_path = os.path.join(replit_root_dir, "sessions", "telethon_session")
client = TelegramClient(session_file_path, API_ID, API_HASH)


# --- Main Bot Logic ---
async def main():
    logger.info("Starting Telethon client...")
    try:
        await client.start(phone=PHONE_NUMBER)
        logger.info("Telethon client started successfully.")
    except SessionPasswordNeededError:
        logger.critical(
            "FATAL ERROR: Two-factor authentication (2FA) is enabled for your account. Please run the script manually once to log in and enter your 2FA password. The script will then save the session, and subsequent runs should work automatically. Exiting."
        )
        sys.exit(1)
    except AuthKeyError as e:
        logger.critical(
            f"FATAL ERROR: Authentication failed. Please check your API ID, API Hash, and Phone Number in .env. If you recently revoked your session, you might need to delete the 'sessions' folder and try again. Error: {e}. Exiting.",
            exc_info=True,
        )
        sys.exit(1)
    except RPCError as e:
        logger.critical(
            f"FATAL ERROR: A Telegram RPC error occurred during client startup: {e}. Exiting.",
            exc_info=True,
        )
        sys.exit(1)
    except Exception as e:
        logger.critical(
            f"FATAL ERROR: An unexpected error occurred during client startup: {e}. Exiting.",
            exc_info=True,
        )
        sys.exit(1)

    if not await client.is_user_authorized():
        logger.critical(
            "FATAL ERROR: Telethon client is not authorized. Please run the script manually once to complete the login process (enter phone number, code, and 2FA if applicable). Exiting."
        )
        sys.exit(1)

    # --- Resolve Target Channel ---
    target_channel_entity = None
    target_identifier = TARGET_CHANNEL_CONFIG.get("id") or TARGET_CHANNEL_CONFIG.get(
        "username"
    )
    target_channel_name_for_logs = TARGET_CHANNEL_CONFIG.get("title", target_identifier)

    logger.info(
        f"Attempting to resolve target channel '{target_channel_name_for_logs}' (ID/Username: {target_identifier})..."
    )

    # Handle private target channel joining if an invite hash is provided
    if TARGET_CHANNEL_CONFIG.get("type") == "private" and TARGET_CHANNEL_CONFIG.get(
        "invite_hash"
    ):
        invite_hash = TARGET_CHANNEL_CONFIG["invite_hash"]
        logger.info(
            f"Attempting to ensure membership in target private channel '{target_channel_name_for_logs}' using invite hash..."
        )
        try:
            await client(ImportChatInviteRequest(invite_hash))
            logger.info(
                f"Successfully joined or already a member of target channel '{target_channel_name_for_logs}'."
            )
        except UserAlreadyParticipantError:
            logger.info(
                f"Telethon account is already a participant in target channel '{target_channel_name_for_logs}'."
            )
        except InviteHashExpiredError:
            logger.critical(
                f"FATAL ERROR: The invite hash '{invite_hash}' for target channel '{target_channel_name_for_logs}' has expired or is invalid. Exiting."
            )
            sys.exit(1)
        except ChatIdInvalidError:
            logger.critical(
                f"FATAL ERROR: The invite hash '{invite_hash}' for target channel '{target_channel_name_for_logs}' corresponds to an invalid chat ID. Exiting."
            )
            sys.exit(1)
        except Exception as e:
            logger.critical(
                f"FATAL ERROR: An unexpected error occurred while attempting to join target channel '{target_channel_name_for_logs}' with invite hash '{invite_hash}': {e}. Exiting.",
                exc_info=True,
            )
            sys.exit(1)
    elif (
        TARGET_CHANNEL_CONFIG.get("type") == "private"
        and not TARGET_CHANNEL_CONFIG.get("invite_hash")
        and TARGET_CHANNEL_CONFIG.get("id")
    ):
        logger.info(
            f"Target private channel '{target_channel_name_for_logs}' configured with ID only. Assuming account is already a member. Proceeding to get entity."
        )
    else:
        logger.info(
            f"Target channel '{target_channel_name_for_logs}' is configured as public or has no specific type/invite hash. Proceeding to get entity."
        )

    try:
        target_channel_entity = await client.get_entity(target_identifier)
        logger.info(
            f"Target channel resolved: {target_channel_entity.title} ({target_identifier})"
        )
    except ChannelPrivateError:
        logger.critical(
            f"FATAL ERROR: Target channel '{target_channel_name_for_logs}' (ID: {target_identifier}) is private and could not be accessed. Your account must be a member or the invite_hash was incorrect (if applicable). Exiting."
        )
        sys.exit(1)
    except UserNotParticipantError:
        logger.critical(
            f"FATAL ERROR: Your account is not a participant in target channel '{target_channel_name_for_logs}' (ID: {target_identifier}). Please join it first or provide a valid invite_hash if it's private. Exiting."
        )
        sys.exit(1)
    except Exception as e:
        logger.critical(
            f"FATAL ERROR: Could not resolve target channel '{target_channel_name_for_logs}' (ID: {target_identifier}). Please check the username/ID and ensure your account can access it: {e}",
            exc_info=True,
        )
        sys.exit(1)

    # --- Resolve Source Channels ---
    source_channel_entities = []
    for source_config in SOURCE_CHANNEL_CONFIGS:
        source_identifier = source_config.get("id") or source_config.get("username")
        source_channel_name_for_logs = source_config.get("title", source_identifier)

        logger.info(
            f"Attempting to resolve source channel '{source_channel_name_for_logs}' (ID/Username: {source_identifier})..."
        )

        # Handle private source channel joining if an invite hash is provided
        if source_config.get("type") == "private" and source_config.get("invite_hash"):
            invite_hash = source_config["invite_hash"]
            logger.info(
                f"Attempting to ensure membership in source private channel '{source_channel_name_for_logs}' using invite hash..."
            )
            try:
                await client(ImportChatInviteRequest(invite_hash))
                logger.info(
                    f"Successfully joined or already a member of source channel '{source_channel_name_for_logs}'."
                )
            except UserAlreadyParticipantError:
                logger.info(
                    f"Telethon account is already a participant in source channel '{source_channel_name_for_logs}'."
                )
            except InviteHashExpiredError:
                logger.error(
                    f"ERROR: The invite hash '{invite_hash}' for source channel '{source_channel_name_for_logs}' has expired or is invalid. Skipping this channel."
                )
                continue  # Skip this source channel and proceed to the next
            except ChatIdInvalidError:
                logger.error(
                    f"ERROR: The invite hash '{invite_hash}' for source channel '{source_channel_name_for_logs}' corresponds to an invalid chat ID. Skipping this channel."
                )
                continue  # Skip this source channel
            except Exception as e:
                logger.error(
                    f"ERROR: An unexpected error occurred while attempting to join source channel '{source_channel_name_for_logs}' with invite hash '{invite_hash}': {e}. Skipping this channel.",
                    exc_info=True,
                )
                continue  # Skip this source channel
        elif (
            source_config.get("type") == "private"
            and not source_config.get("invite_hash")
            and source_config.get("id")
        ):
            logger.info(
                f"Source private channel '{source_channel_name_for_logs}' configured with ID only. Assuming account is already a member. Proceeding to get entity."
            )
        else:
            logger.info(
                f"Source channel '{source_channel_name_for_logs}' is configured as public or has no specific type/invite hash. Proceeding to get entity."
            )

        try:
            entity = await client.get_entity(source_identifier)
            source_channel_entities.append(entity)
            logger.info(
                f"Source channel resolved: {entity.title} (ID/Username: {source_identifier})"
            )
        except ChannelPrivateError:
            logger.error(
                f"ERROR: Source channel '{source_channel_name_for_logs}' (ID: {source_identifier}) is private and could not be accessed. Your account must be a member or the invite_hash was incorrect (if applicable). Skipping this channel."
            )
        except UserNotParticipantError:
            logger.error(
                f"ERROR: Your account is not a participant in source channel '{source_channel_name_for_logs}' (ID: {source_identifier}). Please join it first or provide a valid invite_hash if it's private. Skipping this channel."
            )
        except Exception as e:
            logger.error(
                f"ERROR: Could not resolve source channel '{source_channel_name_for_logs}' (ID: {source_identifier}). Please check the username/ID and ensure your account can access it: {e}. Skipping this channel.",
                exc_info=True,
            )

    if not source_channel_entities:
        logger.critical(
            "FATAL ERROR: No valid source channels could be resolved. The bot has nothing to forward from. Exiting."
        )
        sys.exit(1)

    # --- Message Forwarding Logic ---
    @client.on(events.NewMessage(chats=source_channel_entities))
    async def handler(event):
        try:
            logger.info(
                f"New message detected in source channel '{event.chat.title}' (ID: {event.chat_id}). Attempting to forward..."
            )
            await event.forward_to(target_channel_entity)
            logger.info(
                f"Message from '{event.chat.title}' successfully forwarded to '{target_channel_entity.title}'."
            )
        except Exception as e:
            logger.error(
                f"Failed to forward message from '{event.chat.title}' to '{target_channel_entity.title}': {e}",
                exc_info=True,
            )

    logger.info(
        "Bot is now listening for new messages in configured source channels..."
    )
    logger.info(
        f"Forwarding messages to: '{target_channel_entity.title}' (ID: {target_channel_entity.id})"
    )

    start_time = datetime.now(pytz.timezone(UGANDA_TIMEZONE_STR))
    end_time = start_time + timedelta(hours=OPERATION_DURATION_HOURS)
    logger.info(
        f"Bot scheduled to run for {OPERATION_DURATION_HOURS} hours, until {end_time.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"
    )

    # Keep the client running until operation duration is reached
    while datetime.now(pytz.timezone(UGANDA_TIMEZONE_STR)) < end_time:
        await asyncio.sleep(60)  # Check every minute

    logger.info("Operation duration reached. Initiating graceful shutdown.")


# --- Script Entry Point ---
if __name__ == "__main__":
    current_uganda_time = datetime.now(pytz.timezone(UGANDA_TIMEZONE_STR)).time()

    if not (ACTIVE_START_HOUR <= current_uganda_time.hour < ACTIVE_END_HOUR):
        logger.info(
            f"Current Uganda time: {current_uganda_time.strftime('%H:%M')}. Bot is outside active hours ({ACTIVE_START_HOUR}:00 - {ACTIVE_END_HOUR}:00). Exiting gracefully."
        )
        sys.exit(0)  # Exit gracefully if outside active hours

    try:
        # Create the sessions directory if it doesn't exist
        sessions_dir = os.path.join(replit_root_dir, "sessions")
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir)
            logger.info(f"Created sessions directory: {sessions_dir}")
        else:
            logger.info(f"Sessions directory already exists: {sessions_dir}")

        asyncio.run(main())  # Run the main function
    except SystemExit:
        # Catch SystemExit which is used for controlled exits
        logger.info("Script exited via SystemExit (controlled exit).")
    except Exception as e:
        logger.critical(
            f"CRITICAL APPLICATION ERROR: Telethon bot encountered an unhandled exception during startup or main execution: {e}",
            exc_info=True,
        )
    finally:
        # Ensure client is disconnected even if main() exits via sys.exit(0) or errors
        if client and client.is_connected():
            logger.info("Final cleanup: Disconnecting Telethon client.")
            client.disconnect()
        logger.info("Telethon client disconnected. Script exiting.")
        # Ensure that the log file is properly closed
        if sys.stdout != sys.__stdout__:
            sys.stdout.close()
            sys.stdout = sys.__stdout__  # Restore original stdout
        if sys.stderr != sys.__stderr__:
            sys.stderr.close()
            sys.stderr = sys.__stderr__  # Restore original stderr
