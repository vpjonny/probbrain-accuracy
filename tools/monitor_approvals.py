#!/usr/bin/env python3
"""
Approval reminder: alerts when pending signals sit unreviewed for too long.
Usage: python tools/monitor_approvals.py [--threshold-hours N]
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
PENDING_PATH = ROOT / "data" / "pending_signals.json"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
TELEGRAM_API = "https://api.telegram.org"

DEFAULT_THRESHOLD_HOURS = 2


def load_pending() -> list:
    if not PENDING_PATH.exists():
        return []
    try:
        data = json.loads(PENDING_PATH.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, KeyError):
        logger.warning("Could not parse %s", PENDING_PATH)
        return []


def find_stale(signals: list, threshold_hours: float) -> list:
    now = datetime.now(timezone.utc)
    stale = []
    for s in signals:
        created = s.get("created_at", "")
        if not created:
            continue
        try:
            ts = datetime.fromisoformat(created.replace("Z", "+00:00"))
            hours_waiting = (now - ts).total_seconds() / 3600
            if hours_waiting >= threshold_hours:
                stale.append({**s, "_hours_waiting": round(hours_waiting, 1)})
        except (ValueError, TypeError):
            continue
    return stale


def send_alert(stale: list) -> bool:
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.warning("TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set; printing to stdout")
        for s in stale:
            print(f"  STALE: {s.get('signal_id')} — {s.get('question', '?')[:60]} ({s['_hours_waiting']}h)")
        return False

    lines = ["⏰ *Pending signals awaiting approval:*\n"]
    for s in stale:
        sid = s.get("signal_id", "?")
        q = s.get("question", "?")[:50]
        h = s["_hours_waiting"]
        gap = s.get("gap_pct", "?")
        conf = s.get("confidence", "?")
        lines.append(f"• *{sid}* — {q}… \\({gap}pp {conf}, {h}h waiting\\)")

    text = "\n".join(lines)
    url = f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("Sent approval reminder for %d stale signals", len(stale))
        return True
    except httpx.HTTPError as exc:
        logger.error("Failed to send Telegram alert: %s", exc)
        return False


def main():
    threshold = DEFAULT_THRESHOLD_HOURS
    for i, arg in enumerate(sys.argv):
        if arg == "--threshold-hours" and i + 1 < len(sys.argv):
            threshold = float(sys.argv[i + 1])

    pending = load_pending()
    if not pending:
        logger.info("No pending signals — nothing to check")
        return

    stale = find_stale(pending, threshold)
    if not stale:
        logger.info("All %d pending signals are within %sh threshold", len(pending), threshold)
        return

    logger.warning("%d signal(s) pending approval for >%sh", len(stale), threshold)
    send_alert(stale)


if __name__ == "__main__":
    main()
