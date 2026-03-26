"""
Post SIG-022: US forces enter Iran by April 30?
Polymarket 63.5% YES vs our estimate 38%. Gap: 25.5pp NO_UNDERPRICED.

CEO approved (Approved label on PRO-183).
Reviewed by:
  - Content Creator (PRO-264): APPROVED
  - Twitter Engager (PRO-265): APPROVED — Tweet 2 condensed from 657→257 chars

Posting to Telegram + X.

Usage: python tools/post_sig022_iran_forces_entry_2026_03_26.py [--dry-run]
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

SIGNAL = {
    "signal_number": 22,
    "signal_id": "SIG-022",
    "market_id": "1640919",
    "question": "US forces enter Iran by April 30?",
    "slug": "us-forces-enter-iran-by-april-30-899",
    "category": "geopolitics",
    "direction": "NO_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.38,
    "market_price_at_signal": 0.635,
    "gap_pct": 25.5,
    "volume_usdc": 3874080,
    "close_date": "2026-04-30",
    "paperclip_issue": "PRO-183",
    "evidence": [
        "White House official, March 26 2026: Trump 'has no current plans to send troops' to Iran — statement issued after 82nd Airborne deployment announced (CNN, CBS, WaPo)",
        "Military expert consensus, AP/WaPo March 24-25 2026: deployed force of ~6,700 troops (82nd Airborne + Marines) 'not sufficient for major invasion nor to hold a single city' — sized for 'limited/targeted ops only'",
        "Iran actively mining and fortifying Kharg Island with MANPADS and anti-armor mines (CNN March 25, BusinessToday March 26) — raising operational cost and risk of any ground entry significantly",
        "Historical base rate: US has NEVER physically entered Iranian sovereign territory in 40+ years of direct conflict and hostility — all 5 prior timeframe markets (Jan 31, Feb 28, Mar 1, Mar 3, Mar 14) resolved NO",
        "March 31 market (5 days away) priced at only 24.5% YES — implies crowd sees entry as unlikely in the near term, making the April 30 jump to 63.5% structurally aggressive",
    ],
    "telegram_copy": (
        "\U0001f534 HIGH — Bet NO | MARKET SIGNAL\n"
        "\n"
        "\U0001f4ca US forces enter Iran by April 30?\n"
        "\n"
        "Market: 63.5% YES | Our estimate: 38% YES\n"
        "Gap: 25.5pp (market overpricing YES)\n"
        "Volume: $3.87M\n"
        "Closes: 2026-04-30\n"
        "\n"
        "Evidence:\n"
        "\u2022 White House March 26: Trump \u201chas no current plans\u201d to send troops to Iran (CNN/CBS/WaPo)\n"
        "\u2022 Military experts: ~6,700-troop force sized for limited ops only, not invasion (AP/WaPo)\n"
        "\u2022 Iran mining and fortifying Kharg Island with MANPADS \u2014 raises operational cost significantly\n"
        "\u2022 Historical base rate: zero US physical entries into Iran in 40+ years; all 5 prior markets resolved NO\n"
        "\u2022 March 31 market at 24.5% YES \u2014 crowd sees near-term entry as unlikely\n"
        "\n"
        "Counter-evidence: Marines and 82nd Airborne are specifically staging for potential Kharg Island seizure, Iran fortifying means they view the threat as credible, and ceasefire talks collapsed March 25.\n"
        "\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n"
        "\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/"
    ),
    "x_thread_copy": {
        "tweet_1": (
            "Polymarket prices US troops entering Iran by April 30 at 63.5%. "
            "White House: \u201cno current plans.\u201d Our estimate: 38%. "
            "Zero historical precedent in 40+ years. Lean NO. [thread]"
        ),
        "tweet_2": (
            "WH: \u201cno current plans\u201d (Mar 26). ~6,700 troops = deterrence, not invasion. "
            "Kharg fortified w/ MANPADS. All 5 prior US/Iran markets: NO. "
            "Zero entries in 40+ yrs.\n"
            "\n"
            "Market: 63.5% | Our: 38% | Gap: 25.5pp\n"
            "\n"
            "Trade NO: https://dub.sh/pb-x Not financial advice."
        ),
        "tweet_3": (
            "We track every call publicly, win or lose.\n"
            "\n"
            "Accuracy dashboard: https://vpjonny.github.io/probbrain-accuracy/\n"
            "\n"
            "Get signals early: https://t.me/ProbBrain\n"
            "\n"
            "Follow @ProbBrain for more threads like this."
        ),
    },
}


def telegram_post(text: str) -> int:
    import urllib.request
    import urllib.parse

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": "true",
    }).encode()
    req = urllib.request.Request(url, data=data)
    resp = urllib.request.urlopen(req)
    result = json.loads(resp.read())
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")
    msg_id = result["result"]["message_id"]
    logger.info("Telegram posted (message_id=%s)", msg_id)
    return msg_id


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
        "approved_by": "CEO-approved-PRO-183",
        "platforms": ["telegram", "x"],
        "telegram_link": "https://dub.sh/pb-tg",
        "x_link": "https://dub.sh/pb-x",
        "x_account": "@ProbBrain",
        "telegram_channel": "@ProbBrain",
        "evidence": sig["evidence"],
        "telegram_copy": sig["telegram_copy"],
        "x_thread_copy": sig["x_thread_copy"],
        "telegram_message_id": tg_msg_id,
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
    logger.info("published_signals.json updated for SIG-022")


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
    logger.info("=== SIG-022 posting script starting (DRY_RUN=%s) ===", DRY_RUN)

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

    # Check daily Telegram count
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_tg = sum(
        1 for p in records
        if p.get("actually_posted_at", "").startswith(today_str)
        and "telegram" in (p.get("platforms") or [])
    )
    logger.info("Telegram signals posted today: %d/5", today_tg)

    sig = SIGNAL
    tw = sig["x_thread_copy"]

    # Validate tweet lengths
    t1_len = len(tw["tweet_1"])
    t2_len = len(tw["tweet_2"])
    t3_len = len(tw["tweet_3"])
    logger.info("Tweet 1: %d chars (limit 200)", t1_len)
    logger.info("Tweet 2: %d chars (limit 280)", t2_len)
    logger.info("Tweet 3: %d chars (limit 280)", t3_len)
    if t1_len > 200:
        logger.error("Tweet 1 exceeds 200 chars — aborting")
        sys.exit(1)
    if t2_len > 280:
        logger.error("Tweet 2 exceeds 280 chars — aborting")
        sys.exit(1)
    if t3_len > 280:
        logger.error("Tweet 3 exceeds 280 chars — aborting")
        sys.exit(1)

    # --- Post Telegram ---
    tg_msg_id = None
    if today_tg >= 5:
        logger.warning("Telegram daily limit reached (%d/5) — skipping Telegram", today_tg)
    else:
        logger.info("Posting SIG-022 to Telegram...")
        if DRY_RUN:
            logger.info("DRY RUN Telegram:\n%s", sig["telegram_copy"])
            tg_msg_id = "dry-tg"
        else:
            tg_msg_id = telegram_post(sig["telegram_copy"])

    # --- Post X thread ---
    logger.info("Posting SIG-022 X thread...")
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
        update_published(sig, tg_msg_id, x_ids, posted_at)
        logger.info("SIG-022 posted at %s", posted_at)
        logger.info("Pushing dashboard...")
        push_dashboard()
    else:
        logger.info("DRY RUN — skipping published_signals.json update and dashboard push")

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
