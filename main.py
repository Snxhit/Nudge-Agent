import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot.config import config
from bot.handlers import start_command, handle_message, error_handler
from bot.database import init_db
from bot.scheduler import process_due_reminders

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO)

async def post_init(application: Application):
    await init_db()
    logging.info("SQLite database initialised in WAL mode.")

def main():
    app = Application.builder().token(config.telegram_token).post_init(post_init).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.job_queue.run_repeating(process_due_reminders, interval=15, first=5)

    logging.info("Nudge Agent Bot started...")
    app.run_polling(drop_pending_updates=True)

    app.add_error_handler(error_handler)

if __name__ == "__main__":
    main()