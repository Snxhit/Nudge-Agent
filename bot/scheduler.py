import logging
from telegram.ext import ContextTypes
from bot.database import fetch_due_reminders, mark_reminder_sent

logger = logging.getLogger(__name__)

async def process_due_reminders(context: ContextTypes.DEFAULT_TYPE):
    due_items = await fetch_due_reminders(platform="telegram")
    for item in due_items:
        try:
            await context.bot.send_message(chat_id=int(item["chat_id"]), text=f"!! Reminder:\n{item['message']}")
            await mark_reminder_sent(item["id"])
        except Exception:
            logger.exception("Failed to send reminder #%s", item["id"])