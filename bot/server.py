"""
Telegram bot server — supports both webhook and polling modes.

Webhook mode (production):
    Set TELEGRAM_WEBHOOK_URL in env, then run this module.
    The bot registers its webhook at startup and listens on WEBHOOK_PORT.

Polling mode (development/local):
    Leave TELEGRAM_WEBHOOK_URL unset — the bot falls back to long-polling.
"""
import logging
import os

from telegram.ext import (
    Application,
    CommandHandler,
)

from .handlers import start_handler, stop_handler, help_handler, signals_handler, error_handler

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")   # e.g. https://yourserver.com/webhook
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")


def build_application() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("stop", stop_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("signals", signals_handler))
    app.add_error_handler(error_handler)

    return app


def run_webhook(app: Application) -> None:
    logger.info("Starting bot in webhook mode on port %d", WEBHOOK_PORT)
    app.run_webhook(
        listen="0.0.0.0",
        port=WEBHOOK_PORT,
        url_path=WEBHOOK_PATH,
        webhook_url=f"{WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}",
    )


def run_polling(app: Application) -> None:
    logger.info("Starting bot in polling mode")
    app.run_polling(drop_pending_updates=True)


def start_bot() -> None:
    app = build_application()
    if WEBHOOK_URL:
        run_webhook(app)
    else:
        run_polling(app)
