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
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "proj_config.json")
CONFIG_PATH = os.path.abspath(CONFIG_PATH)

# Required keys expected in proj_config.json
REQUIRED_CONFIG_KEYS = [
    "timezone",
    "active_start_hour",
    "active_end_hour",
    "operation_duration_hours",
]


def validate():
    print("--- Running Configuration Validation ---")
    load_dotenv()  # Load .env variables for validation

    # 1. Validate core environment variables
    REQUIRED_CORE_ENV_VARS = [
        "TELETHON_API_ID",
        "TELETHON_API_HASH",
        "TELETHON_PHONE_NUMBER",
    ]
    for env_var in REQUIRED_CORE_ENV_VARS:
        if not os.getenv(env_var):
            print(f"ERROR: Missing or empty core environment variable: {env_var}")
            return False

    # 2. Validate TELETHON_API_ID is an integer
    try:
        if os.getenv("TELETHON_API_ID"):
            int(os.getenv("TELETHON_API_ID"))
    except ValueError:
        print("ERROR: TELETHON_API_ID must be an integer.")
        return False

    # 3. Validate target channel config using the shared parser
    print("\n--- Validating Target Channel Configuration ---")
    try:
        target_config = parse_channel_env_var("TELETHON_TARGET_CHANNEL_CONFIG")
        print(
            f"SUCCESS: TELETHON_TARGET_CHANNEL_CONFIG loaded and parsed successfully: {target_config.get('title', 'N/A')}"
        )
    except (ValueError, RuntimeError) as e:
        print(f"ERROR: Error in TELETHON_TARGET_CHANNEL_CONFIG: {e}")
        return False

    # 4. Validate source channel configurations using the shared parser
    print("\n--- Validating Source Channel Configurations ---")
    found_source_channels = False
    for i in range(
        1, 100
    ):  # Check for TELETHON_SOURCE_CHANNEL_1 to TELETHON_SOURCE_CHANNEL_99
        env_var_name = f"TELETHON_SOURCE_CHANNEL_{i}"
        if os.getenv(env_var_name) is None:  # None means the env var does not exist
            continue

        try:
            source_config = parse_channel_env_var(env_var_name)
            print(
                f"SUCCESS: {env_var_name} loaded and parsed successfully: {source_config.get('title', 'N/A')}"
            )
            found_source_channels = True
        except (ValueError, RuntimeError) as e:
            print(f"ERROR: Error in {env_var_name}: {e}")
            return False

    if not found_source_channels:
        print(
            "ERROR: No valid source channel configurations found (e.g., TELETHON_SOURCE_CHANNEL_1). At least one is required."
        )
        return False

    # 5. Validate proj_config.json file existence
    print("\n--- Validating proj_config.json ---")
    if not os.path.exists(CONFIG_PATH):
        print(f"ERROR: proj_config.json not found at: {CONFIG_PATH}.")
        return False

    # 6. Validate proj_config.json content
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
    sys.exit(0)  # Exit with success code if validation passes
