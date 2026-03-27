"""
Post X thread for SIG-027 + SIG-028 + SIG-029 (X-only, Telegram already sent).
Updates existing published_signals.json entries with X tweet IDs.

Usage: python tools/post_sig027_028_029_x_only.py [--dry-run]
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

import tweepy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent
PUBLISHED = BASE / "data" / "published_signals.json"
DRY_RUN = "--dry-run" in sys.argv

# Combined X thread for all three signals
X_THREAD = {
    "tweet_1": (
        "Polymarket: 40.5% chance of US-Iran ceasefire by April 30. "
        "Iran rejected the 15-point plan. FM denies any talks. "
        "Our estimate: 15%. Gap: 25.5pp."
    ),
    "tweet_2": (
        "• Iran rejected 15-point plan\n"
        "• FM: 'no peace talks have taken place'\n"
        "• Pakistan backchannel — Iran refuses\n"
        "• Military escalation both sides\n\n"
        "Apr 7: 14%→3% | Apr 15: 28.5%→9% | Apr 30: 40.5%→15%\n\n"
        "Trade NO: https://dub.sh/pb-x\n"
        "Not financial advice."
    ),
    "tweet_3": (
        "If ceasefire doesn't happen by April 7 (our highest-confidence NO at 3%), "
        "April 15 and April 30 become even less likely. Each deadline builds on the last. "
        "The market is pricing hope, not evidence."
    ),
    "tweet_4": (
        "We track every call publicly.\n"
        "Accuracy dashboard: https://vpjonny.github.io/probbrain-accuracy/\n\n"
        "Join us on Telegram: https://t.me/ProbBrain\n"
        "Follow @ProbBrain for more signals."
    ),
}


def x_post_thread(tweets: list[str]) -> list[str]:
    client = tweepy.Client(
        consumer_key=os.getenv("X_CONSUMER_KEY", "").strip(),
        consumer_secret=os.getenv("X_CONSUMER_SECRET", "").strip(),
        access_token=os.getenv("X_ACCESS_TOKEN", "").strip(),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET", "").strip(),
    )
    ids = []
    prev_id = None
    for i, text in enumerate(tweets):
        kwargs = {"text": text}
        if prev_id:
            kwargs["in_reply_to_tweet_id"] = prev_id
        r = client.create_tweet(**kwargs)
        tid = str(r.data["id"])
        ids.append(tid)
        prev_id = tid
        logger.info("X tweet %d posted (id=%s)", i + 1, tid)
        if i < len(tweets) - 1:
            time.sleep(2)
    return ids


def update_published_records_x_only(x_ids, posted_at):
    """Update existing published_signals.json entries with X tweet IDs (only first signal gets thread)."""
    records = json.loads(PUBLISHED.read_text())

    sig_ids_to_update = ["SIG-027", "SIG-028", "SIG-029"]
    found_first = False

    for record in records:
        if record.get("signal_id") in sig_ids_to_update:
            # Add "x" to platforms if not already there
            if "x" not in record.get("platforms", []):
                record["platforms"].append("x")

            # Only the first signal gets the thread IDs (combined thread)
            if record.get("signal_id") == "SIG-027" and not found_first:
                record["x_tweet_ids"] = {f"tweet_{i+1}": tid for i, tid in enumerate(x_ids)}
                record["x_posted_at"] = posted_at
                found_first = True
                logger.info("Updated %s with X thread (4 tweets)", record.get("signal_id"))
            else:
                logger.info("Updated %s platforms to include 'x'", record.get("signal_id"))

    PUBLISHED.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    logger.info("published_signals.json updated with X thread IDs")


def main():
    logger.info("=== SIG-027 + SIG-028 + SIG-029 X-only posting (DRY_RUN=%s) ===", DRY_RUN)

    # Validate tweet lengths
    for i, key in enumerate(["tweet_1", "tweet_2", "tweet_3", "tweet_4"]):
        length = len(X_THREAD[key])
        limit = 200 if i == 0 else 280
        logger.info("Tweet %d length: %d chars (limit %d)", i + 1, length, limit)
        if length > limit:
            logger.error("Tweet %d exceeds %d chars (%d) — aborting", i + 1, limit, length)
            sys.exit(1)

    # --- X: Combined thread ---
    logger.info("Posting combined X thread (SIG-027 + SIG-028 + SIG-029)...")
    tweets = [X_THREAD["tweet_1"], X_THREAD["tweet_2"], X_THREAD["tweet_3"], X_THREAD["tweet_4"]]
    if DRY_RUN:
        for i, t in enumerate(tweets):
            logger.info("DRY RUN Tweet %d: %s", i + 1, t)
        x_ids = ["dry-t1", "dry-t2", "dry-t3", "dry-t4"]
    else:
        x_ids = x_post_thread(tweets)

    posted_at = datetime.now(timezone.utc).isoformat()

    # Update published records with X IDs only
    if not DRY_RUN:
        update_published_records_x_only(x_ids, posted_at)

    logger.info("X thread posted at %s", posted_at)
    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
