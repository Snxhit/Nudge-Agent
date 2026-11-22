import logging
import asyncio
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from bot.llm import run_agent

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
    if not update.message or not update.effective_user:
        return
    await update.message.reply_text(f"Hey, {update.effective_user.first_name}, Nudge is online.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    typing_task = asyncio.create_task(_keep_typing(context.bot, chat_id))

    try:
        reply = await run_agent(update.message.text)
    except Exception as exc:
        logger.exception("LLM call failed!")
        reply = f"!! LLM Error: `{exc}`"
    finally:
        typing_task.cancel()

    await update.message.reply_text(reply)