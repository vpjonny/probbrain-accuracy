"""
Publisher: push signals to Telegram channel with deduplication.
Sends one message per signal to TELEGRAM_CHANNEL_ID.
Checks published_signals.json before posting to prevent duplicates.
Persists successfully published signals back to published_signals.json.
"""
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import httpx

from scanner.models import Market
from bot.templates import format_signal

logger = logging.getLogger(__name__)

# Hard-coded gap between posting successive signals (seconds).
# 30 minutes minimum between posts to avoid flooding channels.
MIN_GAP_BETWEEN_POSTS_SEC = 1800

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")    # e.g. @ProbBrain or -100xxxxxxxxxx
DUB_LINK_TELEGRAM = os.getenv("DUB_LINK_TELEGRAM", "https://polymarket.com")

TELEGRAM_API = "https://api.telegram.org"

PUBLISHED_SIGNALS_PATH = Path("data/published_signals.json")


def _load_published_market_ids() -> set:
    """Load set of market IDs already published to prevent duplicate posts."""
    if not PUBLISHED_SIGNALS_PATH.exists():
        return set()
    try:
        signals = json.loads(PUBLISHED_SIGNALS_PATH.read_text())
        return {str(s.get("market_id", "")) for s in signals if s.get("market_id")}
    except (json.JSONDecodeError, KeyError):
        logger.warning("Could not parse %s for dedup check", PUBLISHED_SIGNALS_PATH)
        return set()


def _get_next_signal_number() -> int:
    """Get the next auto-incremented signal number."""
    if not PUBLISHED_SIGNALS_PATH.exists():
        return 1
    try:
        signals = json.loads(PUBLISHED_SIGNALS_PATH.read_text())
        if not signals:
            return 1
        # Find max signal_number and increment
        max_num = max(int(s.get("signal_number", 0)) for s in signals if s.get("signal_number"))
        return max_num + 1
    except (json.JSONDecodeError, KeyError, ValueError):
        logger.warning("Could not compute next signal number; defaulting to 1")
        return 1


def _persist_published_signal(
    market_id: str,
    question: str,
    telegram_message_id: Optional[str],
    channel_id: str,
) -> None:
    """
    Append a published signal record to published_signals.json.
    Only called after successful Telegram posting.
    """
    try:
        # Load existing signals
        if PUBLISHED_SIGNALS_PATH.exists():
            signals = json.loads(PUBLISHED_SIGNALS_PATH.read_text())
        else:
            signals = []

        # Prepare new record with minimal fields
        signal_record = {
            "signal_number": _get_next_signal_number(),
            "market_id": market_id,
            "question": question,
            "telegram_message_id": telegram_message_id,
            "telegram_channel": channel_id,
            "published_at": datetime.utcnow().isoformat() + "Z",
        }

        signals.append(signal_record)

        # Write back to file
        PUBLISHED_SIGNALS_PATH.write_text(json.dumps(signals, indent=2))
        logger.info("Persisted published signal: market_id=%s, signal_number=%d",
                    market_id, signal_record["signal_number"])
    except Exception as exc:
        logger.error("Failed to persist published signal for market %s: %s", market_id, exc)


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
    Skips markets already in published_signals.json (dedup guard).
    Returns number of messages sent.
    """
    channel = channel_id or CHANNEL_ID
    link = dub_link or DUB_LINK_TELEGRAM

    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    if not channel:
        raise RuntimeError("TELEGRAM_CHANNEL_ID is not set")

    # Dedup: skip already-published markets
    published_ids = _load_published_market_ids()

    sent = 0
    for market in markets:
        if str(market.id) in published_ids:
            logger.info("DEDUP: skipping market %s (%s) — already published", market.id, market.question[:40])
            continue

        try:
            # Enforce gap between successive posts
            if sent > 0:
                logger.info(
                    "Waiting %d seconds before next signal post...",
                    MIN_GAP_BETWEEN_POSTS_SEC,
                )
                time.sleep(MIN_GAP_BETWEEN_POSTS_SEC)

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
            result = _send_message(channel, text)
            message_id = result.get("result", {}).get("message_id")
            sent += 1
            # Add to in-memory set so subsequent markets in same batch are also deduped
            published_ids.add(str(market.id))
            logger.info("Published signal: %s (%.1f%%) [tg_msg_id=%s]",
                        market.question[:60], market.implied_probability, message_id)
            # Persist to published_signals.json after successful post
            _persist_published_signal(
                market_id=str(market.id),
                question=market.question,
                telegram_message_id=message_id,
                channel_id=channel,
            )
        except Exception as exc:
            logger.error("Failed to publish signal for %s: %s", market.id, exc)

    logger.info("Published %d/%d signals to %s", sent, len(markets), channel)
    return sent
