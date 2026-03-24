"""
Post approved signals #2 and #3 to Telegram and X.
Reads pre-written copy from data/published_signals.json.
Usage: python post_signals.py [--signal 2] [--dry-run]
"""
import json
import logging
import os
import sys
import time
from pathlib import Path

# Load .env
env_path = Path(__file__).parent / ".env"
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

BASE = Path(__file__).parent
PUBLISHED = BASE / "data" / "published_signals.json"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
TELEGRAM_API = "https://api.telegram.org"

DRY_RUN = "--dry-run" in sys.argv

# Which signal numbers to post (default: 2 and 3)
signal_nums = []
for i, arg in enumerate(sys.argv):
    if arg == "--signal" and i + 1 < len(sys.argv):
        signal_nums.append(int(sys.argv[i + 1]))
if not signal_nums:
    signal_nums = [2, 3]


def check_credentials():
    errors = []
    if not BOT_TOKEN:
        errors.append("TELEGRAM_BOT_TOKEN not set")
    if not CHANNEL_ID:
        errors.append("TELEGRAM_CHANNEL_ID not set")
    for key in ["X_CONSUMER_KEY", "X_CONSUMER_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_TOKEN_SECRET"]:
        if not os.getenv(key, "").strip():
            errors.append(f"{key} not set")
    return errors


def telegram_send(text: str) -> dict:
    url = f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "disable_web_page_preview": True,
    }
    with httpx.Client(timeout=20) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


def x_post_thread(tweet1: str, tweet2: str, tweet3: str) -> list[str]:
    client = tweepy.Client(
        consumer_key=os.getenv("X_CONSUMER_KEY", "").strip(),
        consumer_secret=os.getenv("X_CONSUMER_SECRET", "").strip(),
        access_token=os.getenv("X_ACCESS_TOKEN", "").strip(),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET", "").strip(),
    )
    ids = []
    r1 = client.create_tweet(text=tweet1)
    t1 = r1.data["id"]
    ids.append(t1)
    logger.info("X tweet 1 posted (id=%s)", t1)
    time.sleep(2)

    r2 = client.create_tweet(text=tweet2, in_reply_to_tweet_id=t1)
    t2 = r2.data["id"]
    ids.append(t2)
    logger.info("X tweet 2 posted (id=%s)", t2)
    time.sleep(2)

    r3 = client.create_tweet(text=tweet3, in_reply_to_tweet_id=t2)
    t3 = r3.data["id"]
    ids.append(t3)
    logger.info("X tweet 3 posted (id=%s)", t3)
    return ids


def main():
    cred_errors = check_credentials()
    if cred_errors and not DRY_RUN:
        for e in cred_errors:
            logger.error("CREDENTIAL ERROR: %s", e)
        sys.exit(1)
    elif cred_errors and DRY_RUN:
        for e in cred_errors:
            logger.warning("(dry-run) Missing: %s", e)

    signals = json.loads(PUBLISHED.read_text())

    results = {}

    for sig_num in signal_nums:
        sig = next((s for s in signals if s["signal_number"] == sig_num), None)
        if sig is None:
            logger.error("Signal #%d not found in published_signals.json", sig_num)
            continue

        q = sig["question"]
        tg_copy = sig.get("telegram_copy", "")
        x_copy = sig.get("x_thread_copy", {})
        tw1 = x_copy.get("tweet_1", "")
        tw2 = x_copy.get("tweet_2", "")
        tw3 = x_copy.get("tweet_3", "")

        logger.info("=== Signal #%d: %s ===", sig_num, q)
        logger.info("Confidence: %s | Gap: %s%%", sig["confidence"], sig["gap_pct"])

        # --- Telegram ---
        logger.info("Posting to Telegram...")
        if tg_copy:
            if DRY_RUN:
                logger.info("DRY RUN Telegram:\n%s", tg_copy)
                tg_result = {"ok": True, "dry_run": True}
            else:
                tg_result = telegram_send(tg_copy)
                logger.info("Telegram OK — message_id=%s", tg_result.get("result", {}).get("message_id"))
        else:
            logger.error("No telegram_copy for signal #%d", sig_num)
            tg_result = {}

        time.sleep(3)

        # --- X Thread ---
        logger.info("Posting X thread...")
        if tw1 and tw2 and tw3:
            if DRY_RUN:
                logger.info("DRY RUN X thread:\nTweet 1: %s\nTweet 2: %s\nTweet 3: %s", tw1, tw2, tw3)
                x_ids = ["dry-t1", "dry-t2", "dry-t3"]
            else:
                x_ids = x_post_thread(tw1, tw2, tw3)
                logger.info("X thread posted: %s", x_ids)
        else:
            logger.error("Missing x_thread_copy for signal #%d", sig_num)
            x_ids = []

        results[sig_num] = {
            "telegram": tg_result,
            "x_tweet_ids": x_ids,
        }

        logger.info("Signal #%d done.", sig_num)

        # Gap between signals (if more than one)
        remaining = [n for n in signal_nums if n > sig_num]
        if remaining:
            config = json.loads((BASE / "config" / "publisher.json").read_text())
            gap_sec = config.get("min_gap_between_posts_sec", 1800)
            logger.info("Waiting %d seconds before next signal (per config/publisher.json)...", gap_sec)
            if not DRY_RUN:
                time.sleep(gap_sec)

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
