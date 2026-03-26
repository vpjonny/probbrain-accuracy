"""
Post SIG-017: Will the next Prime Minister of Hungary be Viktor Orbán? (YES_UNDERPRICED)
Sourced from PRO-221 task description and content/drafts/2026-03-26-signal-017-orban-hungary.md.
Content reviewed by Content Creator (PRO-223) — APPROVED.
X thread reviewed by Twitter Engager (PRO-222) — APPROVED.

Posting to X only — Telegram daily limit (5) already reached today (6/5 posts sent).
Tweet 2 uses Twitter Engager condensed version (270 chars, under 280 limit).
All facts preserved from approved draft; no new information added.

This script:
1. Posts SIG-017 to X only (Telegram limit exceeded)
2. Updates data/published_signals.json
3. Pushes dashboard

Usage: python tools/post_sig017_orban_hungary_2026_03_26.py [--dry-run]

TIMING NOTE: Run at least 30 minutes after SIG-016 (posted ~2026-03-26T14:19:33Z).
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

# Final copy — Twitter Engager (PRO-222) approved version.
# Tweet 1: 150 chars ✓  Tweet 2: 270 chars ✓ (URL counted as 23 by Twitter)
SIGNAL = {
    "signal_number": 17,
    "signal_id": "SIG-017",
    "market_id": "hungary-next-pm-viktor-orban-2026",
    "question": "Will the next Prime Minister of Hungary be Viktor Orbán?",
    "category": "politics",
    "direction": "YES_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.55,
    "market_price_at_signal": 0.355,
    "gap_pct": 19.5,
    "volume_usdc": 3650000,
    "close_date": "2026-04-12",
    "paperclip_issue": "PRO-221",
    "evidence": [
        "Electoral system requires Tisza ~55% popular vote for parliamentary majority vs Fidesz ~45% — confirmed by IOG + Atlatszo structural analysis",
        "Polls near-tied but not past threshold: Tisza 45.6% vs Fidesz 41.6% in independent surveys — opposition leads, but not past the ~55% needed to win",
        "Documented Polymarket whale bets ($200K+ on Magyar/Tisza) artificially suppressing the YES price below 40%",
        "Orbán has won every election since 2010 under the same gerrymandered system — 4 for 4",
        "December 2024 redistricting further cemented Fidesz's structural advantage heading into 2026",
    ],
    "x_thread_copy": {
        "tweet_1": (
            "Polymarket: 35.5% that Orbán stays PM of Hungary. Our read: 55%. Gap: 19.5pp.\n\n"
            "He's won 4 straight elections under this gerrymandered system. [thread]"
        ),
        "tweet_2": (
            "Orbán YES is underpriced at 35.5%:\n\n"
            "• Same map. Fidesz 4/4 wins since 2010.\n"
            "• Tisza needs ~55% national vote to win majority\n"
            "• $200K+ in whale bets on Magyar skewing price\n\n"
            "Market: 35.5% | Our: 55% | Gap: 19.5pp\n\n"
            "Trade YES: https://dub.sh/pb-x\n\n"
            "Not financial advice."
        ),
        "tweet_3": (
            "We track every call publicly, win or lose.\n\n"
            "Accuracy dashboard: https://vpjonny.github.io/probbrain-accuracy/\n\n"
            "Get signals early: https://t.me/ProbBrain"
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
        "approved_by": "auto-PRO-221",
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
    logger.info("published_signals.json updated for SIG-017")


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
    logger.info("=== SIG-017 Orbán Hungary PM posting script starting (DRY_RUN=%s) ===", DRY_RUN)

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
    logger.info("Posting SIG-017 X thread (Telegram skipped — limit exceeded)...")
    if DRY_RUN:
        logger.info(
            "DRY RUN X:\nTweet 1 (%d chars): %s\nTweet 2 (%d chars): %s\nTweet 3: %s",
            t1_len, tw["tweet_1"], t2_len, tw["tweet_2"], tw["tweet_3"],
        )
        x_ids = ["dry-t1", "dry-t2", "dry-t3"]
    else:
        x_ids = x_post_thread(tw["tweet_1"], tw["tweet_2"], tw["tweet_3"])

    posted_at = datetime.now(timezone.utc).isoformat()

    if not DRY_RUN:
        update_published(sig, x_ids, posted_at)
        logger.info("SIG-017 posted at %s", posted_at)
        logger.info("Pushing dashboard...")
        push_dashboard()
    else:
        logger.info("DRY RUN — skipping published_signals.json update and dashboard push")

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
