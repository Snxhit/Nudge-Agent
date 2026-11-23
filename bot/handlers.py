import logging
import asyncio
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from bot.llm import run_agent
from bot.database import get_or_create_account

logger = logging.getLogger(__name__)

# func to send typing status to show responsiveness
async def _keep_typing(bot, chat_id: int):
    try:
        while True:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
            await asyncio.sleep(4)
    except asyncio.CancelledError:
        pass
    except Exception:
        logger.debug("Typing indicator couldn't send.")

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

    await get_or_create_account("telegram", user.id, chat.id, user.username)
    typing_task = asyncio.create_task(_keep_typing(context.bot, chat.id))

    try:
        reply = await run_agent(update.message.text)
    except Exception as exc:
        logger.exception("LLM call failed.")
        reply = f"LLM error: `{exc}`"
    finally:
        typing_task.cancel()

    await update.message.reply_text(reply)