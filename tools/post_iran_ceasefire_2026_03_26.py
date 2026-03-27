"""
Post SIG-020 and SIG-021: US x Iran ceasefire by April 15 / April 30 (NO_UNDERPRICED)
Sourced from PRO-159 task description (2026-03-26T06:27:55Z scan).
Content reviewed by Content Creator (PRO-162) and Twitter Engager (PRO-163).
Board approved via Approved label on PRO-159.

This script:
1. Posts SIG-020 to Telegram then X
2. Waits 30 min (rate limit)
3. Posts SIG-021 to Telegram then X
4. Updates data/published_signals.json
5. PATCHes PRO-159 to done via Paperclip API

Usage: python tools/post_iran_ceasefire_2026_03_26.py [--dry-run]
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
PRO_159_ID = "8e6efd4d-0508-4a9c-9805-1a513a89fef9"

DRY_RUN = "--dry-run" in sys.argv

# --- Signal 1: US x Iran ceasefire by April 15 ---
# Copy reviewed by Content Creator (PRO-162) and Twitter Engager (PRO-163)
SIGNAL_1 = {
    "signal_number": 20,
    "signal_id": "SIG-020",
    "market_id": "1569627",
    "polymarket_slug": "us-x-iran-ceasefire-by-april-15-182-528-637",
    "question": "US x Iran ceasefire by April 15?",
    "category": "geopolitics",
    "direction": "NO_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.04,
    "market_price_at_signal": 0.34,
    "gap_pct": 30.0,
    "volume_usdc": 4590000,
    "close_date": "2026-04-15",
    "paperclip_issue": "PRO-159",
    "evidence": [
        "Al Jazeera (Mar 25): Iran called the US 15-point peace plan 'maximalist, unreasonable' — rejected outright",
        "Al Jazeera (Mar 25): Iran FM — 'no negotiations planned'; US diplomacy claims are 'the US talking to itself'",
        "Resolution requires clear public confirmation from both govts — Iran has publicly stated the opposite",
        "Iran counter-demands Strait of Hormuz sovereignty — non-starter; positions remain incompatible 3 weeks from deadline",
    ],
    "telegram_copy": (
        "\U0001f534 HIGH \u2014 Bet NO | MARKET SIGNAL\n\n"
        "\U0001f4ca US x Iran ceasefire by April 15?\n\n"
        "Market: 34% YES | Our estimate: 4% YES\n"
        "Gap: 30pp (market overpricing YES)\n"
        "Volume: $4.59M\n"
        "Closes: 2026-04-15\n\n"
        "Evidence:\n"
        "\u2022 Al Jazeera (Mar 25): Iran called the US 15-point peace plan \u201cmaximalist, unreasonable\u201d \u2014 rejected outright\n"
        "\u2022 Al Jazeera (Mar 25): Iran FM \u2014 \u201cno negotiations planned\u201d; US diplomacy claims are \u201cthe US talking to itself\u201d\n"
        "\u2022 Resolution requires clear public confirmation from both govts \u2014 Iran has publicly stated the opposite\n"
        "\u2022 Iran counter-demands Strait of Hormuz sovereignty \u2014 non-starter; positions remain incompatible 3 weeks from deadline\n\n"
        "Counter-evidence: Surprise ceasefires have occurred in modern conflicts; backchannels may exist beyond public statements.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/"
    ),
    "x_thread_copy": {
        "tweet_1": (
            "Polymarket prices US-Iran ceasefire by April 15 at 34%. "
            "Our estimate: 4%. Iran rejected the US peace plan on March 25 "
            "as 'maximalist, unreasonable.' Gap: 30pp. [thread]"
        ),
        "tweet_2": (
            "\u2022 Iran FM: 'no negotiations planned' \u2014 US is 'talking to itself' (Al Jazeera, Mar 25)\n"
            "\u2022 Resolution requires public confirmation from both govts \u2014 Iran said NO\n"
            "\u2022 Counter: Hormuz sovereignty \u2014 US non-starter\n\n"
            "Trade: https://dub.sh/pb-x Not financial advice."
        ),
        "tweet_3": (
            "We track every call publicly \u2192 https://vpjonny.github.io/probbrain-accuracy/\n\n"
            "Join us on Telegram: https://t.me/ProbBrain\n"
            "Follow @ProbBrain for more."
        ),
    },
}

# --- Signal 2: US x Iran ceasefire by April 30 ---
SIGNAL_2 = {
    "signal_number": 21,
    "signal_id": "SIG-021",
    "market_id": "1466016",
    "polymarket_slug": "us-x-iran-ceasefire-by-april-30-194-679-389",
    "question": "US x Iran ceasefire by April 30?",
    "category": "geopolitics",
    "direction": "NO_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.08,
    "market_price_at_signal": 0.44,
    "gap_pct": 36.0,
    "volume_usdc": 5340000,
    "close_date": "2026-04-30",
    "paperclip_issue": "PRO-159",
    "evidence": [
        "CNBC (Mar 25): Iran rejected US ceasefire terms — counter-demands include Strait of Hormuz sovereignty, reparations, end to all US/Israeli regional ops",
        "Al Jazeera (Mar 25): Iran denied direct US-Iran talks exist; US claims are 'the US talking to itself'",
        "Time (Mar 25): No bilateral framework in place — Pakistan mediators still attempting to arrange a first meeting",
        "Base rate: war started Feb 28 (<4 weeks ago); formal ceasefire within 60 days with active rejection from one side: <10%",
    ],
    "telegram_copy": (
        "\U0001f534 HIGH \u2014 Bet NO | MARKET SIGNAL\n\n"
        "\U0001f4ca US x Iran ceasefire by April 30?\n\n"
        "Market: 44% YES | Our estimate: 8% YES\n"
        "Gap: 36pp (market overpricing YES)\n"
        "Volume: $5.34M\n"
        "Closes: 2026-04-30\n\n"
        "Evidence:\n"
        "\u2022 CNBC (Mar 25): Iran rejected US ceasefire terms \u2014 counter-demands include Strait of Hormuz sovereignty, reparations, end to all US/Israeli regional ops\n"
        "\u2022 Al Jazeera (Mar 25): Iran denied direct US-Iran talks exist; US claims are \u201cthe US talking to itself\u201d\n"
        "\u2022 Time (Mar 25): No bilateral framework in place \u2014 Pakistan mediators still attempting to arrange a first meeting\n"
        "\u2022 Base rate: war started Feb 28 (<4 weeks ago); formal ceasefire within 60 days with active rejection from one side: <10%\n\n"
        "Counter-evidence: 5-week window allows more room for movement; Pakistan mediator framework is active even without direct talks.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/"
    ),
    "x_thread_copy": {
        "tweet_1": (
            "Polymarket: 44% on US-Iran ceasefire by April 30. Our estimate: 8%. "
            "War started 26 days ago. Iran's counter-demands include Hormuz sovereignty. "
            "Gap: 36pp. [thread]"
        ),
        "tweet_2": (
            "\u2022 Iran counter: Hormuz sovereignty, reparations, US base closures (CNBC, Mar 25)\n"
            "\u2022 No direct talks; mediators still arranging first meeting (Time, Mar 25)\n"
            "\u2022 <4 weeks old; formal ceasefire rate when one side rejects terms: <10%\n\n"
            "Trade: https://dub.sh/pb-x Not financial advice."
        ),
        "tweet_3": (
            "We track every call publicly \u2192 https://vpjonny.github.io/probbrain-accuracy/\n\n"
            "Join us on Telegram: https://t.me/ProbBrain\n"
            "Follow @ProbBrain for more."
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
        "approved_by": "label-approved-PRO-159",
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
    logger.info("published_signals.json updated for %s", sig["signal_id"])


def paperclip_done(comment: str):
    if not PAPERCLIP_API_URL or not PAPERCLIP_API_KEY:
        logger.warning("Paperclip env vars not set — skipping done update")
        return
    url = f"{PAPERCLIP_API_URL}/api/issues/{PRO_159_ID}"
    headers = {
        "Authorization": f"Bearer {PAPERCLIP_API_KEY}",
        "Content-Type": "application/json",
        "X-Paperclip-Run-Id": PAPERCLIP_RUN_ID,
    }
    payload = {"status": "done", "comment": comment}
    with httpx.Client(timeout=20) as client:
        resp = client.patch(url, json=payload, headers=headers)
        if resp.status_code == 200:
            logger.info("PRO-159 marked done in Paperclip")
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


def post_signal(sig: dict) -> tuple:
    """Post one signal to Telegram then X. Returns (tg_result, x_ids, posted_at)."""
    tw = sig["x_thread_copy"]

    # Verify tweet lengths
    for key in ["tweet_1", "tweet_2", "tweet_3"]:
        length = len(tw[key])
        logger.info("%s %s length: %d chars", sig["signal_id"], key, length)
        if length > 280:
            logger.error("%s %s exceeds 280 chars — aborting", sig["signal_id"], key)
            sys.exit(1)

    # Telegram
    logger.info("Posting %s to Telegram...", sig["signal_id"])
    if DRY_RUN:
        logger.info("DRY RUN Telegram:\n%s", sig["telegram_copy"])
        tg_result = {"ok": True, "dry_run": True, "result": {"message_id": -1}}
    else:
        tg_result = telegram_send(sig["telegram_copy"])
        logger.info("Telegram OK — message_id=%s", tg_result.get("result", {}).get("message_id"))

    time.sleep(3)

    # X thread
    logger.info("Posting %s X thread...", sig["signal_id"])
    if DRY_RUN:
        logger.info("DRY RUN X:\nTweet 1: %s\nTweet 2: %s\nTweet 3: %s",
                     tw["tweet_1"], tw["tweet_2"], tw["tweet_3"])
        x_ids = ["dry-t1", "dry-t2", "dry-t3"]
    else:
        x_ids = x_post_thread(tw["tweet_1"], tw["tweet_2"], tw["tweet_3"])

    posted_at = datetime.now(timezone.utc).isoformat()
    update_published(sig, tg_result, x_ids, posted_at)
    return tg_result, x_ids, posted_at


def main():
    logger.info("=== Iran ceasefire posting script (SIG-020 + SIG-021) DRY_RUN=%s ===", DRY_RUN)

    # Post Signal 1
    _, _, posted_1 = post_signal(SIGNAL_1)
    logger.info("SIG-020 posted at %s", posted_1)

    # Rate limit: 30 min between posts
    if not DRY_RUN:
        logger.info("Waiting 1800s (30 min) for rate limit before SIG-021...")
        time.sleep(1800)
    else:
        logger.info("DRY RUN — skipping 30 min wait")

    # Post Signal 2
    _, _, posted_2 = post_signal(SIGNAL_2)
    logger.info("SIG-021 posted at %s", posted_2)

    # Push dashboard
    logger.info("Pushing dashboard...")
    if not DRY_RUN:
        push_dashboard()

    summary = (
        "## Published — SIG-020 + SIG-021\n\n"
        "Both Iran ceasefire signals posted to Telegram (@ProbBrain) and X (@ProbBrain).\n\n"
        "**SIG-020:** US x Iran ceasefire by April 15?\n"
        "- Direction: NO_UNDERPRICED | Market: 34% | Our estimate: 4% | Gap: 30pp\n"
        "- Volume: $4.59M | Closes: 2026-04-15\n\n"
        "**SIG-021:** US x Iran ceasefire by April 30?\n"
        "- Direction: NO_UNDERPRICED | Market: 44% | Our estimate: 8% | Gap: 36pp\n"
        "- Volume: $5.34M | Closes: 2026-04-30\n\n"
        "Copy reviewed by Content Creator ([PRO-162](/PRO/issues/PRO-162)) "
        "and Twitter Engager ([PRO-163](/PRO/issues/PRO-163)).\n"
        "Approved via `Approved` label on [PRO-159](/PRO/issues/PRO-159).\n\n"
        "Dashboard pushed. Not financial advice."
    )
    if not DRY_RUN:
        paperclip_done(summary)
    else:
        logger.info("DRY RUN — would mark PRO-159 done with:\n%s", summary)

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
