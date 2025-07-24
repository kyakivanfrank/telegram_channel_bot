import json
import os
import sys

# Updated REQUIRED_KEYS for proj_config.json
# Sensitive keys are now expected as environment variables
REQUIRED_CONFIG_KEYS = ["source_channels"]
REQUIRED_ENV_VARS = [
    "TELETHON_API_ID",
    "TELETHON_API_HASH",
    "TELETHON_PHONE_NUMBER",
    "TELETHON_TARGET_CHANNEL",
]

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "proj_config.json")
CONFIG_PATH = os.path.abspath(CONFIG_PATH)


def validate():
    # 1. Validate environment variables
    for env_var in REQUIRED_ENV_VARS:
        if not os.getenv(env_var):
            print(f"❌ Missing or empty environment variable: {env_var}")
            return False

    # 2. Validate proj_config.json file existence
    if not os.path.exists(CONFIG_PATH):
        print("❌ proj_config.json not found.")
        return False

    # 3. Validate proj_config.json content
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

        # Special check for source_channels: it must be a non-empty list
        if key == "source_channels":
            if not isinstance(data[key], list) or not data[key]:
                print(
                    f"❌ 'source_channels' in proj_config.json must be a non-empty list of channel usernames/IDs."
                )
                return False
        elif not data[
            key
        ]:  # General check for other keys to not be empty (though source_channels is the only one left)
            print(f"❌ Empty config field in proj_config.json: {key}")
            return False

    print(
        "✅ Configuration (Environment Variables & proj_config.json) loaded and validated."
    )
    return True


if not validate():
    sys.exit(1)
