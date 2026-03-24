"""
Telegram bot command handlers for @ProbBrain_bot.
"""
import logging
import os

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from .subscribers import log_message, register_subscriber, unsubscribe
from .templates import HELP_MESSAGE, format_onboarding_day0, format_signal_list

logger = logging.getLogger(__name__)

# Pro subscriber chat IDs — populated from env or a persistent store
PRO_USER_IDS: set[int] = set(
    int(x) for x in os.getenv("PRO_USER_IDS", "").split(",") if x.strip().isdigit()
)

DUB_LINK_TELEGRAM = os.getenv("DUB_LINK_TELEGRAM_BOT", "https://polymarket.com")


def _is_pro(user_id: int) -> bool:
    return user_id in PRO_USER_IDS


def _load_latest_signals() -> list[dict]:
    """Load signals from the most recent scanner snapshot."""
    try:
        from scanner.polymarket import load_latest_snapshot
        snapshot = load_latest_snapshot()
        if snapshot:
            return snapshot.get("markets", [])
    except Exception as exc:
        logger.warning("Could not load signals: %s", exc)
    return []


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id
    username = user.username if user else None

    subscriber, is_new = register_subscriber(chat_id, username=username)

    if is_new:
        msg = format_onboarding_day0()
        await update.message.reply_text(
            msg,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )
        log_message(chat_id, "onboarding_day0", preview="Day 0 welcome sent")
        logger.info("Sent Day 0 onboarding to chat_id=%d (username=%s)", chat_id, username)
    else:
        await update.message.reply_text(
            HELP_MESSAGE,
            parse_mode=ParseMode.MARKDOWN_V2,
            disable_web_page_preview=True,
        )


async def stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    unsubscribe(chat_id)
    await update.message.reply_text(
        "You've been unsubscribed from ProbBrain\\. No more messages\\.\n\n"
        "If you change your mind, just send /start\\.",
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    logger.info("Unsubscribed chat_id=%d", chat_id)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        HELP_MESSAGE,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )


async def signals_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    is_pro = _is_pro(user_id)

    signals = _load_latest_signals()
    msg = format_signal_list(signals, dub_link=DUB_LINK_TELEGRAM, is_pro=is_pro)

    await update.message.reply_text(
        msg,
        parse_mode=ParseMode.MARKDOWN_V2,
        disable_web_page_preview=True,
    )
    logger.info("Sent %s signals to user %d (pro=%s)", len(signals), user_id, is_pro)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Telegram error: %s", context.error, exc_info=context.error)
