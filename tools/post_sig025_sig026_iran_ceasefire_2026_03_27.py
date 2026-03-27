"""
Post SIG-025 + SIG-026: US × Iran ceasefire by April 15 / April 7 (NO_UNDERPRICED)
From 2026-03-27T15:00Z scan (PRO-291).

Content reviewed by Content Creator (PRO-292) and Twitter Engager (PRO-293).
Incorporates feedback: softened 'insider' language, added counter-evidence,
combined X thread per Twitter Engager recommendation.

Signal 2 (April 30, approval_required: true) is held for board approval.

Usage: python tools/post_sig025_sig026_iran_ceasefire_2026_03_27.py [--dry-run]
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

SIGNAL_025 = {
    "signal_number": 25,
    "signal_id": "SIG-025",
    "market_id": "1569627",
    "slug": "us-x-iran-ceasefire-by-april-15-182-528-637",
    "question": "US × Iran ceasefire by April 15?",
    "category": "geopolitics",
    "direction": "NO_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.09,
    "market_price_at_signal": 0.275,
    "gap_pct": 18.5,
    "volume_usdc": 5117922,
    "close_date": "2026-04-15",
    "paperclip_issue": "PRO-291",
    "evidence": [
        "Iran rejected US 15-point ceasefire plan, calling it 'maximalist, unreasonable' (Al Jazeera, March 25)",
        "Iran FM: 'no peace talks with the US have taken place' — no plans for negotiations (NBC News)",
        "Pentagon considering 10,000 additional troops — escalation, not de-escalation (PBS)",
        "Unusual positioning on the escalation side in Polymarket betting (Times of Israel)",
        "Resolution requires public confirmation from both govts — no direct talks exist (OPB)",
    ],
    "telegram_copy": (
        "\U0001f534 HIGH \u2014 Bet NO | MARKET SIGNAL\n\n"
        "\U0001f4ca US \u00d7 Iran ceasefire by April 15?\n\n"
        "Market: 27.5% YES | Our estimate: 9% YES\n"
        "Gap: 18.5pp (market overpricing YES)\n"
        "Volume: $5.1M\n"
        "Closes: 2026-04-15\n\n"
        "Evidence:\n"
        "\u2022 Iran rejected US 15-point ceasefire plan, calling it \u201cmaximalist, unreasonable\u201d (Al Jazeera)\n"
        "\u2022 Iran FM: \u201cno peace talks with the US have taken place\u201d (NBC News)\n"
        "\u2022 Pentagon considering 10,000 additional troops \u2014 escalation, not de-escalation (PBS)\n"
        "\u2022 Unusual positioning on the escalation side in Polymarket betting (Times of Israel)\n"
        "\u2022 Resolution requires public confirmation from both govts \u2014 no direct talks exist\n\n"
        "Counter-evidence: Diplomatic channels could reopen quickly via indirect mediators; "
        "our estimate accounts for this low-probability path.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/\n"
        "\U0001f426 Follow us on X: https://x.com/ProbBrain"
    ),
}

SIGNAL_026 = {
    "signal_number": 26,
    "signal_id": "SIG-026",
    "market_id": "1706788",
    "slug": "us-x-iran-ceasefire-by-april-7-278",
    "question": "US × Iran ceasefire by April 7?",
    "category": "geopolitics",
    "direction": "NO_UNDERPRICED",
    "confidence": "MEDIUM",
    "our_estimate": 0.03,
    "market_price_at_signal": 0.135,
    "gap_pct": 10.5,
    "volume_usdc": 688288,
    "close_date": "2026-04-07",
    "paperclip_issue": "PRO-291",
    "evidence": [
        "Iran rejected US ceasefire plan 2 days ago; FM denies any talks occurring (Al Jazeera, NBC News)",
        "Trump's energy strike pause deadline expires April 6 — Iran has not engaged (NPR)",
        "Only 11 days to close; resolution requires mutual public confirmation from both govts",
    ],
    "telegram_copy": (
        "\U0001f7e1 MEDIUM \u2014 Lean NO | MARKET SIGNAL\n\n"
        "\U0001f4ca US \u00d7 Iran ceasefire by April 7?\n\n"
        "Market: 13.5% YES | Our estimate: 3% YES\n"
        "Gap: 10.5pp (market overpricing YES)\n"
        "Volume: $688k\n"
        "Closes: 2026-04-07\n\n"
        "Evidence:\n"
        "\u2022 Iran rejected US ceasefire plan 2 days ago; FM denies any talks occurring (Al Jazeera, NBC News)\n"
        "\u2022 Trump\u2019s energy strike pause deadline expires April 6 \u2014 Iran has not engaged (NPR)\n"
        "\u2022 Only 11 days to close; resolution requires mutual public confirmation from both govts\n\n"
        "Counter-evidence: Trump\u2019s deadline extension shows some willingness to pause, "
        "though Iran has not reciprocated.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/\n"
        "\U0001f426 Follow us on X: https://x.com/ProbBrain"
    ),
}

# Combined X thread for both signals (per Twitter Engager recommendation)
X_THREAD = {
    "tweet_1": (
        "Polymarket: 27.5% chance of US-Iran ceasefire by April 15. "
        "Iran just rejected the 15-point plan. FM: 'no talks.' "
        "Our estimate: 9%. Gap: 18.5pp."
    ),
    "tweet_2": (
        "Why market overprices ceasefire:\n\n"
        "\u2022 Iran rejected 15-point plan ('maximalist')\n"
        "\u2022 FM: 'no peace talks have taken place'\n"
        "\u2022 Pentagon: 10K more troops\n"
        "\u2022 No direct talks exist\n\n"
        "Apr 7: 13.5% \u2192 3% | Apr 15: 27.5% \u2192 9%\n\n"
        "Trade NO: https://dub.sh/pb-x\n"
        "Not financial advice."
    ),
    "tweet_3": (
        "If ceasefire doesn't happen by April 7 (our highest-confidence NO at 3%), "
        "April 15 becomes even less likely. Each deadline builds on the last. "
        "The market is pricing hope, not evidence."
    ),
    "tweet_4": (
        "We track every call publicly.\n"
        "Accuracy dashboard: https://vpjonny.github.io/probbrain-accuracy/\n\n"
        "Join us on Telegram: https://t.me/ProbBrain\n"
        "Follow @ProbBrain for more signals."
    ),
}


def telegram_send(text: str) -> dict:
    url = f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "parse_mode": "Markdown"}
    r = httpx.post(url, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


def x_post_thread(tweets: list[str]) -> list[str]:
    client = tweepy.Client(
        consumer_key=os.getenv("X_CONSUMER_KEY", "").strip(),
        consumer_secret=os.getenv("X_CONSUMER_SECRET", "").strip(),
        access_token=os.getenv("X_ACCESS_TOKEN", "").strip(),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET", "").strip(),
    )
    ids = []
    prev_id = None
    for i, text in enumerate(tweets):
        kwargs = {"text": text}
        if prev_id:
            kwargs["in_reply_to_tweet_id"] = prev_id
        r = client.create_tweet(**kwargs)
        tid = str(r.data["id"])
        ids.append(tid)
        prev_id = tid
        logger.info("X tweet %d posted (id=%s)", i + 1, tid)
        if i < len(tweets) - 1:
            time.sleep(2)
    return ids


def update_published(sig: dict, tg_msg_id, x_ids: list, posted_at: str, platforms: list):
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
        "approved_by": "auto-PRO-291",
        "platforms": platforms,
        "telegram_link": "https://dub.sh/pb-tg",
        "x_link": "https://dub.sh/pb-x",
        "x_account": "@ProbBrain",
        "telegram_channel": "@ProbBrain",
        "evidence": sig["evidence"],
        "telegram_copy": sig["telegram_copy"],
        "telegram_message_id": tg_msg_id,
        "x_thread_copy": None,  # combined thread, set on SIG-025
        "x_tweet_ids": None,
        "paperclip_issue": sig["paperclip_issue"],
        "actually_posted_at": posted_at,
    }
    if x_ids:
        entry["x_tweet_ids"] = {
            f"tweet_{i+1}": tid for i, tid in enumerate(x_ids)
        }
    records.append(entry)
    PUBLISHED.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    logger.info("published_signals.json updated for %s", sig["signal_id"])


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
    logger.info("=== SIG-025 + SIG-026 Iran ceasefire posting script (DRY_RUN=%s) ===", DRY_RUN)

    # Validate tweet lengths
    for i, key in enumerate(["tweet_1", "tweet_2", "tweet_3", "tweet_4"]):
        length = len(X_THREAD[key])
        limit = 200 if i == 0 else 280
        logger.info("Tweet %d length: %d chars (limit %d)", i + 1, length, limit)
        if length > limit:
            logger.error("Tweet %d exceeds %d chars (%d) — aborting", i + 1, limit, length)
            sys.exit(1)

    # --- Telegram: SIG-025 (April 15) ---
    logger.info("Posting SIG-025 to Telegram...")
    tg_msg_id_025 = None
    if DRY_RUN:
        logger.info("DRY RUN TG SIG-025:\n%s", SIGNAL_025["telegram_copy"])
        tg_msg_id_025 = "dry-tg-025"
    else:
        resp = telegram_send(SIGNAL_025["telegram_copy"])
        tg_msg_id_025 = resp.get("result", {}).get("message_id")
        logger.info("TG SIG-025 posted (message_id=%s)", tg_msg_id_025)

    time.sleep(3)

    # --- Telegram: SIG-026 (April 7) ---
    logger.info("Posting SIG-026 to Telegram...")
    tg_msg_id_026 = None
    if DRY_RUN:
        logger.info("DRY RUN TG SIG-026:\n%s", SIGNAL_026["telegram_copy"])
        tg_msg_id_026 = "dry-tg-026"
    else:
        resp = telegram_send(SIGNAL_026["telegram_copy"])
        tg_msg_id_026 = resp.get("result", {}).get("message_id")
        logger.info("TG SIG-026 posted (message_id=%s)", tg_msg_id_026)

    time.sleep(3)

    # --- X: Combined thread ---
    logger.info("Posting combined X thread (SIG-025 + SIG-026)...")
    tweets = [X_THREAD["tweet_1"], X_THREAD["tweet_2"], X_THREAD["tweet_3"], X_THREAD["tweet_4"]]
    if DRY_RUN:
        for i, t in enumerate(tweets):
            logger.info("DRY RUN Tweet %d: %s", i + 1, t)
        x_ids = ["dry-t1", "dry-t2", "dry-t3", "dry-t4"]
    else:
        x_ids = x_post_thread(tweets)

    posted_at = datetime.now(timezone.utc).isoformat()

    # Log SIG-025 with X thread info
    update_published(SIGNAL_025, tg_msg_id_025, x_ids, posted_at, ["telegram", "x"])
    # Log SIG-026 with TG only (X thread is combined, logged under SIG-025)
    update_published(SIGNAL_026, tg_msg_id_026, [], posted_at, ["telegram", "x"])

    logger.info("SIG-025 + SIG-026 posted at %s", posted_at)

    if not DRY_RUN:
        logger.info("Pushing dashboard...")
        push_dashboard()

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
