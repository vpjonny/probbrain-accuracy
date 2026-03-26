"""
Post SIG-008 UPDATE: Will Kon Knueppel win the 2025-26 NBA Rookie of the Year award?
Market dropped from 56.7% → 52.8% with no adverse news. Edge widened 8.8pp → 12.1pp.
Confidence upgraded MEDIUM → HIGH.

Sourced from PRO-216 signal description.
Content reviewed by Content Creator (PRO-218). Twitter Engager (PRO-217) caught tweet 2
at 466 chars and condensed to 262 chars (all facts preserved).

Posting to X only — Telegram daily limit (5) already reached today.

This script:
1. Posts SIG-008 UPDATE to X only (Telegram limit exceeded)
2. Updates data/published_signals.json
3. Pushes dashboard

Usage: python tools/post_sig008_update_knueppel_2026_03_26.py [--dry-run]

TIMING NOTE: Run at least 30 minutes after SIG-016 (posted ~14:19Z).
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

# Final copy — incorporates Content Creator (PRO-218) and Twitter Engager (PRO-217) feedback.
# Tweet 2: Twitter Engager condensed from Content Creator's 466-char draft → 262 chars
# Twitter-weighted (all key facts: BetMGM/Dimers, stats, Flagg delta, prices, affiliate link).
SIGNAL = {
    "signal_number": 8,
    "signal_id": "SIG-008",
    "update_of": "SIG-008",
    "market_id": "knueppel-nba-roy-2026",
    "question": "Will Kon Knueppel win the 2025\u201326 NBA Rookie of the Year award?",
    "category": "sports",
    "direction": "YES_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.649,
    "market_price_at_signal": 0.528,
    "gap_pct": 12.1,
    "volume_usdc": 599000,
    "close_date": "2026-05-18",
    "paperclip_issue": "PRO-216",
    "evidence": [
        "BetMGM -180 (64.3% implied) \u2014 sportsbooks increased confidence in Knueppel",
        "Dimers consensus -190 (65.5% implied) \u2014 all major books tilted further YES",
        "19.3 PPG / 49% FG, all-time NBA rookie 3-point record \u2014 statistical case strengthened",
        "Cooper Flagg played 11 fewer games than Knueppel \u2014 visibility gap widens",
    ],
    "x_thread_copy": {
        "tweet_1": (
            "SIG-008 UPDATE: Knueppel Rookie of the Year market dropped to 52.8% with no bad news. "
            "BetMGM -180 (64.3%). "
            "Edge widened from 8.8pp \u2192 12.1pp. Confidence upgraded: MEDIUM \u2192 HIGH. [thread]"
        ),
        "tweet_2": (
            "No bad news. Market fell 56.7% \u2192 52.8%.\n\n"
            "\u2022 BetMGM -180 (64.3%) | Dimers -190 (65.5%)\n"
            "\u2022 19.3 PPG / 49% FG, all-time rookie 3PT record\n"
            "\u2022 Flagg: 11 fewer games (injury)\n\n"
            "Market: 52.8% | Our: 64.9% | Gap: 12.1pp\n\n"
            "Trade: https://dub.sh/pb-x\n\n"
            "Not financial advice."
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
        "update_of": sig.get("update_of"),
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
        "approved_by": "auto-PRO-216",
        "platforms": ["x"],
        "telegram_link": "https://dub.sh/pb-tg",
        "x_link": "https://dub.sh/pb-x",
        "x_account": "@ProbBrain",
        "telegram_channel": "@ProbBrain",
        "evidence": sig["evidence"],
        "telegram_copy": None,
        "telegram_skipped_reason": "Telegram daily limit reached (7/5 signals posted today)",
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
    logger.info("published_signals.json updated for SIG-008 UPDATE")


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
    logger.info("=== SIG-008 UPDATE posting script starting (DRY_RUN=%s) ===", DRY_RUN)

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

    # Validate tweet lengths (raw char counts — Twitter replaces URLs with t.co/23-char tokens)
    t1_len = len(tw["tweet_1"])
    t2_raw = len(tw["tweet_2"])
    # URL https://dub.sh/pb-x (20 chars raw) → 23 chars on Twitter (+3)
    t2_twitter = t2_raw + 3
    logger.info("Tweet 1 length: %d chars (limit 200 per agent spec)", t1_len)
    logger.info("Tweet 2 length: %d raw / %d Twitter-weighted (limit 280)", t2_raw, t2_twitter)
    if t1_len > 200:
        logger.error("Tweet 1 exceeds 200 chars — aborting")
        sys.exit(1)
    if t2_twitter > 280:
        logger.error("Tweet 2 exceeds 280 chars Twitter-weighted (%d) — aborting", t2_twitter)
        sys.exit(1)

    # X thread (Telegram skipped — daily limit exceeded)
    logger.info("Posting SIG-008 UPDATE X thread (Telegram skipped — limit exceeded)...")
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
        logger.info("SIG-008 UPDATE posted at %s", posted_at)
        logger.info("Pushing dashboard...")
        push_dashboard()
    else:
        logger.info("DRY RUN — skipping published_signals.json update and dashboard push")

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
