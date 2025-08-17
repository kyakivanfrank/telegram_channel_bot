# helpers/notifier.py
import os
from telethon import TelegramClient


async def notify_telegram(client: TelegramClient, message: str):
    chat_id = os.getenv("TELETHON_ACC_1_NOTIFICATION_CHAT_ID")
    if not chat_id:
        return
    try:
        await client.send_message(int(chat_id), message)
    except Exception as e:
        print(f"[Notifier] Failed to send message: {e}")
