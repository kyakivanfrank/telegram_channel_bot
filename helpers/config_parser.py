import json
import os
import sys
import logging

# Set up a basic logger for this module, as it might be used independently for validation
parser_logger = logging.getLogger(__name__)
if not parser_logger.handlers:
    # Add a handler only if one doesn't already exist (e.g., from main script's setup)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def parse_channel_env_var(env_var_name):
    """
    Parses a JSON string from an environment variable for channel configuration,
    and performs basic validation. It attempts to strip potential outer quotes.
    Returns the parsed dictionary or raises an exception if parsing/validation fails.
    """
    channel_config_str = os.getenv(env_var_name)
    if not channel_config_str:
        parser_logger.critical(
            f"FATAL ERROR: Environment variable '{env_var_name}' is missing or empty."
        )
        raise ValueError(f"Missing or empty environment variable: {env_var_name}")

    # --- Robustness Fix: Attempt to strip potential outer single or double quotes ---
    # This helps when ENV systems (like some Replit setups) incorrectly wrap the JSON in extra quotes
    if (channel_config_str.startswith("'") and channel_config_str.endswith("'")) or (
        channel_config_str.startswith('"') and channel_config_str.endswith('"')
    ):
        # Only strip if the string starts and ends with the same quote
        channel_config_str = channel_config_str[1:-1]
    # --- End Robustness Fix ---

    try:
        channel_data = json.loads(channel_config_str)
    except json.JSONDecodeError as e:
        parser_logger.critical(
            f"FATAL ERROR: '{env_var_name}' is not a valid JSON string: '{channel_config_str}'. Error: {e}"
        )
        raise ValueError(f"Invalid JSON for {env_var_name}: {e}")
    except Exception as e:
        parser_logger.critical(
            f"FATAL ERROR: An unexpected error occurred parsing '{env_var_name}': {e}",
            exc_info=True,
        )
        raise RuntimeError(f"Unexpected parsing error for {env_var_name}: {e}")

    # Convert simple string (if allowed by json.loads, which it won't be if it's not quoted)
    # This block is mainly for robustness, though current usage expects JSON object.
    if isinstance(channel_data, str):
        # If it's just a string, assume it's a username/title
        channel_data = {"username": channel_data, "title": channel_data}

    # Basic validation for required fields
    identifier_present = channel_data.get("username") or channel_data.get("id")
    if not identifier_present:
        parser_logger.critical(
            f"FATAL ERROR: '{env_var_name}' JSON is missing 'username' or 'id'. Please provide at least one."
        )
        raise ValueError(f"Missing identifier (username or id) for {env_var_name}")

    # Ensure title is present for logging clarity
    if not channel_data.get("title"):
        channel_data["title"] = channel_data.get("username") or str(
            channel_data.get("id")
        )
        parser_logger.warning(
            f"Warning: '{env_var_name}' JSON is missing 'title'. Using '{channel_data['title']}' for logging."
        )

    # Validate private channel specifics
    if channel_data.get("type") == "private":
        if not channel_data.get("invite_hash") and not channel_data.get("id"):
            parser_logger.critical(
                f"FATAL ERROR: Private channel '{env_var_name}' is missing 'invite_hash' or 'id'. For private channels, either an 'invite_hash' (to join) or an 'id' (if already a member) is required."
            )
            raise ValueError(
                f"Private channel {env_var_name} is missing invite_hash or id."
            )

    return channel_data
