import logging

from telegram.ext import Application

from app.bot.client.me import register_user_handlers
from app.core.config import settings

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


def create_bot_app() -> Application:
    """
    Creates and configures the Telegram Bot Application object, but does not run it.
    """
    # Replace with your actual bot token from BotFather
    BOT_TOKEN = settings.telegram_bot_token

    # Create application
    app = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    register_user_handlers(app)

    return app


# This main function is now only for running the bot standalone for testing
def main():
    app = create_bot_app()
    # Run the bot
    logger.info("Starting bot in polling mode...")
    app.run_polling()


if __name__ == "__main__":
    main()
