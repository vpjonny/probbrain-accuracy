"""
Post SIG-027 + SIG-028 + SIG-029: US × Iran ceasefire by April 7 / 15 / 30 (NO_UNDERPRICED)
From 2026-03-27T16:00Z scan (PRO-298).

Content reviewed by Content Creator (PRO-299) and Twitter Engager (PRO-300).
SIG-029 board-approved via Approved label.
Combined X thread per Twitter Engager recommendation.

Usage: python tools/post_sig027_028_029_iran_ceasefire_2026_03_27.py [--dry-run]
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

SIGNAL_027 = {
    "signal_number": 27,
    "signal_id": "SIG-027",
    "market_id": "1706788",
    "question": "US × Iran ceasefire by April 7?",
    "category": "geopolitics",
    "direction": "NO_UNDERPRICED",
    "confidence": "MEDIUM",
    "our_estimate": 0.03,
    "market_price_at_signal": 0.14,
    "gap_pct": 11.0,
    "volume_usdc": 689793,
    "close_date": "2026-04-07",
    "paperclip_issue": "PRO-298",
    "evidence": [
        "Iran rejected US 15-point plan; FM publicly denies peace talks have taken place",
        "Active military escalation: Israel struck IRGC navy commander + Isfahan targets; Iran fired missiles at central Israel",
        "VP Vance chided Netanyahu for overselling regime change",
        "Only 11 days to close; resolution requires mutual public confirmation",
    ],
    "telegram_copy": (
        "\U0001f7e1 MEDIUM \u2014 Lean NO | MARKET SIGNAL\n\n"
        "\U0001f4ca US \u00d7 Iran ceasefire by April 7?\n\n"
        "Market: 14% YES | Our estimate: 3% YES\n"
        "Gap: 11pp (market overpricing YES)\n"
        "Volume: $689k\n"
        "Closes: 2026-04-07\n\n"
        "Evidence:\n"
        "\u2022 Iran rejected US 15-point plan; FM publicly denies peace talks have taken place\n"
        "\u2022 Active military escalation: Israel struck IRGC navy commander + Isfahan targets; Iran fired missiles at central Israel\n"
        "\u2022 VP Vance chided Netanyahu for overselling regime change\n"
        "\u2022 Only 11 days to close; resolution requires mutual public confirmation\n\n"
        "Counter-evidence: Despite reports of a Pakistan-mediated backchannel (Jerusalem Post/WaPo), "
        "Iran publicly refuses to negotiate, making a deal within 11 days extremely unlikely.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/\n"
        "\U0001f426 Follow us on X: https://x.com/ProbBrain"
    ),
}

SIGNAL_028 = {
    "signal_number": 28,
    "signal_id": "SIG-028",
    "market_id": "1569627",
    "question": "US × Iran ceasefire by April 15?",
    "category": "geopolitics",
    "direction": "NO_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.09,
    "market_price_at_signal": 0.285,
    "gap_pct": 19.5,
    "volume_usdc": 5120413,
    "close_date": "2026-04-15",
    "paperclip_issue": "PRO-298",
    "evidence": [
        "Iran rejected US 15-point plan; FM publicly denies any peace talks",
        "Israel struck IRGC navy commander and Isfahan targets; Iran fired missiles at central Israel",
        "VP Vance chided Netanyahu for overselling regime change — limited US diplomatic leverage",
        "Pakistan backchannel confirmed but Iran publicly refuses to negotiate",
    ],
    "telegram_copy": (
        "\U0001f534 HIGH \u2014 Bet NO | MARKET SIGNAL\n\n"
        "\U0001f4ca US \u00d7 Iran ceasefire by April 15?\n\n"
        "Market: 28.5% YES | Our estimate: 9% YES\n"
        "Gap: 19.5pp (market overpricing YES)\n"
        "Volume: $5,120k\n"
        "Closes: 2026-04-15\n\n"
        "Evidence:\n"
        "\u2022 Iran rejected US 15-point plan; FM publicly denies any peace talks\n"
        "\u2022 Israel struck IRGC navy commander and Isfahan targets; Iran fired missiles at central Israel\n"
        "\u2022 VP Vance chided Netanyahu for overselling regime change \u2014 limited US diplomatic leverage\n"
        "\u2022 Pakistan backchannel confirmed but Iran publicly refuses to negotiate\n\n"
        "Counter-evidence: Despite reports of a Pakistan-mediated backchannel (Jerusalem Post/WaPo), "
        "Iran publicly refuses to negotiate, making a ceasefire within 19 days very unlikely.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/\n"
        "\U0001f426 Follow us on X: https://x.com/ProbBrain"
    ),
}

SIGNAL_029 = {
    "signal_number": 29,
    "signal_id": "SIG-029",
    "market_id": "iran-ceasefire-apr30",
    "question": "US × Iran ceasefire by April 30?",
    "category": "geopolitics",
    "direction": "NO_UNDERPRICED",
    "confidence": "HIGH",
    "our_estimate": 0.15,
    "market_price_at_signal": 0.405,
    "gap_pct": 25.5,
    "volume_usdc": 5965869,
    "close_date": "2026-04-30",
    "paperclip_issue": "PRO-298",
    "evidence": [
        "Iran rejected US 15-point plan; FM publicly denies any peace talks",
        "Israel struck IRGC navy commander and Isfahan targets; Iran fired missiles at central Israel",
        "VP Vance chided Netanyahu for overselling regime change",
        "Pakistan backchannel confirmed but Iran publicly refuses to negotiate",
    ],
    "telegram_copy": (
        "\U0001f534 HIGH \u2014 Bet NO | MARKET SIGNAL\n\n"
        "\U0001f4ca US \u00d7 Iran ceasefire by April 30?\n\n"
        "Market: 40.5% YES | Our estimate: 15% YES\n"
        "Gap: 25.5pp (market overpricing YES)\n"
        "Volume: $5,965k\n"
        "Closes: 2026-04-30\n\n"
        "Evidence:\n"
        "\u2022 Iran rejected US 15-point plan; FM publicly denies any peace talks\n"
        "\u2022 Israel struck IRGC navy commander and Isfahan targets; Iran fired missiles at central Israel\n"
        "\u2022 VP Vance chided Netanyahu for overselling regime change\n"
        "\u2022 Pakistan backchannel confirmed but Iran publicly refuses to negotiate\n\n"
        "Counter-evidence: Despite reports of a Pakistan-mediated backchannel (Jerusalem Post/WaPo), "
        "Iran publicly refuses to negotiate. However, the longer April 30 deadline gives slightly more runway "
        "for a diplomatic surprise.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/\n"
        "\U0001f426 Follow us on X: https://x.com/ProbBrain"
    ),
}

# Combined X thread (per Twitter Engager recommendation)
X_THREAD = {
    "tweet_1": (
        "Polymarket: 40.5% chance of US-Iran ceasefire by April 30. "
        "Iran rejected the 15-point plan. FM denies any talks. "
        "Our estimate: 15%. Gap: 25.5pp."
    ),
    "tweet_2": (
        "\u2022 Iran rejected 15-point plan\n"
        "\u2022 FM: 'no peace talks have taken place'\n"
        "\u2022 Pakistan backchannel \u2014 Iran refuses\n"
        "\u2022 Military escalation both sides\n\n"
        "Apr 7: 14%\u21923% | Apr 15: 28.5%\u21929% | Apr 30: 40.5%\u219215%\n\n"
        "Trade NO: https://dub.sh/pb-x\n"
        "Not financial advice."
    ),
    "tweet_3": (
        "If ceasefire doesn't happen by April 7 (our highest-confidence NO at 3%), "
        "April 15 and April 30 become even less likely. Each deadline builds on the last. "
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


def update_published_records(signals_posted, tg_msg_ids, x_ids, posted_at):
    """Remove draft entries for these signals and add final posted entries."""
    records = json.loads(PUBLISHED.read_text())
    # Remove existing draft entries
    sig_ids = {s["signal_id"] for s in signals_posted}
    records = [r for r in records if r.get("signal_id") not in sig_ids]

    for sig, tg_id in zip(signals_posted, tg_msg_ids):
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
            "approved_by": "auto-PRO-298" if sig["gap_pct"] < 20 else "board-approved-PRO-298",
            "platforms": ["telegram", "x"],
            "telegram_link": "https://dub.sh/pb-tg",
            "x_link": "https://dub.sh/pb-x",
            "x_account": "@ProbBrain",
            "telegram_channel": "@ProbBrain",
            "evidence": sig["evidence"],
            "telegram_copy": sig["telegram_copy"],
            "telegram_message_id": tg_id,
            "x_thread_copy": None,
            "x_tweet_ids": None,
            "paperclip_issue": sig["paperclip_issue"],
            "published_at": posted_at,
        }
        # X thread IDs on first signal only (combined thread)
        if sig["signal_id"] == signals_posted[0]["signal_id"] and x_ids:
            entry["x_tweet_ids"] = {f"tweet_{i+1}": tid for i, tid in enumerate(x_ids)}
            entry["x_posted_at"] = posted_at
        records.append(entry)

    PUBLISHED.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    logger.info("published_signals.json updated for %s", ", ".join(s["signal_id"] for s in signals_posted))


def main():
    logger.info("=== SIG-027 + SIG-028 + SIG-029 Iran ceasefire posting (DRY_RUN=%s) ===", DRY_RUN)

    # Validate tweet lengths
    for i, key in enumerate(["tweet_1", "tweet_2", "tweet_3", "tweet_4"]):
        length = len(X_THREAD[key])
        limit = 200 if i == 0 else 280
        logger.info("Tweet %d length: %d chars (limit %d)", i + 1, length, limit)
        if length > limit:
            logger.error("Tweet %d exceeds %d chars (%d) — aborting", i + 1, limit, length)
            sys.exit(1)

    signals = [SIGNAL_027, SIGNAL_028, SIGNAL_029]
    tg_msg_ids = []

    # --- Telegram: Post each signal ---
    for sig in signals:
        logger.info("Posting %s to Telegram...", sig["signal_id"])
        if DRY_RUN:
            logger.info("DRY RUN TG %s:\n%s", sig["signal_id"], sig["telegram_copy"])
            tg_msg_ids.append(f"dry-tg-{sig['signal_number']}")
        else:
            resp = telegram_send(sig["telegram_copy"])
            msg_id = resp.get("result", {}).get("message_id")
            tg_msg_ids.append(msg_id)
            logger.info("TG %s posted (message_id=%s)", sig["signal_id"], msg_id)
        time.sleep(3)

    # --- X: Combined thread ---
    logger.info("Posting combined X thread (SIG-027 + SIG-028 + SIG-029)...")
    tweets = [X_THREAD["tweet_1"], X_THREAD["tweet_2"], X_THREAD["tweet_3"], X_THREAD["tweet_4"]]
    if DRY_RUN:
        for i, t in enumerate(tweets):
            logger.info("DRY RUN Tweet %d: %s", i + 1, t)
        x_ids = ["dry-t1", "dry-t2", "dry-t3", "dry-t4"]
    else:
        x_ids = x_post_thread(tweets)

    posted_at = datetime.now(timezone.utc).isoformat()

    # Update published records (replace drafts with actual post data)
    update_published_records(signals, tg_msg_ids, x_ids, posted_at)

    logger.info("SIG-027 + SIG-028 + SIG-029 posted at %s", posted_at)
    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
