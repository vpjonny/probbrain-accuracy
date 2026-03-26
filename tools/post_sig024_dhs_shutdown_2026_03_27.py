"""
Post SIG-024: Will the DHS shutdown end after March 31, 2026? (YES_UNDERPRICED)
Updated numbers from 2026-03-26T23:00Z scan (PRO-271).
Market moved from 68.15% to 46% — refreshed signal with larger gap.

Content reviewed by Content Creator (PRO-272) and Twitter Engager (PRO-273).
Incorporates reviewer feedback: updated numbers, trimmed Tweet 2, added X follow CTA.

Posts to both Telegram and X (0/5 TG, 0/40 X used today).

Usage: python tools/post_sig024_dhs_shutdown_2026_03_27.py [--dry-run]
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

import httpx
import tweepy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent
PUBLISHED = BASE / "data" / "published_signals.json"
DRY_RUN = "--dry-run" in sys.argv

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
TELEGRAM_API = "https://api.telegram.org"

SIGNAL = {
    "signal_number": 24,
    "signal_id": "SIG-024",
    "market_id": "dhs-shutdown-ends-after-march-31-2026",
    "question": "Will the DHS shutdown end after March 31, 2026?",
    "category": "politics",
    "direction": "YES_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.65,
    "market_price_at_signal": 0.46,
    "gap_pct": 18.95,
    "volume_usdc": 985820,
    "close_date": "2026-03-31",
    "paperclip_issue": "PRO-271",
    "evidence": [
        "Senate vote failed for 5th time today (54-46)",
        "Thune dismissed Democratic counteroffer as \"unserious\"",
        "Day 40+ of shutdown — TSA absences at 40%",
        "5 days to deadline with positions hardening",
    ],
    "telegram_copy": (
        "\U0001f534 HIGH \u2014 Bet YES | MARKET SIGNAL\n\n"
        "\U0001f4ca Will the DHS shutdown end after March 31, 2026?\n\n"
        "Market: 46% YES | Our estimate: 65% YES\n"
        "Gap: 18.95pp (market underpricing YES)\n"
        "Volume: $986K\n"
        "Closes: 2026-03-31\n\n"
        "Evidence:\n"
        "\u2022 Senate vote failed for 5th time today (54-46)\n"
        "\u2022 Thune dismissed Democratic counteroffer as \u201cunserious\u201d\n"
        "\u2022 Day 40+ of shutdown \u2014 TSA absences at 40%\n"
        "\u2022 5 days to deadline with positions hardening\n\n"
        "Counter-evidence: Last-minute deals remain possible \u2014 if Trump signals flexibility or "
        "a bipartisan framework emerges before March 31, the market could be correct.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/"
    ),
    "x_thread_copy": {
        "tweet_1": (
            "Polymarket: 46% chance the DHS shutdown extends past March 31. "
            "Our estimate: 65%. Gap: 19pp. Day 40+, Senate vote just failed for the 5th time."
        ),
        "tweet_2": (
            "Why the market underprices continued shutdown:\n\n"
            "\u2022 Senate vote failed 5th time (54-46)\n"
            "\u2022 Thune dismissed Dem counteroffer\n"
            "\u2022 TSA 40% absences, Day 40+\n"
            "\u2022 Positions hardening, 5 days left\n\n"
            "Market: 46% | Our: 65% | Gap: 18.95pp\n\n"
            "Trade YES: https://dub.sh/pb-x\n"
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


def telegram_send(text: str) -> dict:
    url = f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "Markdown"}
    r = httpx.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


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


def update_published(sig: dict, tg_msg_id, x_ids: list, posted_at: str):
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
        "approved_by": "auto-PRO-271",
        "platforms": ["telegram", "x"],
        "telegram_link": "https://dub.sh/pb-tg",
        "x_link": "https://dub.sh/pb-x",
        "x_account": "@ProbBrain",
        "telegram_channel": "@ProbBrain",
        "evidence": sig["evidence"],
        "telegram_copy": sig["telegram_copy"],
        "telegram_message_id": tg_msg_id,
        "x_thread_copy": sig["x_thread_copy"],
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
    logger.info("published_signals.json updated for SIG-024")


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
    logger.info("=== SIG-024 DHS shutdown posting script starting (DRY_RUN=%s) ===", DRY_RUN)

    sig = SIGNAL
    tw = sig["x_thread_copy"]

    # Validate tweet lengths
    t1_len = len(tw["tweet_1"])
    t2_len = len(tw["tweet_2"])
    logger.info("Tweet 1 length: %d chars (limit 200)", t1_len)
    logger.info("Tweet 2 length: %d chars (limit 280)", t2_len)
    if t1_len > 200:
        logger.error("Tweet 1 exceeds 200 chars — aborting")
        sys.exit(1)
    if t2_len > 280:
        logger.error("Tweet 2 exceeds 280 chars (%d) — aborting", t2_len)
        sys.exit(1)

    # Telegram
    logger.info("Posting SIG-024 to Telegram...")
    tg_msg_id = None
    if DRY_RUN:
        logger.info("DRY RUN TG:\n%s", sig["telegram_copy"])
        tg_msg_id = "dry-tg"
    else:
        resp = telegram_send(sig["telegram_copy"])
        tg_msg_id = resp.get("result", {}).get("message_id")
        logger.info("Telegram posted (message_id=%s)", tg_msg_id)

    time.sleep(3)

    # X thread
    logger.info("Posting SIG-024 X thread...")
    if DRY_RUN:
        logger.info(
            "DRY RUN X:\nTweet 1: %s\nTweet 2: %s\nTweet 3: %s",
            tw["tweet_1"], tw["tweet_2"], tw["tweet_3"],
        )
        x_ids = ["dry-t1", "dry-t2", "dry-t3"]
    else:
        x_ids = x_post_thread(tw["tweet_1"], tw["tweet_2"], tw["tweet_3"])

    posted_at = datetime.now(timezone.utc).isoformat()
    update_published(sig, tg_msg_id, x_ids, posted_at)
    logger.info("SIG-024 posted at %s", posted_at)

    if not DRY_RUN:
        logger.info("Pushing dashboard...")
        push_dashboard()

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
