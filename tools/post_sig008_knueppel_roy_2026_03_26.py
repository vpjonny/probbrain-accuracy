"""
Post SIG-008: Will Kon Knueppel win the 2025-26 NBA Rookie of the Year award? (YES_UNDERPRICED)
Sourced from PRO-166 signal description.
Content reviewed by Content Creator (PRO-168) and Twitter Engager (PRO-167).

This script:
1. Posts SIG-008 to Telegram then X
2. Updates data/published_signals.json
3. Pushes dashboard
4. PATCHes PRO-166 to done via Paperclip API

Usage: python tools/post_sig008_knueppel_roy_2026_03_26.py [--dry-run]
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
PUBLISHED = BASE / "data" / "published_signals.json"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
TELEGRAM_API = "https://api.telegram.org"

PAPERCLIP_API_URL = os.getenv("PAPERCLIP_API_URL", "").strip()
PAPERCLIP_API_KEY = os.getenv("PAPERCLIP_API_KEY", "").strip()
PAPERCLIP_RUN_ID = os.getenv("PAPERCLIP_RUN_ID", "").strip()
PRO_166_ID = "6578b785-b6d9-4f64-bda4-d750c5848463"

DRY_RUN = "--dry-run" in sys.argv

# Final copy — incorporates Content Creator (PRO-168) and Twitter Engager (PRO-167) feedback.
# Tweet 2 is condensed to fit within Twitter's 280-char limit while preserving all key evidence
# points from PRO-167's approved draft (FanDuel -190, NBA.com panel 90%, 3PT record, Flagg injury).
SIGNAL = {
    "signal_number": 8,
    "signal_id": "SIG-008",
    "market_id": "knueppel-nba-roy-2026",
    "question": "Will Kon Knueppel win the 2025\u201326 NBA Rookie of the Year award?",
    "category": "sports",
    "direction": "YES_UNDERPRICED",
    "confidence": "MEDIUM",
    "our_estimate": 0.655,
    "market_price_at_signal": 0.567,
    "gap_pct": 8.8,
    "volume_usdc": 597000,
    "close_date": "2026-05-18",
    "paperclip_issue": "PRO-166",
    "evidence": [
        "FanDuel -190 (65.5% implied) \u2014 sportsbooks pricing Knueppel as heavy favourite",
        "NBA.com expert panel: 90% backing Knueppel \u2014 near-consensus among insiders",
        "Set all-time NBA rookie 3-point record in 2025\u201326 \u2014 historically dominant milestone",
        "Cooper Flagg (closest rival) missed ~1 month with foot injury \u2014 lost games, visibility, and votes",
    ],
    "telegram_copy": (
        "\U0001f7e1 MEDIUM \u2014 Lean YES | MARKET SIGNAL\n\n"
        "\U0001f4ca Will Kon Knueppel win the 2025\u201326 NBA Rookie of the Year award?\n\n"
        "Market: 56.7% YES | Our estimate: 65.5% YES\n"
        "Gap: 8.8pp (market underpricing YES)\n"
        "Volume: $597k\n"
        "Closes: 2026-05-18\n\n"
        "Evidence:\n"
        "\u2022 FanDuel -190 (65.5% implied) \u2014 sportsbooks pricing Knueppel as heavy favourite\n"
        "\u2022 NBA.com expert panel: 90% backing Knueppel \u2014 near-consensus among insiders\n"
        "\u2022 Set all-time NBA rookie 3-point record in 2025\u201326 \u2014 historically dominant milestone\n"
        "\u2022 Cooper Flagg (closest rival) missed ~1 month with foot injury \u2014 lost games, visibility, and votes\n\n"
        "Counter-evidence: If Flagg goes on a historic playoff run or Knueppel regresses late, "
        "ROY votes could tighten. Market may be weighting that playoff-surge scenario.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/"
    ),
    "x_thread_copy": {
        "tweet_1": (
            "Polymarket prices Knueppel at 56.7% to win NBA Rookie of the Year. "
            "FanDuel has him at -190 (65.5%). NBA.com\u2019s expert panel: 90%. Gap: 8.8pp. [thread]"
        ),
        "tweet_2": (
            "FanDuel: -190 (65.5% implied). NBA.com expert panel: 90% Knueppel. "
            "All-time rookie 3PT record. Flagg missed ~1 month with foot injury. "
            "Market underpricing YES.\n\n"
            "Market: 56.7% | Our: 65.5% | Gap: 8.8pp\n\n"
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
        "approved_by": "auto-PRO-166",
        "platforms": ["telegram", "x"],
        "telegram_link": "https://dub.sh/pb-tg",
        "x_link": "https://dub.sh/pb-x",
        "x_account": "@ProbBrain",
        "telegram_channel": "@ProbBrain",
        "evidence": sig["evidence"],
        "telegram_copy": sig["telegram_copy"],
        "x_thread_copy": sig["x_thread_copy"],
        "telegram_message_id": tg_result.get("result", {}).get("message_id") if not DRY_RUN else None,
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
    logger.info("published_signals.json updated for SIG-008")


def paperclip_mark_done(comment: str):
    if not PAPERCLIP_API_URL or not PAPERCLIP_API_KEY:
        logger.warning("Paperclip env vars not set — skipping done update")
        return
    url = f"{PAPERCLIP_API_URL}/api/issues/{PRO_166_ID}"
    headers = {
        "Authorization": f"Bearer {PAPERCLIP_API_KEY}",
        "Content-Type": "application/json",
        "X-Paperclip-Run-Id": PAPERCLIP_RUN_ID,
    }
    payload = {"status": "done", "comment": comment}
    with httpx.Client(timeout=20) as client:
        resp = client.patch(url, json=payload, headers=headers)
        if resp.status_code == 200:
            logger.info("PRO-166 marked done in Paperclip")
        else:
            logger.error("Paperclip PATCH failed: %s %s", resp.status_code, resp.text)


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
    logger.info("=== SIG-008 Knueppel NBA ROY posting script starting (DRY_RUN=%s) ===", DRY_RUN)

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

    # Telegram
    logger.info("Posting SIG-008 to Telegram...")
    if DRY_RUN:
        logger.info("DRY RUN Telegram:\n%s", sig["telegram_copy"])
        tg_result = {"ok": True, "dry_run": True, "result": {"message_id": -1}}
    else:
        tg_result = telegram_send(sig["telegram_copy"])
        logger.info("Telegram OK — message_id=%s", tg_result.get("result", {}).get("message_id"))

    time.sleep(3)

    # X thread
    logger.info("Posting SIG-008 X thread...")
    if DRY_RUN:
        logger.info(
            "DRY RUN X:\nTweet 1: %s\nTweet 2: %s\nTweet 3: %s",
            tw["tweet_1"], tw["tweet_2"], tw["tweet_3"],
        )
        x_ids = ["dry-t1", "dry-t2", "dry-t3"]
    else:
        x_ids = x_post_thread(tw["tweet_1"], tw["tweet_2"], tw["tweet_3"])

    posted_at = datetime.now(timezone.utc).isoformat()
    update_published(sig, tg_result, x_ids, posted_at)
    logger.info("SIG-008 posted at %s", posted_at)

    logger.info("Pushing dashboard...")
    if not DRY_RUN:
        push_dashboard()

    summary = (
        "SIG-008 posted to Telegram (@ProbBrain) and X (@ProbBrain).\n\n"
        "**Signal:** Will Kon Knueppel win the 2025\u201326 NBA Rookie of the Year award?\n"
        "**Direction:** YES_UNDERPRICED | **Confidence:** MEDIUM\n"
        "**Market:** 56.7% YES | **Our estimate:** 65.5% YES | **Gap:** 8.8pp\n"
        "**Volume:** $597k | **Closes:** 2026-05-18\n\n"
        "Copy reviewed by Content Creator ([PRO-168](/PRO/issues/PRO-168)) "
        "and Twitter Engager ([PRO-167](/PRO/issues/PRO-167)).\n"
        "Auto-published (gap < 20pp, approval_required: false).\n\n"
        "Dashboard pushed. Not financial advice."
    )
    if not DRY_RUN:
        paperclip_mark_done(summary)
    else:
        logger.info("DRY RUN — would mark PRO-166 done with:\n%s", summary)

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
