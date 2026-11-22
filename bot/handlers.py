import logging
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from bot.llm import run_agent

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.effective_user:
        return
    await update.message.reply_text(f"Hey, {update.effective_user.first_name}, Nudge is online.")