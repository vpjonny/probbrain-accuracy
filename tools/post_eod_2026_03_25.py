"""
Post Day 2 EOD accountability post to Telegram and X.
Content sourced from: content/drafts/2026-03-25-eod.md and PRO-103 task description.
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

import httpx
import tweepy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent
PUBLISHED_EOD = BASE / "data" / "published_eod.json"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
TELEGRAM_API = "https://api.telegram.org"

DRY_RUN = "--dry-run" in sys.argv

DASHBOARD_URL = "https://vpjonny.github.io/probbrain-accuracy/"

# --- Content ---

TELEGRAM_TEXT = """Day 2 update.

Three signals published late yesterday (after EOD), one new call today.

OPEN POSITIONS (4 total, 0 resolved):

Signal #1: Russia x Ukraine ceasefire NO
Market 34.5% → Our est. ~19% | HIGH | Closes Dec 31 2026

Signal #2: China invades Taiwan before GTA VI NO
Market 51.5% → Our est. ~4% | HIGH | Closes ~Jul 2026

Signal #3: OKC Thunder win Western Conference Finals YES
Market 50.5% → Our est. ~60% | MEDIUM | Closes ~Jun 2026

Signal #4: Bitcoin hits $1M before GTA VI NO
Market 48.7% → Our est. ~2% | HIGH | Closes ~Jul 2026

Accuracy: 0 resolved markets. Track record in progress.

Accuracy dashboard: https://vpjonny.github.io/probbrain-accuracy/
Follow us on X: https://x.com/ProbBrain

Not financial advice."""

TWEETS = [
    # Tweet 1 — main hook (185 chars)
    (
        "Day 2. Three signals published after yesterday's EOD window — plus one new call this morning.\n\n"
        "4 signals published total. 0 resolved. Accuracy: building.\n\n"
        "Open positions below. [thread]"
    ),
    # Tweet 2 — Signals 1 & 2 (~199 chars)
    (
        "Signal #1: Russia x Ukraine ceasefire by Dec 31 — NO\n"
        "Market 34.5% | Our est. ~19% | HIGH confidence\n\n"
        "Signal #2: China invades Taiwan before GTA VI — NO\n"
        "Market 51.5% | Our est. ~4% | HIGH confidence"
    ),
    # Tweet 3 — Signals 3 & 4 + summary (~225 chars)
    (
        "Signal #3: OKC Thunder win the WCF — YES\n"
        "Market 50.5% | Our est. ~60% | MEDIUM confidence\n\n"
        "Signal #4: Bitcoin hits $1M before GTA VI — NO\n"
        "Market 48.7% | Our est. ~2% | HIGH confidence\n\n"
        "All 4 positions open. Nothing resolved."
    ),
    # Tweet 4 — dashboard + follow hooks
    (
        "We publish every call. Win or lose, it goes on the record.\n\n"
        f"Accuracy dashboard: {DASHBOARD_URL}\n\n"
        "Get signals on Telegram: https://t.me/ProbBrain\n\n"
        "Not financial advice."
    ),
]


def post_telegram():
    if DRY_RUN:
        logger.info("[DRY RUN] Would post Telegram:\n%s", TELEGRAM_TEXT)
        return None
    url = f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": TELEGRAM_TEXT,
        "disable_web_page_preview": False,
    }
    with httpx.Client(timeout=15) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        msg_id = data["result"]["message_id"]
        logger.info("Telegram posted — message_id=%s", msg_id)
        return msg_id


def post_x_thread():
    consumer_key = os.getenv("X_CONSUMER_KEY", "").strip()
    consumer_secret = os.getenv("X_CONSUMER_SECRET", "").strip()
    access_token = os.getenv("X_ACCESS_TOKEN", "").strip()
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET", "").strip()

    if DRY_RUN:
        for i, t in enumerate(TWEETS, 1):
            logger.info("[DRY RUN] Tweet %d:\n%s\n", i, t)
        return {}

    client = tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    tweet_ids = {}
    prev_id = None
    for i, text in enumerate(TWEETS, 1):
        kwargs = {"text": text}
        if prev_id:
            kwargs["in_reply_to_tweet_id"] = prev_id
        resp = client.create_tweet(**kwargs)
        tid = resp.data["id"]
        tweet_ids[f"tweet_{i}"] = tid
        logger.info("X tweet %d posted — id=%s", i, tid)
        prev_id = tid
        if i < len(TWEETS):
            time.sleep(2)

    return tweet_ids


def update_published_eod(telegram_msg_id, tweet_ids):
    existing = json.loads(PUBLISHED_EOD.read_text()) if PUBLISHED_EOD.exists() else []
    entry = {
        "date": "2026-03-25",
        "type": "eod_accountability",
        "platforms": ["telegram", "x"],
        "published_at": datetime.now(timezone.utc).isoformat(),
        "paperclip_issue": "PRO-103",
        "dry_run": DRY_RUN,
        "telegram": {
            "message_id": telegram_msg_id,
            "channel": CHANNEL_ID,
        },
        "x": {
            "tweet_ids": tweet_ids,
            "account": "@ProbBrain",
        },
    }
    existing.append(entry)
    PUBLISHED_EOD.write_text(json.dumps(existing, indent=2))
    logger.info("Logged to published_eod.json")


def main():
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)
    if not CHANNEL_ID:
        logger.error("TELEGRAM_CHANNEL_ID not set")
        sys.exit(1)

    logger.info("Posting Day 2 EOD accountability post%s", " [DRY RUN]" if DRY_RUN else "")

    # Post Telegram first
    telegram_msg_id = post_telegram()
    logger.info("Waiting 30s before X post...")
    if not DRY_RUN:
        time.sleep(30)

    # Post X thread
    tweet_ids = post_x_thread()

    # Log
    update_published_eod(telegram_msg_id, tweet_ids)
    logger.info("Done.")


if __name__ == "__main__":
    main()
