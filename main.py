import logging
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from bot.config import config
from bot.handlers import start_command

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO)

def main():
    app = Application.builder().token(config.telegram_token).build()
    app.add_handler(CommandHandler("start", start_command))
    # message handler todo
    #app.add_handler()

    logging.info("Nudge Agent Bot started...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()