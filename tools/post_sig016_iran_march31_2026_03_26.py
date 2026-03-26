"""
Post SIG-016: US forces enter Iran by March 31? (NO_UNDERPRICED)
Sourced from PRO-211 signal description and content/drafts/2026-03-26-signal-016-iran-march31.md.
Content reviewed by Content Creator (PRO-213). Twitter Engager (PRO-212) reviewed wrong draft
(SIG-011/April 30) but flagged discrepancy; resolved — correct signal is SIG-016.

Posting to X only — Telegram daily limit (5) already reached today (6 posts sent).
Tweet 2 trimmed to 267 chars from original 293-char draft prose (under 280-char limit).
All facts preserved; no new information added.

This script:
1. Posts SIG-016 to X only (Telegram limit exceeded)
2. Updates data/published_signals.json
3. Pushes dashboard

Usage: python tools/post_sig016_iran_march31_2026_03_26.py [--dry-run]

TIMING NOTE: Run at least 30 minutes after SIG-015 (posted ~2026-03-26T13:49Z).
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

import tweepy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent
PUBLISHED = BASE / "data" / "published_signals.json"

DRY_RUN = "--dry-run" in sys.argv

# Final copy — incorporates Content Creator (PRO-213) feedback.
# Tweet 2: trimmed from 293-char draft prose to 267 chars (all key facts preserved).
SIGNAL = {
    "signal_number": 16,
    "signal_id": "SIG-016",
    "market_id": "us-forces-enter-iran-march-31-2026",
    "question": "US forces enter Iran by March 31?",
    "category": "geopolitics",
    "direction": "NO_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.13,
    "market_price_at_signal": 0.255,
    "gap_pct": 12.5,
    "volume_usdc": 21900000,
    "close_date": "2026-03-31",
    "paperclip_issue": "PRO-211",
    "evidence": [
        "White House insider (Axios, Mar 20): \"We need about a month more of strikes before taking the island\" — a March 31 ground entry contradicts their own stated timeline",
        "Kharg Island air strikes already happened March 13; market resolves only on physical boots-on-ground entry",
        "~1,000 82nd Airborne + ~4,700 Marines en route — military experts: \"targeted, short-duration,\" not invasion-scale",
        "Iran actively fortifying Kharg with MANPADS — neither side positioned for imminent ground assault",
        "Diplomacy still live: US-Iran Pakistan talks proposed for March 27 with Iran's 5-point counterproposal on the table",
    ],
    "x_thread_copy": {
        "tweet_1": (
            "Polymarket prices US forces entering Iran by March 31 at 25.5%. "
            "White House says they need ~4 more weeks. "
            "5 days to close. Our estimate: 13%. [thread]"
        ),
        "tweet_2": (
            "WH (Axios Mar 20): \"need ~1 more month\" \u2014 March 31 ruled out by WH\u2019s own plan. "
            "Strikes landed Mar 13; resolves on ground entry only. "
            "~5,700 troops = deterrence, not invasion.\n\n"
            "Market: 25.5% | Our: 13% | Gap: 12.5pp\n\n"
            "Trade NO: https://dub.sh/pb-x Not financial advice."
        ),
        "tweet_3": (
            "We track every call publicly.\n"
            "Accuracy dashboard: https://vpjonny.github.io/probbrain-accuracy/\n\n"
            "Join us on Telegram: https://t.me/ProbBrain\n"
            "Follow @ProbBrain for more signals."
        ),
    },
}


def x_post_thread(tweet1: str, tweet2: str, tweet3: str) -> list:
    client = tweepy.Client(
        consumer_key=os.getenv("X_CONSUMER_KEY", "").strip(),
        consumer_secret=os.getenv("X_CONSUMER_SECRET", "").strip(),
        access_token=os.getenv("X_ACCESS_TOKEN", "").strip(),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET", "").strip(),
    )
    ids = []
    r1 = client.create_tweet(text=tweet1)
    t1 = r1.data["id"]
    ids.append(str(t1))
    logger.info("X tweet 1 posted (id=%s)", t1)
    time.sleep(2)

    r2 = client.create_tweet(text=tweet2, in_reply_to_tweet_id=t1)
    t2 = r2.data["id"]
    ids.append(str(t2))
    logger.info("X tweet 2 posted (id=%s)", t2)
    time.sleep(2)

    r3 = client.create_tweet(text=tweet3, in_reply_to_tweet_id=t2)
    t3 = r3.data["id"]
    ids.append(str(t3))
    logger.info("X tweet 3 posted (id=%s)", t3)
    return ids


def update_published(sig: dict, x_ids: list, posted_at: str):
    records = json.loads(PUBLISHED.read_text())
    entry = {
        "signal_number": sig["signal_number"],
        "signal_id": sig["signal_id"],
        "market_id": sig["market_id"],
        "question": sig["question"],
        "category": sig["category"],
        "direction": sig["direction"],
        "confidence": sig["confidence"],
        "market_yes_price": sig["market_price_at_signal"],
        "our_calibrated_estimate": sig["our_estimate"],
        "gap_pct": sig["gap_pct"],
        "volume_usdc": sig["volume_usdc"],
        "close_date": sig["close_date"],
        "approved_by": "auto-PRO-211",
        "platforms": ["x"],
        "telegram_link": "https://dub.sh/pb-tg",
        "x_link": "https://dub.sh/pb-x",
        "x_account": "@ProbBrain",
        "telegram_channel": "@ProbBrain",
        "evidence": sig["evidence"],
        "telegram_copy": None,
        "telegram_skipped_reason": "Telegram daily limit reached (6/5 signals posted today)",
        "x_thread_copy": sig["x_thread_copy"],
        "telegram_message_id": None,
        "x_tweet_ids": {
            "tweet_1": x_ids[0] if len(x_ids) > 0 else None,
            "tweet_2": x_ids[1] if len(x_ids) > 1 else None,
            "tweet_3": x_ids[2] if len(x_ids) > 2 else None,
        },
        "paperclip_issue": sig["paperclip_issue"],
        "actually_posted_at": posted_at,
    }
    records.append(entry)
    PUBLISHED.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    logger.info("published_signals.json updated for SIG-016")


def push_dashboard():
    import subprocess
    result = subprocess.run(
        ["python3", str(BASE / "tools" / "git_push_dashboard.py")],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )
    if result.returncode == 0:
        logger.info("Dashboard pushed successfully")
    else:
        logger.warning("Dashboard push stderr: %s", result.stderr[:300])


def main():
    logger.info("=== SIG-016 Iran/March 31 posting script starting (DRY_RUN=%s) ===", DRY_RUN)

    # Enforce 30-minute gap from last post
    records = json.loads(PUBLISHED.read_text())
    all_times = [p.get("actually_posted_at") for p in records if p.get("actually_posted_at")]
    if all_times:
        last_post_str = max(all_times)
        last_post = datetime.fromisoformat(last_post_str)
        now = datetime.now(timezone.utc)
        elapsed = (now - last_post).total_seconds()
        if elapsed < 1800 and not DRY_RUN:
            logger.error(
                "Rate limit: only %.0f seconds since last post (need 1800). Aborting.",
                elapsed,
            )
            sys.exit(1)
        logger.info("Gap since last post: %.0f seconds (minimum 1800)", elapsed)

    sig = SIGNAL
    tw = sig["x_thread_copy"]

    # Validate tweet lengths
    t1_len = len(tw["tweet_1"])
    t2_len = len(tw["tweet_2"])
    logger.info("Tweet 1 length: %d chars (limit 200 per agent spec)", t1_len)
    logger.info("Tweet 2 length: %d chars (limit 280)", t2_len)
    if t1_len > 200:
        logger.error("Tweet 1 exceeds 200 chars — aborting")
        sys.exit(1)
    if t2_len > 280:
        logger.error("Tweet 2 exceeds 280 chars (%d) — aborting", t2_len)
        sys.exit(1)

    # X thread (Telegram skipped — daily limit exceeded)
    logger.info("Posting SIG-016 X thread (Telegram skipped — limit exceeded)...")
    if DRY_RUN:
        logger.info(
            "DRY RUN X:\nTweet 1: %s\nTweet 2: %s\nTweet 3: %s",
            tw["tweet_1"], tw["tweet_2"], tw["tweet_3"],
        )
        x_ids = ["dry-t1", "dry-t2", "dry-t3"]
    else:
        x_ids = x_post_thread(tw["tweet_1"], tw["tweet_2"], tw["tweet_3"])

    posted_at = datetime.now(timezone.utc).isoformat()

    if not DRY_RUN:
        update_published(sig, x_ids, posted_at)
        logger.info("SIG-016 posted at %s", posted_at)
        logger.info("Pushing dashboard...")
        push_dashboard()
    else:
        logger.info("DRY RUN — skipping published_signals.json update and dashboard push")

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
