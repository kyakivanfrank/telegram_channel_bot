import logging
import json
import os
import sys
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
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

# --- Import the notifier ---
from helpers.notifier import notify_telegram


# --- Custom Exception for Controlled Exits ---
class BotFatalError(Exception):
    """Custom exception for critical errors that should stop the bot."""

    pass


# --- CRITICAL PATH FIX FOR REPLIT ---
# For local Windows execution, this will effectively be os.getcwd()
# but this block specifically handles Replit's environment.
replit_root_dir = os.getcwd()
replit_site_packages_path = os.path.join(
    replit_root_dir, ".pythonlibs", "lib", "python3.12", "site-packages"
)
if (
    os.path.exists(replit_site_packages_path)
    and replit_site_packages_path not in sys.path
):
    sys.path.insert(0, replit_site_packages_path)
# --- END CRITICAL PATH FIX ---


# --- LOGGING SETUP ---
# Initialize Logging to console only
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Prevent Telethon's logger from adding duplicate handlers
if not any(
    isinstance(h, logging.StreamHandler) for h in logging.getLogger("telethon").handlers
):
    TELETHON_ACCOUNT_2_logger = logging.getLogger("telethon")
    TELETHON_ACCOUNT_2_logger.setLevel(logging.WARNING)
    TELETHON_ACCOUNT_2_logger.addHandler(logging.StreamHandler(sys.stdout))


load_dotenv()

# --- Configuration Loading from proj_config.json ---
CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "proj_config.json"
)
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
    raise BotFatalError(f"Malformed proj_config.json: {CONFIG_PATH}")
except Exception as e:
    logger.critical(
        f"FATAL ERROR: An unexpected error occurred while loading {CONFIG_PATH}: {e}. Exiting.",
        exc_info=True,
    )
    raise BotFatalError(f"Error loading proj_config.json: {e}")

# --- General Bot Settings from CONFIG ---
BOT_TITLE = CONFIG.get("title", "Telegram Channel Forwarder Bot")
BOT_SHORTNAME = CONFIG.get("shortname", "ForwarderBot")
UGANDA_TIMEZONE_STR = CONFIG.get("timezone", "Africa/Kampala")

# --- Telethon API Credentials from Environment Variables ---
API_ID = os.getenv("TELETHON_ACCOUNT_2_API_ID")
API_HASH = os.getenv("TELETHON_ACCOUNT_2_API_HASH")
PHONE_NUMBER = os.getenv("TELETHON_ACCOUNT_2_PHONE_NUMBER")

if not all([API_ID, API_HASH, PHONE_NUMBER]):
    logger.critical(
        "FATAL ERROR: TELETHON_ACCOUNT_2_API_ID, TELETHON_ACCOUNT_2_API_HASH, or TELETHON_ACCOUNT_2_PHONE_NUMBER not found in .env. Exiting."
    )
    raise BotFatalError("Missing critical Telethon environment variables.")

try:
    API_ID = int(API_ID)
except ValueError:
    logger.critical(
        "FATAL ERROR: TELETHON_ACCOUNT_2_API_ID must be an integer. Exiting."
    )
    raise BotFatalError("TELETHON_ACCOUNT_2_API_ID must be an integer.")

# --- Use the new helper function for configuration loading ---
try:
    TARGET_CHANNEL_CONFIG = parse_channel_env_var(
        "TELETHON_ACCOUNT_2_TARGET_CHANNEL_CONFIG"
    )
    logger.info(
        f"Target channel config loaded: {TARGET_CHANNEL_CONFIG.get('title', 'N/A')}"
    )
except ValueError as e:
    logger.critical(f"FATAL ERROR during target channel config parsing: {e}. Exiting.")
    raise BotFatalError(f"Target channel config invalid: {e}")
except RuntimeError as e:
    logger.critical(
        f"FATAL ERROR during target channel config parsing (unexpected error): {e}. Exiting.",
        exc_info=True,
    )
    raise BotFatalError(f"Target channel config parsing error: {e}")

SOURCE_CHANNEL_CONFIGS = []
for i in range(1, 100):
    env_var_name = f"TELETHON_ACCOUNT_2_SOURCE_CHANNEL_{i}"
    source_channel_str = os.getenv(env_var_name)
    if source_channel_str is None:
        break

    try:
        source_config = parse_channel_env_var(env_var_name)
        if source_config is not None:
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
        "FATAL ERROR: No valid source channel configurations found in .env (e.g., TELETHON_ACCOUNT_2_SOURCE_CHANNEL_1). At least one source channel is required. Exiting."
    )
    raise BotFatalError("No valid source channel configurations found.")

session_file_path = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "sessions", "TELETHON_ACCOUNT_2_session"
)
client = TelegramClient(session_file_path, API_ID, API_HASH)


async def main():
    logger.info(f"Starting {BOT_TITLE}...")

    try:
        logger.info("Connecting Telethon client...")
        await client.start(phone=PHONE_NUMBER)
        logger.info("Telethon client started successfully.")
        await notify_telegram(client, f"🚀 {BOT_TITLE} started successfully!")
    except SessionPasswordNeededError:
        logger.critical(
            "FATAL ERROR: Two-factor authentication (2FA) is enabled for your account. Please run the script manually once to log in and enter your 2FA password. The script will then save the session, and subsequent runs should work automatically. Exiting."
        )
        raise BotFatalError("2FA enabled, manual login required.")
    except AuthKeyError as e:
        logger.critical(
            f"FATAL ERROR: Authentication failed. Please check your API ID, API Hash, and Phone Number in .env. If you recently revoked your session, you might need to delete the 'sessions' folder and try again. Error: {e}. Exiting.",
            exc_info=True,
        )
        raise BotFatalError(f"Authentication failed: {e}")
    except RPCError as e:
        logger.critical(
            f"FATAL ERROR: A Telegram RPC error occurred during client startup: {e}. Exiting.",
            exc_info=True,
        )
        raise BotFatalError(f"Telegram RPC error during startup: {e}")
    except Exception as e:
        logger.critical(
            f"FATAL ERROR: An unexpected error occurred during client startup: {e}. Exiting.",
            exc_info=True,
        )
        raise BotFatalError(f"Unexpected error during client startup: {e}")

    if not await client.is_user_authorized():
        logger.critical(
            "FATAL ERROR: Telethon client is not authorized. Please run the script manually once to complete the login process (enter phone number, code, and 2FA if applicable). Exiting."
        )
        raise BotFatalError("Telethon client not authorized, manual login required.")

    target_channel_entity = None
    target_identifier = TARGET_CHANNEL_CONFIG.get("id") or TARGET_CHANNEL_CONFIG.get(
        "username"
    )
    target_channel_name_for_logs = TARGET_CHANNEL_CONFIG.get("title", target_identifier)

    logger.info(
        f"Attempting to resolve target channel '{target_channel_name_for_logs}' (ID/Username: {target_identifier})...."
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
            raise BotFatalError(f"Target channel invite hash expired: {invite_hash}")
        except ChatIdInvalidError:
            logger.critical(
                f"FATAL ERROR: The invite hash '{invite_hash}' for target channel '{target_channel_name_for_logs}' corresponds to an invalid chat ID. Exiting."
            )
            raise BotFatalError(
                f"Target channel invite hash invalid chat ID: {invite_hash}"
            )
        except Exception as e:
            logger.critical(
                f"FATAL ERROR: An unexpected error occurred while attempting to join target channel '{target_channel_name_for_logs}' with invite hash '{invite_hash}': {e}. Exiting.",
                exc_info=True,
            )
            raise BotFatalError(f"Error joining target channel with invite hash: {e}")
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
        raise BotFatalError(
            f"Target channel is private and inaccessible: {target_identifier}"
        )
    except UserNotParticipantError:
        logger.critical(
            f"FATAL ERROR: Your account is not a participant in target channel '{target_channel_name_for_logs}' (ID: {target_identifier}). Please join it first or provide a valid invite_hash if it's private. Exiting."
        )
        raise BotFatalError(f"Not a participant in target channel: {target_identifier}")
    except Exception as e:
        logger.critical(
            f"FATAL ERROR: Could not resolve target channel '{target_channel_name_for_logs}' (ID: {target_identifier}). Please check the username/ID and ensure your account can access it: {e}",
            exc_info=True,
        )
        raise BotFatalError(f"Could not resolve target channel: {e}")

    source_channel_entities = []
    for source_config in SOURCE_CHANNEL_CONFIGS:
        source_identifier = source_config.get("id") or source_config.get("username")
        source_channel_name_for_logs = source_config.get("title", source_identifier)

        logger.info(
            f"Attempting to resolve source channel '{source_channel_name_for_logs}' (ID/Username: {source_identifier})...."
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
        raise BotFatalError("No valid source channels could be resolved.")

    # Attach the target channel entity to the config for easy access in the handler.
    TARGET_CHANNEL_CONFIG["entity"] = target_channel_entity

    @client.on(
        events.NewMessage(
            chats=[s.get("username") or s.get("id") for s in SOURCE_CHANNEL_CONFIGS]
        )
    )
    async def handler(event):
        # Gracefully handle events with no chat object.
        if not event.chat:
            logger.warning(
                "Received a message event with no associated chat object. Skipping."
            )
            return

        source_channel_config = next(
            (
                c
                for c in SOURCE_CHANNEL_CONFIGS
                if str(c.get("id")) == str(event.chat_id)
                or c.get("username") == event.chat.username
            ),
            None,
        )

        if not source_channel_config:
            logger.warning(
                f"Could not find configuration for source channel {event.chat_id}. Skipping."
            )
            return

        source_title = source_channel_config.get("title", "Unknown Channel")
        target_channel_entity = TARGET_CHANNEL_CONFIG["entity"]

        try:
            # Check for the protected_forwarding flag from the source channel config
            is_protected = source_channel_config.get("protected_forwarding", False)

            if is_protected:
                logger.info(
                    f"New message detected in protected source channel '{source_title}' (ID: {event.chat_id}). Attempting to send a copy..."
                )
                await client.send_message(
                    target_channel_entity,
                    message=event.message.message,
                    file=event.message.media,
                    link_preview=False,
                    formatting=event.message.entities,
                    reply_to=event.message.reply_to_msg_id,
                )
            else:
                logger.info(
                    f"New message detected in source channel '{source_title}' (ID: {event.chat_id}). Attempting to forward..."
                )
                await event.forward_to(target_channel_entity)

            logger.info(
                f"Message from '{source_title}' successfully handled and sent to '{target_channel_entity.title}'."
            )

        except Exception as e:
            logger.error(
                f"Failed to process message from '{source_title}' to '{target_channel_entity.title}': {e}",
                exc_info=True,
            )

    logger.info(
        "Bot is now listening for new messages in configured source channels..."
    )
    logger.info(
        f"Forwarding messages to: '{target_channel_entity.title}' (ID: {target_channel_entity.id})"
    )

    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except BotFatalError as e:
        logger.critical(
            f"Bot stopped due to a fatal configuration or startup error: {e}"
        )
    except Exception as e:
        logger.critical(
            f"CRITICAL APPLICATION ERROR: Telethon bot encountered an unhandled exception during main execution: {e}",
            exc_info=True,
        )
    finally:
        if client and client.is_connected():
            logger.info("Final cleanup: Disconnecting Telethon client.")
            try:
                asyncio.run(notify_telegram(client, f"🛑 {BOT_TITLE} has stopped."))
                asyncio.run(client.disconnect())
            except RuntimeError as e:
                logger.error(
                    f"Error during final async cleanup (event loop issue): {e}"
                )
            except Exception as e:
                logger.error(f"Error during final async cleanup: {e}")
        else:
            logger.info(
                "Client was not connected or already disconnected during final cleanup."
            )
