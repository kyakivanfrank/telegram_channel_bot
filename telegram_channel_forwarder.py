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
    AuthKeyError,
    SessionPasswordNeededError,
    RPCError,
)

# --- Import our new config parser ---
from helpers.config_parser import parse_channel_env_var

# --- CRITICAL PATH FIX FOR REPLIT (Keep for future Replit deployment) ---
# For local Windows execution, this will effectively be os.getcwd()
# but this block specifically handles Replit's environment.
# Assuming bot will be run from its root directory locally or on Replit.
replit_root_dir = os.getcwd()  # Changed from hardcoded Replit path
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
# Define log folder and file paths
LOGS_DIR = os.path.join(replit_root_dir, "logs")
BOT_LOG_FILE_PATH = os.path.join(LOGS_DIR, "bot_log.txt")

# Ensure the logs directory exists
log_dir = os.path.dirname(BOT_LOG_FILE_PATH)
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Redirect stdout and stderr to the bot log file
# This prevents excessive output being sent back to the cron job (on Replit)
# or cluttering the console (locally).
sys.stdout = open(BOT_LOG_FILE_PATH, "a", buffering=1, encoding="utf-8")
sys.stderr = sys.stdout

print(
    f"[{datetime.now().isoformat()}] Script started. Logs redirected to {BOT_LOG_FILE_PATH}"
)

# --- Initialize Logging ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

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
ACTIVE_START_HOUR = CONFIG.get("active_start_hour", 6)
ACTIVE_END_HOUR = CONFIG.get("active_end_hour", 20)
OPERATION_DURATION_HOURS = CONFIG.get("operation_duration_hours", 23)

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

# --- Use the new helper function for configuration loading ---
try:
    TARGET_CHANNEL_CONFIG = parse_channel_env_var("TELETHON_TARGET_CHANNEL_CONFIG")
    logger.info(
        f"Target channel config loaded: {TARGET_CHANNEL_CONFIG.get('title', 'N/A')}"
    )
except ValueError as e:
    logger.critical(f"FATAL ERROR during target channel config parsing: {e}. Exiting.")
    sys.exit(1)
except RuntimeError as e:
    logger.critical(
        f"FATAL ERROR during target channel config parsing (unexpected error): {e}. Exiting.",
        exc_info=True,
    )
    sys.exit(1)

SOURCE_CHANNEL_CONFIGS = []
for i in range(1, 100):
    env_var_name = f"TELETHON_SOURCE_CHANNEL_{i}"
    source_channel_str = os.getenv(env_var_name)
    if source_channel_str is None:
        break

    try:
        source_config = parse_channel_env_var(env_var_name)
        SOURCE_CHANNEL_CONFIGS.append(source_config)
        logger.info(
            f"Source channel '{env_var_name}' config loaded: {source_config.get('title', 'N/A')}"
        )
    except (ValueError, RuntimeError) as e:
        logger.error(
            f"ERROR: Failed to parse source channel '{env_var_name}': {e}. Skipping this channel."
        )
        continue
    except Exception as e:
        logger.error(
            f"ERROR: An unexpected issue occurred while processing '{env_var_name}': {e}. Skipping this channel.",
            exc_info=True,
        )
        continue


if not SOURCE_CHANNEL_CONFIGS:
    logger.critical(
        "FATAL ERROR: No valid source channel configurations found in .env (e.g., TELETHON_SOURCE_CHANNEL_1). At least one source channel is required. Exiting."
    )
    sys.exit(1)

session_file_path = os.path.join(replit_root_dir, "sessions", "telethon_session")
client = TelegramClient(session_file_path, API_ID, API_HASH)


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

    target_channel_entity = None
    target_identifier = TARGET_CHANNEL_CONFIG.get("id") or TARGET_CHANNEL_CONFIG.get(
        "username"
    )
    target_channel_name_for_logs = TARGET_CHANNEL_CONFIG.get("title", target_identifier)

    logger.info(
        f"Attempting to resolve target channel '{target_channel_name_for_logs}' (ID/Username: {target_identifier})..."
    )

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

    source_channel_entities = []
    for source_config in SOURCE_CHANNEL_CONFIGS:
        source_identifier = source_config.get("id") or source_config.get("username")
        source_channel_name_for_logs = source_config.get("title", source_identifier)

        logger.info(
            f"Attempting to resolve source channel '{source_channel_name_for_logs}' (ID/Username: {source_identifier})..."
        )

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
                continue
            except ChatIdInvalidError:
                logger.error(
                    f"ERROR: The invite hash '{invite_hash}' for source channel '{source_channel_name_for_logs}' corresponds to an invalid chat ID. Skipping this channel."
                )
                continue
            except Exception as e:
                logger.error(
                    f"ERROR: An unexpected error occurred while attempting to join source channel '{source_channel_name_for_logs}' with invite hash '{invite_hash}': {e}. Skipping this channel.",
                    exc_info=True,
                )
                continue
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

    while datetime.now(pytz.timezone(UGANDA_TIMEZONE_STR)) < end_time:
        await asyncio.sleep(60)

    logger.info("Operation duration reached. Initiating graceful shutdown.")


if __name__ == "__main__":
    current_uganda_time = datetime.now(pytz.timezone(UGANDA_TIMEZONE_STR)).time()

    if not (ACTIVE_START_HOUR <= current_uganda_time.hour < ACTIVE_END_HOUR):
        logger.info(
            f"Current Uganda time: {current_uganda_time.strftime('%H:%M')}. Bot is outside active hours ({ACTIVE_START_HOUR}:00 - {ACTIVE_END_HOUR}:00). Exiting gracefully."
        )
        sys.exit(0)

    try:
        sessions_dir = os.path.join(replit_root_dir, "sessions")
        if not os.path.exists(sessions_dir):
            os.makedirs(sessions_dir)
            logger.info(f"Created sessions directory: {sessions_dir}")
        else:
            logger.info(f"Sessions directory already exists: {sessions_dir}")

        asyncio.run(main())
    except SystemExit:
        logger.info("Script exited via SystemExit (controlled exit).")
    except Exception as e:
        logger.critical(
            f"CRITICAL APPLICATION ERROR: Telethon bot encountered an unhandled exception during startup or main execution: {e}",
            exc_info=True,
        )
    finally:
        if client and client.is_connected():
            logger.info("Final cleanup: Disconnecting Telethon client.")
            client.disconnect()
        # Ensure sys.stdout and sys.stderr are restored before script truly exits
        # This is important if an external process (like start.bat) is also redirecting output
        if sys.stdout != sys.__stdout__:
            sys.stdout.close()
            sys.stdout = sys.__stdout__
        if sys.stderr != sys.__stderr__:
            sys.stderr.close()
            sys.stderr = sys.__stderr__
