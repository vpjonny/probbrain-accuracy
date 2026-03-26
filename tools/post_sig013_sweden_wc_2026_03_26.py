"""
Post SIG-013: Will Sweden qualify for the 2026 FIFA World Cup? (NO_UNDERPRICED)
Sourced from PRO-198 signal description.
Content reviewed by Content Creator (PRO-199) and Twitter Engager (PRO-200).

This script:
1. Posts SIG-013 to Telegram then X
2. Updates data/published_signals.json
3. Pushes dashboard
4. PATCHes PRO-198 to done via Paperclip API

Usage: python tools/post_sig013_sweden_wc_2026_03_26.py [--dry-run]
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
PRO_198_ID = "781fc859-0917-481a-a6e8-c8e65de7b10b"

DRY_RUN = "--dry-run" in sys.argv

# Final copy — incorporates Content Creator (PRO-199) and Twitter Engager (PRO-200) feedback.
# Content Creator fix applied: "Poland ~52% fav in the final" → "Poland ~52% fav in the qualifying final"
SIGNAL = {
    "signal_number": 13,
    "signal_id": "SIG-013",
    "market_id": "sweden-2026-wc-qualifier",
    "question": "Will Sweden qualify for the 2026 FIFA World Cup?",
    "category": "sports",
    "direction": "NO_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.155,
    "market_price_at_signal": 0.345,
    "gap_pct": 19.0,
    "volume_usdc": 131000,
    "close_date": "2026-04-12",
    "paperclip_issue": "PRO-198",
    "evidence": [
        "Sweden's semi-final vs Ukraine is TODAY — Opta gives them only 32% to advance (21% in 90 mins + extra time/pens)",
        "Even if Sweden advances, they almost certainly face Poland (Poland ~57% to beat Albania in the other semi)",
        "Combined two-match probability: ~32% × 48% ≈ 15% — matches our estimate exactly",
        "Market is pricing Sweden as if the semi-final is already won — classic single-match double-count error",
        "$131K volume is relatively thin — inefficient market, susceptible to optimism bias",
    ],
    "telegram_copy": (
        "\U0001f534 HIGH \u2014 Bet NO | MARKET SIGNAL\n\n"
        "\U0001f4ca Will Sweden qualify for the 2026 FIFA World Cup?\n\n"
        "Market: 34.5% YES | Our estimate: 15.5% YES\n"
        "Gap: 19pp (market overpricing YES)\n"
        "Volume: $131K\n"
        "Closes: 2026-04-12\n\n"
        "Evidence:\n"
        "\u2022 Sweden's semi-final vs Ukraine is TODAY \u2014 Opta gives them only 32% to advance (21% in 90 mins + extra time/pens)\n"
        "\u2022 Even if Sweden advances, they almost certainly face Poland (Poland ~57% to beat Albania in the other semi)\n"
        "\u2022 Combined two-match probability: ~32% \u00d7 48% \u2248 15% \u2014 matches our estimate exactly\n"
        "\u2022 Market is pricing Sweden as if the semi-final is already won \u2014 classic single-match double-count error\n"
        "\u2022 $131K volume is relatively thin \u2014 inefficient market, susceptible to optimism bias\n\n"
        "Counter-evidence: Semi-finals are high-variance. Sweden could outperform Opta\u2019s model and draw a weaker path than expected. "
        "If Albania beats Poland, Sweden\u2019s final-stage odds improve meaningfully.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/"
    ),
    "x_thread_copy": {
        "tweet_1": (
            "Polymarket prices Sweden qualifying for the 2026 World Cup at 34.5%. "
            "Their semi-final vs Ukraine is TODAY. Opta: 32% chance they advance. "
            "Combined WC probability: ~15%. Gap: 19pp. [thread]"
        ),
        "tweet_2": (
            "Semi-final TODAY vs Ukraine (Opta: 32% advance). "
            "If through, face likely Poland (~57% vs Albania) \u2014 Poland ~52% fav in the qualifying final. "
            "Combined: 32% \u00d7 48% \u2248 15%.\n\n"
            "Market: 34.5% | Our: 15.5% | Gap: 19pp\n\n"
            "Trade NO: https://dub.sh/pb-x\n\n"
            "Not financial advice."
        ),
        "tweet_3": "We track every call publicly \u2192 https://vpjonny.github.io/probbrain-accuracy/",
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
        "approved_by": "auto-PRO-198",
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
    logger.info("published_signals.json updated for SIG-013")


def paperclip_mark_done(comment: str):
    if not PAPERCLIP_API_URL or not PAPERCLIP_API_KEY:
        logger.warning("Paperclip env vars not set — skipping done update")
        return
    url = f"{PAPERCLIP_API_URL}/api/issues/{PRO_198_ID}"
    headers = {
        "Authorization": f"Bearer {PAPERCLIP_API_KEY}",
        "Content-Type": "application/json",
        "X-Paperclip-Run-Id": PAPERCLIP_RUN_ID,
    }
    payload = {"status": "done", "comment": comment}
    with httpx.Client(timeout=20) as client:
        resp = client.patch(url, json=payload, headers=headers)
        if resp.status_code == 200:
            logger.info("PRO-198 marked done in Paperclip")
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
    logger.info("=== SIG-013 Sweden WC qualifier posting script starting (DRY_RUN=%s) ===", DRY_RUN)

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
    logger.info("Posting SIG-013 to Telegram...")
    if DRY_RUN:
        logger.info("DRY RUN Telegram:\n%s", sig["telegram_copy"])
        tg_result = {"ok": True, "dry_run": True, "result": {"message_id": -1}}
    else:
        tg_result = telegram_send(sig["telegram_copy"])
        logger.info("Telegram OK — message_id=%s", tg_result.get("result", {}).get("message_id"))

    time.sleep(3)

    # X thread
    logger.info("Posting SIG-013 X thread...")
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
    logger.info("SIG-013 posted at %s", posted_at)

    logger.info("Pushing dashboard...")
    if not DRY_RUN:
        push_dashboard()

    summary = (
        "SIG-013 posted to Telegram (@ProbBrain) and X (@ProbBrain).\n\n"
        "**Signal:** Will Sweden qualify for the 2026 FIFA World Cup?\n"
        "**Direction:** NO_UNDERPRICED | **Confidence:** HIGH\n"
        "**Market:** 34.5% YES | **Our estimate:** 15.5% YES | **Gap:** 19pp\n"
        "**Volume:** $131K | **Closes:** 2026-04-12\n\n"
        "Copy reviewed by Content Creator ([PRO-199](/PRO/issues/PRO-199)) "
        "and Twitter Engager ([PRO-200](/PRO/issues/PRO-200)).\n"
        "Content Creator fix applied: 'qualifying final' clarification in Tweet 2.\n"
        "Auto-published (gap < 20pp, approval_required: false).\n\n"
        "Dashboard pushed. Not financial advice."
    )
    if not DRY_RUN:
        paperclip_mark_done(summary)
    else:
        logger.info("DRY RUN — would mark PRO-198 done with:\n%s", summary)

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
