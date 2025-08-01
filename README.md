Telegram Channel Forwarder
This project is a Python-based Telegram bot designed to automatically scrape "open messages" (new, non-forwarded, non-service messages) from specified public Telegram channels and forward them to a designated target Telegram channel. It's built using the Telethon library and is configured to run for a specific duration each day to optimize hosting resource usage.

Features
Automated Message Scraping: Listens for new messages in multiple configured source channels.

Selective Forwarding: Forwards only original text, photo, and document messages, ignoring forwarded messages, bot messages, and service messages.

Configurable Source & Target Channels: Easily define which channels to monitor and where to send the forwarded messages.

Scheduled Operation: Designed to run for a specific duration (e.g., 13 hours) within a defined daily time window (e.g., 8:00 AM - 9:00 PM UTC+3), then gracefully exit to conserve hosting resources.

Secure Credential Handling: Utilizes environment variables for sensitive Telegram API credentials, keeping them out of source control.

Project Structure
.
├── helpers/
│ └── validate_config.py # Script to validate proj_config.json
├── sessions/
│ └── telethon_session.session # Telethon session file (DO NOT SHARE!)
├── proj_config.json # Configuration file for non-sensitive settings
├── requirements.txt # Python dependencies
├── start.bat # Windows batch script for local setup/run
├── telegram_channel_forwarder.py # Main script for channel forwarding
└── .gitignore # Specifies files/folders to ignore in Git
└── README.md # This README file

Setup and Installation (Local)
To run this project locally for testing or initial setup:

Clone the Repository:

git clone <your-github-repo-url>
cd TelegramChannel_Bot # Or whatever your project folder is named

Create and Activate Virtual Environment:

python -m venv venv
.\venv\Scripts\activate.bat # On Windows

# source venv/bin/activate # On macOS/Linux

Install Dependencies:

pip install -r requirements.txt

Prepare proj_config.json:
Create or update proj_config.json in the project root with your channel details. Note: Sensitive API credentials will be set as environment variables, not in this file.

{
"title": "Frank Kyakusse Telethon",
"shortname": "FrankTelethon",
"target_channel": "@YourTargetChannelUsername",
"source_channels": [
"@SourceChannel1Username",
"@SourceChannel2Username"
// Add more source channel usernames or IDs here
]
}

Replace @YourTargetChannelUsername with the actual username of the channel you want to forward messages to.

Replace @SourceChannel1Username, etc., with the usernames or IDs of the public channels you want to scrape from. Your Telegram account (used for Telethon) must be a member of these source channels.

Set Environment Variables (Local):
For local testing, you'll need to set these in your command line session. Replace placeholders with your actual values (get api_id and api_hash from my.telegram.org).

Windows (Command Prompt):

set TELETHON_API_ID=YOUR_API_ID
set TELETHON_API_HASH=YOUR_API_HASH
set TELETHON_PHONE_NUMBER=+YOUR_PHONE_NUMBER

Windows (PowerShell):

$env:TELETHON_API_ID="YOUR_API_ID"
$env:TELETHON_API_HASH="YOUR_API_HASH"
$env:TELETHON_PHONE_NUMBER="+YOUR_PHONE_NUMBER"

macOS/Linux (Bash/Zsh):

export TELETHON_API_ID="YOUR_API_ID"
export TELETHON_API_HASH="YOUR_API_HASH"
export TELETHON_PHONE_NUMBER="+YOUR_PHONE_NUMBER"

YOUR_API_ID: Your Telegram API ID (integer).

YOUR_API_HASH: Your Telegram API Hash (string).

+YOUR_PHONE_NUMBER: Your Telegram phone number, including the international prefix (e.g., +256726348131).

Run the Forwarder:

python telegram_channel_forwarder.py

First Run Authentication: The first time you run it, Telethon will prompt you in the console to enter a verification code sent to your Telegram app. If you have 2FA enabled, it will also ask for your password. Complete this to create telethon_session.session.

Deployment to Replit
This project is designed for efficient deployment on Replit, leveraging its "Always On" feature and an external cron job to manage its operational hours.

Create Repl:

Go to replit.com and create a new Python Repl.

Upload Files:

Upload proj_config.json, telegram_channel_forwarder.py, and requirements.txt to the Repl's root directory.

Create a folder named sessions in the Repl's root.

Upload your telethon_session.session file (generated from your local run) into the sessions folder. This avoids re-authentication on Replit.

Configure requirements.txt:
Ensure requirements.txt contains:

telethon
pytz

Configure .replit file:
Edit the .replit file in your Repl's root to ensure it runs your main script:

run = "python telegram_channel_forwarder.py"
entrypoint = "telegram_channel_forwarder.py"
modules = ["python-3.8"] # Or appropriate Python version

Set Replit Secrets:

In the Replit IDE, go to the "Secrets" tab (padlock icon) in the left sidebar.

Add the following environment variables (these are securely stored and not visible in your code):

TELETHON_API_ID: Your Telegram API ID.

TELETHON_API_HASH: Your Telegram API Hash.

TELETHON_PHONE_NUMBER: Your Telegram phone number (e.g., +256726348131).

Enable "Always On":

In Replit, navigate to the "Tools" section (hammer icon) on the left sidebar.

Find and toggle "Always On" to ON. This keeps your Repl ready to be activated by the cron job.

Get Replit Project URL:

Run your Repl once. A web view will appear on the right. Copy the URL from that browser tab (e.g., https://your-repl-name--your-username.repl.co). This is your public URL.

Set up External Cron Job (e.g., using cron-job.org):

Go to cron-job.org and sign up/log in.

Create a new cronjob.

Title: Telegram Forwarder Daily Start

URL: Paste your Replit Project URL.

HTTP Method: GET.

Schedule:

Timezone: Set to Africa/Nairobi (or UTC+3).

Time: Set to 08:00 (8:00 AM).

Frequency: Daily.

Save the cronjob.

This cron job will ping your Replit project daily at 8:00 AM UTC+3, causing it to start. The telegram_channel_forwarder.py script will then run for 13 hours and exit, ensuring you stay within your desired operational window and manage Replit hours efficiently.

Usage
Once deployed and running:

Ensure your Telethon account is a member of all channels listed in source_channels in your proj_config.json.

Ensure your Telethon account has permission to post in your target_channel.

Any new, original messages (text, photos, documents) posted in the source channels will be automatically forwarded to your target channel during the active operational hours (8:00 AM - 9:00 PM UTC+3).

Troubleshooting
"FATAL ERROR: proj_config.json not found...": Ensure proj_config.json is in the same directory as telegram_channel_forwarder.py.

"FATAL ERROR: Critical Telethon configurations are missing or empty...": Double-check that all required environment variables (TELETHON_API_ID, TELETHON_API_HASH, TELETHON_PHONE_NUMBER) are set correctly in your environment (locally) or Replit Secrets (online). Also, verify target_channel and source_channels in proj_config.json.

"FATAL ERROR: Two-factor authentication (2FA) is enabled...": You need to manually log in once. Run python -m telethon.sync --session sessions/telethon_session --phone +YOUR_PHONE_NUMBER in your activated virtual environment (or Replit shell) and follow the prompts.

"Could not resolve target channel..." or "Source channel is private..." / "User not participant...": Ensure the channel usernames/IDs are correct and that your Telethon account is a member of (and has access to) all specified channels.

Messages not forwarding:

Check the logs in your Replit console for any errors.

Ensure the messages being sent in source channels are original (not forwarded messages) and are text, photos, or documents.

Verify the bot is running during the active hours (8 AM - 9 PM UTC+3).

Confirm your cron job is correctly configured and triggering.
