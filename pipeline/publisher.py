"""
Publisher: push signals to Telegram channel.
Sends one message per signal to TELEGRAM_CHANNEL_ID.
"""
import logging
import os
from typing import List

import httpx

from scanner.models import Market
from bot.templates import format_signal

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")    # e.g. @ProbBrain or -100xxxxxxxxxx
DUB_LINK_TELEGRAM = os.getenv("DUB_LINK_TELEGRAM", "https://polymarket.com")

TELEGRAM_API = "https://api.telegram.org"


def _send_message(chat_id: str, text: str) -> dict:
    url = f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }
    with httpx.Client(timeout=15) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


def publish_signals(markets: List[Market], channel_id: str = "", dub_link: str = "") -> int:
    """
    Send each market as a formatted signal to the Telegram channel.
    Returns number of messages sent.
    """
    channel = channel_id or CHANNEL_ID
    link = dub_link or DUB_LINK_TELEGRAM

    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    if not channel:
        raise RuntimeError("TELEGRAM_CHANNEL_ID is not set")

    sent = 0
    for market in markets:
        try:
            text = format_signal(
                question=market.question,
                yes_pct=market.implied_probability,
                volume_usd=market.volume_usd,
                close_date=market.close_date,
                category=market.category,
                market_url=market.url,
                dub_link=link,
                is_pro=True,
            )
            _send_message(channel, text)
            sent += 1
            logger.info("Published signal: %s (%.1f%%)", market.question[:60], market.implied_probability)
        except Exception as exc:
            logger.error("Failed to publish signal for %s: %s", market.id, exc)

    logger.info("Published %d/%d signals to %s", sent, len(markets), channel)
    return sent
