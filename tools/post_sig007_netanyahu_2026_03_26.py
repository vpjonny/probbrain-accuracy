"""
Post SIG-007: Netanyahu out by Dec 31, 2026? (NO_UNDERPRICED)
Sourced from data/scans/2026-03-26-07.json, approved via PRO-149 Approved label.
Content reviewed by Content Creator (PRO-156) and Twitter Engager (PRO-158).

This script:
1. Posts SIG-007 to Telegram then X
2. Updates data/published_signals.json
3. Pushes dashboard
4. PATCHes PRO-149 to done via Paperclip API

Usage: python tools/post_sig007_netanyahu_2026_03_26.py [--dry-run]
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
PRO_149_ID = "3c8fc56a-b3c2-42c8-b0d7-d6b390a1f3cc"

DRY_RUN = "--dry-run" in sys.argv

# Final copy — incorporates Content Creator (PRO-156) and Twitter Engager (PRO-158) feedback:
# - Gap written as 21.5pp (not 21.5%)
# - "Oct elections puts" → "Oct elections put" (grammar)
# - Counter-evidence tightened: removed redundant budget path, kept survival path point
# - Tweet 2 compressed to fit 280 chars (Twitter Engager PRO-158)
SIGNAL = {
    "signal_number": 7,
    "signal_id": "SIG-007",
    "market_id": "567688",
    "question": "Will Netanyahu cease to be PM of Israel by Dec 31, 2026?",
    "category": "geopolitics",
    "direction": "NO_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.28,
    "market_price_at_signal": 0.495,
    "gap_pct": 21.5,
    "volume_usdc": 857026,
    "close_date": "2026-12-31",
    "paperclip_issue": "PRO-149",
    "evidence": [
        "Netanyahu re-elected as Likud leader, targets Sept/Oct elections — preference for a late-year vote makes a Dec 31 exit extremely unlikely (Anadolu Agency, March 2026)",
        "Corruption trial verdict not expected until 2027 — no conviction mechanism removing him in calendar 2026 (Wikipedia: Trial of Benjamin Netanyahu)",
        "Israeli coalition formation historically takes 6–12 weeks minimum — Oct elections put a new PM in late Dec or Jan 2027 at best, likely missing the deadline (Chatham House, March 2026)",
        "Budget passes (~55% prob) → Netanyahu controls timing → Oct elections → near-zero Dec 31 exit; if budget fails (~45%), June elections create a narrow but sub-50% exit path",
        "Historical base rate: only 2 of last 5 Israeli PMs left office within 9 months of an active war or major escalation",
    ],
    "telegram_copy": (
        "\U0001f534 HIGH \u2014 Bet NO | MARKET SIGNAL\n\n"
        "\U0001f4ca Will Netanyahu cease to be PM of Israel by Dec 31, 2026?\n\n"
        "Market: 49.5% YES | Our estimate: 28% YES\n"
        "Gap: 21.5pp (market overpricing YES)\n"
        "Volume: $857k\n"
        "Closes: 2026-12-31\n\n"
        "Evidence:\n"
        "\u2022 Netanyahu re-elected as Likud leader, targets Sept/Oct elections \u2014 preference for a late-year vote makes a Dec 31 exit extremely unlikely (Anadolu Agency, March 2026)\n"
        "\u2022 Corruption trial verdict not expected until 2027 \u2014 no conviction mechanism removing him in calendar 2026 (Wikipedia: Trial of Benjamin Netanyahu)\n"
        "\u2022 Israeli coalition formation historically takes 6\u201312 weeks minimum \u2014 Oct elections put a new PM in late Dec or Jan 2027 at best, likely missing the deadline (Chatham House, March 2026)\n"
        "\u2022 Budget passes (~55% prob) \u2192 Netanyahu controls timing \u2192 Oct elections \u2192 near-zero Dec 31 exit; if budget fails (~45%), June elections create a narrow but sub-50% exit path\n"
        "\u2022 Historical base rate: only 2 of last 5 Israeli PMs left office within 9 months of an active war or major escalation\n\n"
        "Counter-evidence: Netanyahu has historically defied political predictions; never count him out of engineering a survival path.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/"
    ),
    "x_thread_copy": {
        "tweet_1": (
            "Polymarket prices Netanyahu at 49.5% to leave office by Dec 31. "
            "Our calibrated estimate: 28%. Gap: 21.5pp. Here\u2019s the evidence. [thread]"
        ),
        "tweet_2": (
            "Likud leadership retained Mar 2026. Targets Sep/Oct elections. "
            "Trial verdict: 2027. Coalition: 6-12 wks. "
            "Oct elections \u2192 new PM in Jan 2027 at earliest. "
            "Budget passes (~55%) \u2192 he controls timing. "
            "Trade: https://dub.sh/pb-x Not financial advice."
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
        "approved_by": "label-approved-PRO-149",
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
    logger.info("published_signals.json updated for SIG-007")


def paperclip_mark_done(comment: str):
    if not PAPERCLIP_API_URL or not PAPERCLIP_API_KEY:
        logger.warning("Paperclip env vars not set — skipping done update")
        return
    url = f"{PAPERCLIP_API_URL}/api/issues/{PRO_149_ID}"
    headers = {
        "Authorization": f"Bearer {PAPERCLIP_API_KEY}",
        "Content-Type": "application/json",
        "X-Paperclip-Run-Id": PAPERCLIP_RUN_ID,
    }
    payload = {"status": "done", "comment": comment}
    with httpx.Client(timeout=20) as client:
        resp = client.patch(url, json=payload, headers=headers)
        if resp.status_code == 200:
            logger.info("PRO-149 marked done in Paperclip")
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
    logger.info("=== SIG-007 Netanyahu posting script starting (DRY_RUN=%s) ===", DRY_RUN)

    sig = SIGNAL
    tw = sig["x_thread_copy"]

    # Verify tweet 2 length (Twitter Engager confirmed ≤280)
    t2_len = len(tw["tweet_2"])
    logger.info("Tweet 2 length: %d chars (limit 280)", t2_len)
    if t2_len > 280:
        logger.error("Tweet 2 exceeds 280 chars — aborting")
        sys.exit(1)

    # Telegram
    logger.info("Posting SIG-007 to Telegram...")
    if DRY_RUN:
        logger.info("DRY RUN Telegram:\n%s", sig["telegram_copy"])
        tg_result = {"ok": True, "dry_run": True, "result": {"message_id": -1}}
    else:
        tg_result = telegram_send(sig["telegram_copy"])
        logger.info("Telegram OK — message_id=%s", tg_result.get("result", {}).get("message_id"))

    time.sleep(3)

    # X thread
    logger.info("Posting SIG-007 X thread...")
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
    logger.info("SIG-007 posted at %s", posted_at)

    logger.info("Pushing dashboard...")
    if not DRY_RUN:
        push_dashboard()

    summary = (
        "SIG-007 posted to Telegram (@ProbBrain) and X (@ProbBrain).\n\n"
        "**Signal:** Will Netanyahu cease to be PM of Israel by Dec 31, 2026?\n"
        "**Direction:** NO_UNDERPRICED\n"
        "**Market:** 49.5% YES | **Our estimate:** 28% YES | **Gap:** 21.5pp\n"
        "**Volume:** $857k | **Closes:** 2026-12-31\n\n"
        "Copy reviewed by Content Creator ([PRO-156](/PRO/issues/PRO-156)) "
        "and Twitter Engager ([PRO-158](/PRO/issues/PRO-158)).\n"
        "Approved via `Approved` label on [PRO-149](/PRO/issues/PRO-149).\n\n"
        "Dashboard pushed. Not financial advice."
    )
    if not DRY_RUN:
        paperclip_mark_done(summary)
    else:
        logger.info("DRY RUN — would mark PRO-149 done with:\n%s", summary)

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
