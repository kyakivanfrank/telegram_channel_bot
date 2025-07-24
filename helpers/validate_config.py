import json
import os
import sys

# Updated REQUIRED_KEYS for Telethon channel forwarding
REQUIRED_KEYS = [
    "api_id",
    "api_hash",
    "phone_number",
    "target_channel",
    "source_channels",
]
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "proj_config.json")
CONFIG_PATH = os.path.abspath(CONFIG_PATH)


def validate():
    if not os.path.exists(CONFIG_PATH):
        print("❌ proj_config.json not found.")
        return False

    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Failed to parse proj_config.json: {e}")
        return False

    for key in REQUIRED_KEYS:
        if key not in data:
            print(f"❌ Missing required config field: {key}")
            return False

        # Special check for source_channels: it must be a non-empty list
        if key == "source_channels":
            if not isinstance(data[key], list) or not data[key]:
                print(
                    f"❌ 'source_channels' must be a non-empty list of channel usernames/IDs."
                )
                return False
        elif not data[key]:  # General check for other keys to not be empty
            print(f"❌ Empty config field: {key}")
            return False

    print("✅ proj_config.json loaded and validated.")
    return True


if not validate():
    sys.exit(1)
