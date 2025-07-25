import json
import os
import sys
from dotenv import load_dotenv  # NEW: Import load_dotenv

load_dotenv()  # NEW: Load environment variables from .env at script start

# Define required environment variables (excluding channel names now, as they are dynamic)
REQUIRED_ENV_VARS = [
    "TELETHON_API_ID",
    "TELETHON_API_HASH",
    "TELETHON_PHONE_NUMBER",
    "TELETHON_TARGET_CHANNEL_CONFIG",  # NEW: Target channel config as JSON string
]

# Define required keys in proj_config.json (general settings only)
REQUIRED_CONFIG_KEYS = [
    "title",
    "shortname",
    "active_start_hour",
    "active_end_hour",
    "operation_duration_hours",
]

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "proj_config.json")
CONFIG_PATH = os.path.abspath(CONFIG_PATH)


def validate_channel_config(channel_data, is_target=False):
    """Validates a single channel configuration dictionary."""
    if not isinstance(channel_data, dict):
        if is_target and isinstance(channel_data, str) and channel_data.strip():
            # For target, a simple username string is also acceptable for public channels
            return True, None
        return False, "Channel config must be a JSON object."

    identifier_present = channel_data.get("username") or channel_data.get("id")
    if not identifier_present:
        return False, "Channel config must have 'username' or 'id'."

    if not channel_data.get("title"):
        return False, "Channel config must have a 'title'."

    if channel_data.get("type") == "private":
        if not channel_data.get("invite_hash"):
            return False, "Private channel config must have an 'invite_hash'."

    return True, None


def validate():
    print("--- Validating Environment Variables ---")
    # 1. Validate required environment variables (non-channel specific)
    for env_var in REQUIRED_ENV_VARS:
        if not os.getenv(env_var):
            print(f"❌ Missing or empty environment variable: {env_var}")
            return False

    # 2. Validate TELETHON_TARGET_CHANNEL_CONFIG
    target_channel_json = os.getenv("TELETHON_TARGET_CHANNEL_CONFIG")
    if not target_channel_json:  # Check if the env var itself is missing or empty
        print(
            f"❌ Missing or empty environment variable: TELETHON_TARGET_CHANNEL_CONFIG"
        )
        return False

    try:
        target_channel_data = json.loads(target_channel_json)
        is_valid, error_msg = validate_channel_config(
            target_channel_data, is_target=True
        )
        if not is_valid:
            print(f"❌ Invalid TELETHON_TARGET_CHANNEL_CONFIG: {error_msg}")
            return False
    except json.JSONDecodeError:
        print(f"❌ TELETHON_TARGET_CHANNEL_CONFIG is not a valid JSON string.")
        return False
    except Exception as e:
        print(f"❌ An error occurred validating TELETHON_TARGET_CHANNEL_CONFIG: {e}")
        return False

    print("✅ Environment variables validated.")

    print("\n--- Validating Source Channel Environment Variables ---")
    source_channel_count = 0
    for i in range(1, 100):  # Assuming max 99 source channels (can adjust)
        env_var_name = f"TELETHON_SOURCE_CHANNEL_{i}"
        source_channel_json = os.getenv(env_var_name)
        if source_channel_json is None:
            # No more source channels found
            break

        source_channel_count += 1
        try:
            source_channel_data = json.loads(source_channel_json)
            is_valid, error_msg = validate_channel_config(source_channel_data)
            if not is_valid:
                print(f"❌ Invalid {env_var_name}: {error_msg}")
                return False
            print(f"✅ {env_var_name} validated.")
        except json.JSONDecodeError:
            print(f"❌ {env_var_name} is not a valid JSON string.")
            return False
        except Exception as e:
            print(f"❌ An error occurred validating {env_var_name}: {e}")
            return False

    if source_channel_count == 0:
        print(
            "❌ No TELETHON_SOURCE_CHANNEL_N variables found. At least one source channel is required."
        )
        return False
    print(f"✅ Found and validated {source_channel_count} source channels.")

    print("\n--- Validating proj_config.json ---")
    # 1. Validate proj_config.json file existence
    if not os.path.exists(CONFIG_PATH):
        print("❌ proj_config.json not found.")
        return False

    # 2. Validate proj_config.json content
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to parse proj_config.json: {e}")
        return False

    for key in REQUIRED_CONFIG_KEYS:
        if key not in data:
            print(f"❌ Missing required config field in proj_config.json: {key}")
            return False
        if not isinstance(
            data[key], (str, int)
        ):  # Ensure these general settings are not empty/wrong type
            print(
                f"❌ Invalid type for config field in proj_config.json: {key}. Expected string or int."
            )
            return False

    print("✅ proj_config.json validated.")
    print("\n✅ All configurations validated successfully!")
    return True


if __name__ == "__main__":
    if validate():
        print("\nConfiguration is valid. You can now run the bot.")
    else:
        print("\nConfiguration is NOT valid. Please fix the errors above.")
        sys.exit(1)
