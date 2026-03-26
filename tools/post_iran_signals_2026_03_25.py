"""
Post 2 HIGH signals: Iran conflict ends by Apr 15 and Apr 30.
Sourced from data/scans/2026-03-25-15.json, approved via PRO-119 Approved label.

This script:
1. Sleeps until 30-min gap clears from last post (Edge Thread at 19:33:33 UTC)
2. Posts Signal 5 (Apr 15) to Telegram then X
3. Sleeps 30 min
4. Posts Signal 6 (Apr 30) to Telegram then X
5. Updates data/published_signals.json
6. Pushes dashboard
7. PATCHes PRO-119 to done via Paperclip API

Usage: python tools/post_iran_signals_2026_03_25.py [--dry-run]
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
PRO_119_ID = "27564047-cc47-4261-8295-932fc4d4ee54"

DRY_RUN = "--dry-run" in sys.argv

# Last post timestamp (Edge Thread posted at 19:33:33 UTC)
LAST_POST_UTC = datetime(2026, 3, 25, 19, 33, 33, tzinfo=timezone.utc)
MIN_GAP_SEC = 1800  # 30 minutes

SIGNALS = [
    {
        "signal_number": 5,
        "signal_id": "SIG-005",
        "market_id": "1567746",
        "question": "Iran x Israel/US conflict ends by April 15, 2026?",
        "category": "geopolitics",
        "direction": "NO_UNDERPRICED",
        "confidence": "HIGH",
        "our_estimate": 0.10,
        "market_price_at_signal": 0.295,
        "gap_pct": 19.5,
        "volume_usdc": 814243,
        "close_date": "2026-04-15",
        "paperclip_issue": "PRO-119",
        "evidence": [
            "CNBC March 25 2026: Iran rejected Trump's 15-point peace plan, issued counteroffer demanding Strait of Hormuz sovereignty \u2014 a US non-starter",
            "Euronews March 25 2026: Iran escalated attacks on Israel and Gulf states on the same day as rejecting the plan",
            "Resolution requires 14 consecutive days of zero qualifying military action starting by April 1 \u2014 only 7 days away while both sides are actively escalating",
        ],
        "telegram_copy": (
            "\U0001f534 HIGH \u2014 Bet NO | MARKET SIGNAL\n\n"
            "\U0001f4ca Iran x Israel/US conflict ends by April 15, 2026?\n\n"
            "Market: 29.5% YES | Our estimate: 10% YES\n"
            "Gap: 19.5% (market overpricing YES)\n"
            "Volume: $814k\n"
            "Closes: 2026-04-15\n\n"
            "Evidence:\n"
            "\u2022 CNBC (March 25): Iran rejected Trump\u2019s 15-point peace plan and issued a counteroffer demanding sovereignty over the Strait of Hormuz \u2014 a US non-starter\n"
            "\u2022 Euronews (March 25): Iran escalated attacks on Israel and Gulf states on the same day as rejecting the plan\n"
            "\u2022 Resolution requires 14 consecutive days of zero military action starting by April 1 \u2014 just 7 days away, while both sides are actively escalating\n\n"
            "Counter-evidence: Diplomatic backchannels remain open and surprise ceasefires have occurred in modern conflicts, though they typically require both sides to de-escalate first.\n\n"
            "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
            "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
            "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/"
        ),
        "x_thread_copy": {
            "tweet_1": (
                "Polymarket prices Iran x Israel/US conflict ending by April 15 at 29.5%. "
                "Our estimate: 10%. Iran explicitly rejected the US peace plan today and escalated. "
                "Gap: 19.5pp. [thread]"
            ),
            "tweet_2": (
                "Evidence:\n"
                "\u2022 CNBC March 25: Iran rejected Trump\u2019s 15-point plan, demanded Strait of Hormuz sovereignty \u2014 a US non-starter\n"
                "\u2022 Euronews March 25: Iran escalated attacks on Israel and Gulf states simultaneously with the rejection\n"
                "\u2022 Resolution requires a 14-day zero-action window starting by April 1 \u2014 only 7 days from today\n\n"
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
    },
    {
        "signal_number": 6,
        "signal_id": "SIG-006",
        "market_id": "1567747",
        "question": "Iran x Israel/US conflict ends by April 30, 2026?",
        "category": "geopolitics",
        "direction": "NO_UNDERPRICED",
        "confidence": "HIGH",
        "our_estimate": 0.18,
        "market_price_at_signal": 0.445,
        "gap_pct": 26.5,
        "volume_usdc": 521018,
        "close_date": "2026-04-30",
        "paperclip_issue": "PRO-119",
        "evidence": [
            "Bloomberg March 25 2026: \u201cIran Rejects US Peace Plan in Blow to Efforts to End War\u201d \u2014 counteroffer includes Hormuz sovereignty, reparations, and US base closures",
            "NPR March 25 2026: Iran\u2019s five stated conditions are incompatible with US red lines on every major point",
            "Historical base rate: major US air campaigns rarely end within 5\u20137 weeks when the adversary is issuing escalatory counteroffers",
            "Resolution requires a 14-day zero-action window starting by April 16 \u2014 22 days from today",
        ],
        "telegram_copy": (
            "\U0001f534 HIGH \u2014 Bet NO | MARKET SIGNAL\n\n"
            "\U0001f4ca Iran x Israel/US conflict ends by April 30, 2026?\n\n"
            "Market: 44.5% YES | Our estimate: 18% YES\n"
            "Gap: 26.5% (market overpricing YES)\n"
            "Volume: $521k\n"
            "Closes: 2026-04-30\n\n"
            "Evidence:\n"
            "\u2022 Bloomberg (March 25): \u201cIran Rejects US Peace Plan in Blow to Efforts to End War\u201d \u2014 counteroffer includes Hormuz sovereignty, reparations, and US base closures\n"
            "\u2022 NPR (March 25): Iran\u2019s five stated conditions are incompatible with US red lines on every major point\n"
            "\u2022 Historical base rate: major US air campaigns rarely end within 5\u20137 weeks when the adversary is issuing escalatory counteroffers, not concessions\n"
            "\u2022 Resolution requires a 14-day zero-action window starting by April 16 \u2014 22 days from today\n\n"
            "Counter-evidence: The April 30 window provides 36 days for diplomacy, and opening positions in negotiations often soften once direct talks begin.\n\n"
            "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
            "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
            "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/"
        ),
        "x_thread_copy": {
            "tweet_1": (
                "Polymarket: 44.5% on Iran conflict ending by April 30. "
                "Our estimate: 18%. Iran rejected the US peace plan today with maximalist demands. "
                "Gap: 26.5pp. [thread]"
            ),
            "tweet_2": (
                "Evidence:\n"
                "\u2022 Bloomberg March 25: Iran rejected the US peace plan, demanding Hormuz sovereignty, reparations, and US base closures \u2014 incompatible with US red lines\n"
                "\u2022 Resolution requires a 14-day zero-action window starting by April 16 \u2014 22 days from today\n"
                "\u2022 Historical base rate: major US air campaigns rarely end within 5\u20137 weeks when the adversary is making escalatory counteroffers\n\n"
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
    },
]


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
        "approved_by": "label-approved-PRO-119",
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
    logger.info("published_signals.json updated for signal #%d", sig["signal_number"])


def paperclip_mark_done(comment: str):
    if not PAPERCLIP_API_URL or not PAPERCLIP_API_KEY:
        logger.warning("Paperclip env vars not set — skipping done update")
        return
    url = f"{PAPERCLIP_API_URL}/api/issues/{PRO_119_ID}"
    headers = {
        "Authorization": f"Bearer {PAPERCLIP_API_KEY}",
        "Content-Type": "application/json",
        "X-Paperclip-Run-Id": PAPERCLIP_RUN_ID,
    }
    payload = {"status": "done", "comment": comment}
    with httpx.Client(timeout=20) as client:
        resp = client.patch(url, json=payload, headers=headers)
        if resp.status_code == 200:
            logger.info("PRO-119 marked done in Paperclip")
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


def enforce_gap(last_post: datetime, gap_sec: int):
    now = datetime.now(timezone.utc)
    elapsed = (now - last_post).total_seconds()
    wait = gap_sec - elapsed
    if wait > 0:
        target = datetime.fromtimestamp(last_post.timestamp() + gap_sec, tz=timezone.utc)
        logger.info(
            "Enforcing %d-second gap. Waiting %.0f seconds until %s UTC...",
            gap_sec,
            wait,
            target.strftime("%H:%M:%S"),
        )
        if not DRY_RUN:
            time.sleep(wait)
        else:
            logger.info("DRY RUN — skipping sleep of %.0f seconds", wait)
    else:
        logger.info("Gap already satisfied (%.0f seconds since last post)", elapsed)


def main():
    logger.info("=== Iran signals posting script starting (DRY_RUN=%s) ===", DRY_RUN)

    last_post = LAST_POST_UTC

    for sig in SIGNALS:
        logger.info("--- Signal #%d: %s ---", sig["signal_number"], sig["question"])

        enforce_gap(last_post, MIN_GAP_SEC)

        # Telegram
        logger.info("Posting to Telegram...")
        if DRY_RUN:
            logger.info("DRY RUN Telegram:\n%s", sig["telegram_copy"])
            tg_result = {"ok": True, "dry_run": True, "result": {"message_id": -1}}
        else:
            tg_result = telegram_send(sig["telegram_copy"])
            logger.info("Telegram OK — message_id=%s", tg_result.get("result", {}).get("message_id"))

        time.sleep(3)

        # X thread
        tw = sig["x_thread_copy"]
        logger.info("Posting X thread...")
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

        last_post = datetime.now(timezone.utc)
        logger.info("Signal #%d posted at %s", sig["signal_number"], posted_at)

    logger.info("Pushing dashboard...")
    if not DRY_RUN:
        push_dashboard()

    summary = (
        "Both Iran conflict signals posted.\n\n"
        "- **Signal 5** (Iran conflict ends Apr 15): market 29.5% \u2192 our estimate 10%, gap 19.5pp, HIGH\n"
        "- **Signal 6** (Iran conflict ends Apr 30): market 44.5% \u2192 our estimate 18%, gap 26.5pp, HIGH\n\n"
        "Both posted to Telegram (@ProbBrain) and X (@ProbBrain). Dashboard pushed. "
        "Approved via `Approved` label on [PRO-119](/PRO/issues/PRO-119)."
    )
    if not DRY_RUN:
        paperclip_mark_done(summary)
    else:
        logger.info("DRY RUN — would mark PRO-119 done with:\n%s", summary)

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
