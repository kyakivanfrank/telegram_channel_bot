import json
import os
import sys
from dotenv import load_dotenv

# --- Import our new config parser ---
# Adjust path if validate_config.py is in a subfolder like 'helpers'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from helpers.config_parser import parse_channel_env_var

sys.path.pop(0)  # Remove added path to keep sys.path clean

# Define the path to proj_config.json relative to the script's location
# If validate_config.py is in 'helpers/', then 'proj_config.json' is in the parent directory.
PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
CONFIG_PATH = os.path.join(PROJECT_ROOT, "proj_config.json")
CONFIG_PATH = os.path.abspath(CONFIG_PATH)

# Required keys expected in proj_config.json
# Removed 'active_start_hour', 'active_end_hour', 'operation_duration_hours'
# as the bot is now configured for continuous operation.
REQUIRED_CONFIG_KEYS = ["timezone"]


def validate():
    print("--- Running Configuration Validation ---")
    load_dotenv()  # Load .env variables for validation

    # 1. Validate core environment variables
    REQUIRED_CORE_ENV_VARS = [
        "TELETHON_ACC_1_API_ID",
        "TELETHON_ACC_1_API_HASH",
        "TELETHON_ACC_1_PHONE_NUMBER",
        "TELETHON_ACC_1_NOTIFICATION_CHAT_ID",  # Added notification chat ID to required env vars
    ]
    all_core_env_vars_present = True
    for var in REQUIRED_CORE_ENV_VARS:
        value = os.getenv(var)
        if not value:
            print(f"ERROR: Missing or empty environment variable: '{var}'")
            all_core_env_vars_present = False
    if all_core_env_vars_present:
        print("SUCCESS: All core environment variables are set.")
    else:
        print(
            "\nPlease set all required environment variables in your .env file or system environment."
        )
        return False

    # 2. Validate target channel environment variable
    print("\n--- Validating Target Channel Configuration ---")
    try:
        # Corrected: Referencing TELETHON_ACC_1_TARGET_CHANNEL_CONFIG as per your .env file
        target_channel_config = os.getenv("TELETHON_ACC_1_TARGET_CHANNEL_CONFIG")
        if not target_channel_config:
            print(
                "ERROR: Environment variable 'TELETHON_ACC_1_TARGET_CHANNEL_CONFIG' is missing or empty."
            )
            return False
        # Attempt to parse to ensure it's valid JSON (or string)
        parse_channel_env_var(
            "TELETHON_ACC_1_TARGET_CHANNEL_CONFIG"
        )  # Pass the correct name to the parser
        print(
            "SUCCESS: TELETHON_ACC_1_TARGET_CHANNEL_CONFIG loaded and parsed successfully."
        )
    except Exception as e:
        print(
            f"ERROR: TELETHON_ACC_1_TARGET_CHANNEL_CONFIG configuration is invalid: {e}"
        )
        return False

    # 3. Validate source channel environment variables
    print("\n--- Validating Source Channel Configurations ---")
    source_channels_found = False
    i = 1
    while True:
        source_channel_config_name = f"TELETHON_ACC_1_SOURCE_CHANNEL_{i}"
        source_channel_config_value = os.getenv(source_channel_config_name)
        if not source_channel_config_value:
            break
        source_channels_found = True
        try:
            parse_channel_env_var(source_channel_config_name)
            print(
                f"SUCCESS: {source_channel_config_name} loaded and parsed successfully."
            )
        except Exception as e:
            print(f"ERROR: {source_channel_config_name} configuration is invalid: {e}")
            return False
        i += 1

    if not source_channels_found:
        print(
            "ERROR: No source channels configured. "
            "Please set at least one TELETHON_ACC_1_SOURCE_CHANNEL_1 environment variable. At least one is required."
        )
        return False

    # 4. Validate proj_config.json file existence
    print("\n--- Validating proj_config.json ---")
    if not os.path.exists(CONFIG_PATH):
        print(f"ERROR: proj_config.json not found at: {CONFIG_PATH}.")
        return False

    # 5. Validate proj_config.json content
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"ERROR: Failed to parse proj_config.json: It might be malformed JSON.")
        return False
    except Exception as e:
        print(
            f"ERROR: An unexpected error occurred while loading proj_config.json: {e}"
        )
        return False

    for key in REQUIRED_CONFIG_KEYS:
        if key not in data:
            print(f"ERROR: Missing required config field in proj_config.json: '{key}'")
            return False
        if data[key] is None:  # Check for None values for required keys
            print(
                f"ERROR: Required config field '{key}' in proj_config.json cannot be empty."
            )
            return False

    print("SUCCESS: All proj_config.json fields are present.")

    print("\n--- All Configurations Validated Successfully! ---")
    return True


if __name__ == "__main__":
    if not validate():
        sys.exit(1)
