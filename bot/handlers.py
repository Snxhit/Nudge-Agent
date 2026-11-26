import logging
import asyncio
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from bot.llm import run_agent
from bot.database import get_or_create_account

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not update.message or not user or not chat:
        return

    account_id = await get_or_create_account("telegram", user.id, chat.id, user.username)
    await update.message.reply_text(f"Hey {user.first_name}! Acc ID: #{account_id}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat
    if not update.message or not update.message.text or not user or not chat:
        return

    acc_id = await get_or_create_account("telegram", user.id, chat.id, user.username)

    try:
        reply = await run_agent(
            user_message=update.message.text,
            acc_id=acc_id,
            platform="telegram",
            chat_id=chat.id
        )
    except Exception as exc:
        logger.exception("Agent error.")
        reply = f"Error: `{exc}`"

    await update.message.reply_text(reply)