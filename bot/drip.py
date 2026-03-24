"""
Drip sequence processor for ProbBrain onboarding.

Called daily (via cron or run_drip.py) to send scheduled follow-up messages
to subscribers who are due for the next step in the onboarding sequence.

Sequence (days relative to subscribed_at):
  Day 0  — Welcome (sent live by bot on /start, not by this module)
  Day 3  — How to read a signal
  Day 7  — First resolved signal result (handled by signal resolver, not here)
  Day 14 — Soft Pro upsell (only if correct_signals_seen >= 3)
  Day 30 — Check-in survey
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode

from .subscribers import _load_json, _save_json, log_message
from .templates import format_onboarding_day3

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_SUBSCRIBERS_PATH = os.path.join(_DATA_DIR, "subscribers.json")

_DASHBOARD_URL = os.getenv("DASHBOARD_URL", "https://vpjonny.github.io/probbrain-accuracy/")

# Full drip schedule — days from subscribed_at
_DRIP_DAYS = [0, 3, 7, 14, 30]

# This module only handles drip days it knows how to send.
# Day 7 is sent by the signal resolver; Day 14 requires correct_signals_seen gate.
_HANDLED_DAYS = {3, 14, 30}


def _next_drip_day(current: int) -> Optional[int]:
    """Return the next drip day after current, or None if sequence is complete."""
    try:
        idx = _DRIP_DAYS.index(current)
    except ValueError:
        return None
    return _DRIP_DAYS[idx + 1] if idx + 1 < len(_DRIP_DAYS) else None


def _can_message(subscriber: dict, now: datetime) -> bool:
    """Return True if the 48-hour quiet window has passed."""
    last = subscriber.get("last_message_at")
    if not last:
        return True
    last_dt = datetime.fromisoformat(last)
    return (now - last_dt) >= timedelta(hours=48)


def get_drip_due(now: Optional[datetime] = None) -> list[dict]:
    """
    Return subscribers due for their next drip message.

    A subscriber is due when:
    - They are active
    - Their days_since_subscribed >= next_drip_day
    - The 48-hour quiet window has elapsed since last message
    - The next drip day is one this module handles
    """
    if now is None:
        now = datetime.now(timezone.utc)
    subscribers = _load_json(_SUBSCRIBERS_PATH)
    due = []
    for s in subscribers:
        if not s.get("active", True):
            continue
        subscribed_at_str = s.get("subscribed_at")
        if not subscribed_at_str:
            continue
        try:
            subscribed_at = datetime.fromisoformat(subscribed_at_str)
        except ValueError:
            continue
        # Ensure timezone-aware comparison
        if subscribed_at.tzinfo is None:
            subscribed_at = subscribed_at.replace(tzinfo=timezone.utc)

        days_since = (now - subscribed_at).days
        current_drip_day = s.get("drip_day", 0)
        next_day = _next_drip_day(current_drip_day)

        if next_day is None:
            continue  # Sequence complete
        if next_day not in _HANDLED_DAYS:
            continue  # Handled elsewhere (e.g. Day 7 by signal resolver)
        if days_since < next_day:
            continue  # Not due yet
        if not _can_message(s, now):
            continue  # 48h quiet window

        # Day 14 upsell gate: must have seen 3+ correct resolved signals
        if next_day == 14 and s.get("correct_signals_seen", 0) < 3:
            logger.info(
                "Skipping Day 14 upsell for chat_id=%s — correct_signals_seen=%d < 3",
                s.get("chat_id"),
                s.get("correct_signals_seen", 0),
            )
            continue

        s["_next_drip_day"] = next_day
        due.append(s)

    return due


def _advance_drip_day(chat_id: int, next_day: int) -> None:
    """Persist the subscriber's drip_day advancement."""
    subscribers = _load_json(_SUBSCRIBERS_PATH)
    for s in subscribers:
        if s["chat_id"] == chat_id:
            s["drip_day"] = next_day
            break
    _save_json(_SUBSCRIBERS_PATH, subscribers)


def _build_message(next_day: int, subscriber: dict) -> Optional[str]:
    """Return the message text for the given drip day."""
    if next_day == 3:
        return format_onboarding_day3(dashboard_url=_DASHBOARD_URL)
    if next_day == 14:
        return _format_day14_upsell()
    if next_day == 30:
        return _format_day30_survey()
    return None


def _format_day14_upsell() -> str:
    return "\n".join([
        "We've sent a few signals now\\. Here's how we're tracking:",
        "",
        f"[Accuracy dashboard]({_DASHBOARD_URL})",
        "",
        "If you want to see the full reasoning behind each call — "
        "the base rates, the evidence sources, the alternative scenarios we considered — "
        "that's what Pro is for\\.",
        "",
        "Free tier gets the signal and the gap\\. "
        "Pro gets the full write\\-up\\.",
        "",
        "No pressure either way\\. The free signals will keep coming regardless\\.",
        "",
        "If you're curious: reply PRO and I'll send you details\\.",
        "",
        "Unsubscribe any time: /stop",
    ])


def _format_day30_survey() -> str:
    return "\n".join([
        "You've been following ProbBrain for a month\\.",
        "",
        "Two quick questions \\(reply with the number and your answer\\):",
        "",
        "1\\. Which signal has been most interesting to you so far?",
        "2\\. What would make these updates more useful?",
        "",
        "No obligation — just helps us improve\\.",
        "",
        "Unsubscribe any time: /stop",
    ])


async def run_drip_async(bot_token: Optional[str] = None) -> dict:
    """
    Send all due drip messages. Returns a summary dict.

    Args:
        bot_token: Telegram bot token. Falls back to TELEGRAM_BOT_TOKEN env var.
    """
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    now = datetime.now(timezone.utc)
    due = get_drip_due(now)

    if not due:
        logger.info("No subscribers due for drip messages.")
        return {"sent": 0, "skipped": 0, "errors": 0}

    bot = Bot(token=token)
    sent = skipped = errors = 0

    for subscriber in due:
        chat_id = subscriber.get("chat_id")
        next_day = subscriber.get("_next_drip_day")

        if not chat_id or not next_day:
            skipped += 1
            continue

        message = _build_message(next_day, subscriber)
        if not message:
            logger.warning("No message template for drip day %d, skipping chat_id=%s", next_day, chat_id)
            skipped += 1
            continue

        try:
            await bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN_V2,
                disable_web_page_preview=True,
            )
            log_message(chat_id, f"onboarding_day{next_day}", preview=message[:120])
            _advance_drip_day(chat_id, next_day)
            logger.info("Sent Day %d drip to chat_id=%s", next_day, chat_id)
            sent += 1
        except Exception as exc:
            logger.error("Failed to send Day %d drip to chat_id=%s: %s", next_day, chat_id, exc)
            errors += 1

    return {"sent": sent, "skipped": skipped, "errors": errors}


def run_drip(bot_token: Optional[str] = None) -> dict:
    """Synchronous wrapper around run_drip_async."""
    return asyncio.run(run_drip_async(bot_token))
