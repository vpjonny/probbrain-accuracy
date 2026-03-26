"""
Post SIG-023: Will Keir Starmer be out as UK PM by June 30, 2026?
Market 44.5% YES vs our estimate 20% YES. Gap: 24.5pp NO_UNDERPRICED.

Reviewed by:
  - Content Creator (PRO-262): PASS
  - Twitter Engager (PRO-263): cancelled (CEO acknowledged, proceed with standard hooks)
  - Board approval: Approved label on PRO-260

Posting to both Telegram and X.

Usage: python tools/post_sig023_starmer_2026_03_26.py [--dry-run]
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
    "signal_number": 23,
    "signal_id": "SIG-023",
    "question": "Will Keir Starmer be out as UK PM by June 30, 2026?",
    "category": "politics",
    "direction": "NO_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.20,
    "market_price_at_signal": 0.445,
    "gap_pct": 24.5,
    "volume_usdc": 1284438,
    "close_date": "2026-06-30",
    "paperclip_issue": "PRO-260",
    "evidence": [
        "Labour holds 403 MPs — 81 needed to trigger leadership challenge, an unprecedented threshold",
        "No sitting Labour PM has ever faced a leadership election in party history",
        "Survived Epstein crisis Feb 2026 with full cabinet support intact",
        "Structural barriers to removal are insurmountable within timeframe",
    ],
    "counter_evidence": (
        "Key risk: -66 net approval is historically low for a UK PM, but no structural "
        "mechanism exists to force removal before June 30. Poor polling alone does not "
        "trigger a leadership challenge under Labour party rules."
    ),
}

TELEGRAM_COPY = (
    "\U0001f534 HIGH \u2014 Bet NO | MARKET SIGNAL\n\n"
    "\U0001f4ca Will Keir Starmer be out as UK PM by June 30, 2026?\n\n"
    "Market: 44.5% YES | Our estimate: 20% YES\n"
    "Gap: 24.5pp (market overpricing YES)\n"
    "Volume: $1.28M\n"
    "Closes: 2026-06-30\n\n"
    "Evidence:\n"
    "\u2022 Labour holds 403 MPs \u2014 81 needed to trigger challenge, unprecedented threshold\n"
    "\u2022 No sitting Labour PM has ever faced a leadership election\n"
    "\u2022 Survived Epstein crisis Feb 2026 with full cabinet support\n\n"
    "Counter-evidence: -66 net approval is historically low, but no structural "
    "mechanism exists to force removal before June 30. Poor polling alone does "
    "not trigger a leadership challenge under Labour party rules.\n\n"
    "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
    "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
    "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/\n"
    "\U0001f426 Follow us on X: https://x.com/ProbBrain"
)

X_THREAD = {
    "tweet_1": (
        "Polymarket prices Starmer leaving by June 30 at 44.5%. "
        "Our estimate: 20%. Labour has 403 MPs \u2014 81 needed to challenge. "
        "No Labour PM has ever faced one. Gap: 24.5pp."
    ),
    "tweet_2": (
        "Why the market overprices Starmer\u2019s exit:\n\n"
        "\u2022 403 MPs; 81 needed for challenge \u2014 unprecedented bar\n"
        "\u2022 No sitting Labour PM ever faced leadership vote\n"
        "\u2022 Survived Epstein crisis with cabinet intact\n\n"
        "Risk: -66 net approval is historically low, but no mechanism forces removal.\n\n"
        "Market: 44.5% | Our: 20% | Gap: 24.5pp\n\n"
        "Trade: https://dub.sh/pb-x\n\n"
        "Not financial advice."
    ),
    "tweet_3": (
        "We track every call publicly.\n"
        "Accuracy dashboard: https://vpjonny.github.io/probbrain-accuracy/\n\n"
        "Join us on Telegram: https://t.me/ProbBrain\n"
        "Follow @ProbBrain for more signals."
    ),
}


def telegram_send(text: str) -> dict:
    url = f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "disable_web_page_preview": True}
    with httpx.Client(timeout=20) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


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


def update_published(sig: dict, tg_result: dict, x_ids: list, posted_at: str):
    records = json.loads(PUBLISHED.read_text())
    entry = {
        "signal_number": sig["signal_number"],
        "signal_id": sig["signal_id"],
        "question": sig["question"],
        "category": sig["category"],
        "direction": sig["direction"],
        "confidence": sig["confidence"],
        "market_yes_price": sig["market_price_at_signal"],
        "our_calibrated_estimate": sig["our_estimate"],
        "gap_pct": sig["gap_pct"],
        "volume_usdc": sig["volume_usdc"],
        "close_date": sig["close_date"],
        "approved_by": "board-label-PRO-260",
        "platforms": ["telegram", "x"],
        "telegram_link": "https://dub.sh/pb-tg",
        "x_link": "https://dub.sh/pb-x",
        "x_account": "@ProbBrain",
        "telegram_channel": "@ProbBrain",
        "evidence": sig["evidence"],
        "counter_evidence": sig["counter_evidence"],
        "telegram_copy": TELEGRAM_COPY,
        "x_thread_copy": X_THREAD,
        "telegram_message_id": tg_result.get("result", {}).get("message_id") if tg_result else None,
        "telegram_posted_at": posted_at,
        "x_tweet_ids": {
            "tweet_1": x_ids[0] if len(x_ids) > 0 else None,
            "tweet_2": x_ids[1] if len(x_ids) > 1 else None,
            "tweet_3": x_ids[2] if len(x_ids) > 2 else None,
        },
        "x_posted_at": posted_at,
        "paperclip_issue": sig["paperclip_issue"],
        "actually_posted_at": posted_at,
    }
    records.append(entry)
    PUBLISHED.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    logger.info("published_signals.json updated for SIG-023")


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
    logger.info("=== SIG-023 posting script starting (DRY_RUN=%s) ===", DRY_RUN)

    # Rate limit check
    records = json.loads(PUBLISHED.read_text())
    all_times = [p.get("actually_posted_at") for p in records if p.get("actually_posted_at")]
    tg_times = [p.get("telegram_posted_at") for p in records if p.get("telegram_posted_at")]
    all_post_times = [t for t in all_times + tg_times if t]
    if all_post_times:
        last_post = datetime.fromisoformat(max(all_post_times))
        now = datetime.now(timezone.utc)
        elapsed = (now - last_post).total_seconds()
        if elapsed < 1800 and not DRY_RUN:
            logger.error("Rate limit: %.0fs since last post (need 1800). Aborting.", elapsed)
            sys.exit(1)
        logger.info("Gap since last post: %.0fs (minimum 1800)", elapsed)

    # Count today's posts
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_tg = sum(1 for p in records if "telegram" in (p.get("platforms") or [])
                   and (p.get("actually_posted_at") or "").startswith(today_str))
    today_x = sum(1 for p in records if "x" in (p.get("platforms") or [])
                  and (p.get("actually_posted_at") or "").startswith(today_str))
    logger.info("Today's posts — Telegram: %d/40, X: %d/40", today_tg, today_x)
    if today_tg >= 40 and not DRY_RUN:
        logger.error("Telegram daily limit reached. Aborting.")
        sys.exit(1)
    if today_x >= 40 and not DRY_RUN:
        logger.error("X daily limit reached. Aborting.")
        sys.exit(1)

    sig = SIGNAL
    tw = X_THREAD

    # Validate tweet lengths
    t1_len = len(tw["tweet_1"])
    logger.info("Tweet 1 length: %d chars (limit 200)", t1_len)
    if t1_len > 200:
        logger.error("Tweet 1 exceeds 200 chars — aborting")
        sys.exit(1)

    # --- Telegram ---
    logger.info("Posting SIG-023 to Telegram...")
    if DRY_RUN:
        logger.info("DRY RUN Telegram:\n%s", TELEGRAM_COPY)
        tg_result = {"ok": True, "result": {"message_id": -1}}
    else:
        tg_result = telegram_send(TELEGRAM_COPY)
        logger.info("Telegram OK — message_id=%s", tg_result.get("result", {}).get("message_id"))

    time.sleep(2)

    # --- X thread ---
    logger.info("Posting SIG-023 X thread...")
    if DRY_RUN:
        logger.info("DRY RUN X:\nTweet 1: %s\nTweet 2: %s\nTweet 3: %s",
                     tw["tweet_1"], tw["tweet_2"], tw["tweet_3"])
        x_ids = ["dry-t1", "dry-t2", "dry-t3"]
    else:
        x_ids = x_post_thread(tw["tweet_1"], tw["tweet_2"], tw["tweet_3"])

    posted_at = datetime.now(timezone.utc).isoformat()

    if not DRY_RUN:
        update_published(sig, tg_result, x_ids, posted_at)
        logger.info("SIG-023 posted at %s", posted_at)
        logger.info("Pushing dashboard...")
        push_dashboard()
    else:
        logger.info("DRY RUN — skipping published_signals.json update and dashboard push")

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
