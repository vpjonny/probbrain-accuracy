#!/usr/bin/env python3
"""
Publish SIG-044: Houthi strike on Israel by March 31, 2026
Direction: NO_UNDERPRICED (we estimate 10%, market at 18.1%)
"""

import argparse
import os
import sys
import json
import httpx
import tweepy
from datetime import datetime, timezone

# Add tools dir to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from posting_utils import should_post_to_platform

# Load config
with open("/home/slova/ProbBrain/config/publisher.json", "r") as f:
    config = json.load(f)

# Signal data
signal = {
    "signal_id": "SIG-044",
    "market_question": "Houthi strike on Israel by March 31, 2026?",
    "market_price_yes": 18.1,
    "our_estimate_yes": 10,
    "confidence": "MEDIUM",
    "volume": "$620k",  # from market data
    "closes": "2026-03-31",
    "evidence": [
        "Active Iran-Israel military escalation ongoing as of March 25 per Polymarket data",
        "Iran fired missiles at central Israel; Israel struck IRGC targets (Operation Epic Fury, Feb 28-present)",
        "Houthis are Iranian proxy but operate with some independence; pattern shows ~15-25% base rate of strikes in active conflict",
        "Two-day window (March 29-31) is short for major coordinated action; most escalatory moves likely already occurred",
        "Market at 18.1% seems reasonable but slightly overweights proxy risk given fatigue from failed ceasefire talks"
    ],
    "counter_evidence": "Proxies have struck unexpectedly in past windows; regional volatility could shift baseline within 48 hours.",
    "gap_pct": 8.1,
    "approval_required": False,
    "approved": True
}

# ===== TELEGRAM MESSAGE =====
telegram_msg = f"""🔴 MARKET SIGNAL

📊 Houthi strike on Israel by March 31, 2026?

Market: 18.1% YES | Our estimate: 10% YES

Gap: 8.1% (market overpriced on YES)

Volume: {signal['volume']}

Closes: {signal['closes']}

Evidence:

• {signal['evidence'][0]}

• {signal['evidence'][1]}

• {signal['evidence'][2]}

Counter-evidence: {signal['counter_evidence']}

🔗 Trade on Polymarket: {config['affiliate_link_telegram']}

⚠️ Not financial advice. Trade at your own risk.

📈 Accuracy track record: {config['dashboard_url']}

🐦 Follow us on X: https://x.com/ProbBrain"""

# ===== X THREAD =====
# Tweet 1: Hook with gap
tweet_1 = f"Houthi strike on Israel by March 31? Market prices 18.1% YES, but our base rate analysis says 10%. 48 hours left."

# Tweet 2: Evidence + affiliate link
tweet_2 = f"""Why we lean NO:

• Active escalation (Iran-IRGC strikes Feb 28+), but pattern shows ~15-25% base rate in active conflict
• 48-hour window is short for major coordinated proxy action
• Market slightly overweights proxy risk given ceasefire fatigue

Trade: {config['affiliate_link_twitter']}

Not financial advice. Trade at own risk."""

# Tweet 3: Dashboard + join/follow
tweet_3 = f"""We track every call publicly → {config['dashboard_url']}

Get signals on Telegram: https://t.me/ProbBrain

Follow @ProbBrain for more."""

SIGNAL_ID = signal["signal_id"]
PUBLISHED_PATH = "/home/slova/ProbBrain/data/published_signals.json"


def post_telegram_msg():
    """Post to Telegram. Returns message_id."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")

    if not bot_token or not channel_id:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": channel_id, "text": telegram_msg, "parse_mode": "Markdown"}
    resp = httpx.post(url, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"Telegram error: {resp.status_code} {resp.text}")
        sys.exit(1)

    tg_data = resp.json()
    msg_id = tg_data.get("result", {}).get("message_id")
    print(f"  ✓ Telegram posted (message_id: {msg_id})")
    return msg_id


def post_x_thread():
    """Post thread to X. Returns list of tweet IDs."""
    client = tweepy.Client(
        consumer_key=os.getenv("X_CONSUMER_KEY"),
        consumer_secret=os.getenv("X_CONSUMER_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    )

    r1 = client.create_tweet(text=tweet_1)
    tweet_1_id = r1.data["id"]
    print(f"  ✓ Tweet 1 posted (id: {tweet_1_id})")

    r2 = client.create_tweet(text=tweet_2, in_reply_to_tweet_id=tweet_1_id)
    tweet_2_id = r2.data["id"]
    print(f"  ✓ Tweet 2 posted (id: {tweet_2_id})")

    r3 = client.create_tweet(text=tweet_3, in_reply_to_tweet_id=tweet_2_id)
    tweet_3_id = r3.data["id"]
    print(f"  ✓ Tweet 3 posted (id: {tweet_3_id})")

    return [tweet_1_id, tweet_2_id, tweet_3_id]


def log_published(telegram_message_id, x_tweet_ids):
    """Log to published_signals.json"""
    with open(PUBLISHED_PATH, "r") as f:
        published = json.load(f)

    published_entry = {
        "signal_id": signal["signal_id"],
        "market_question": signal["market_question"],
        "our_estimate": signal["our_estimate_yes"],
        "market_price": signal["market_price_yes"],
        "gap_pct": signal["gap_pct"],
        "confidence": signal["confidence"],
        "closes": signal["closes"],
        "telegram_message_id": telegram_message_id,
        "x_tweet_ids": x_tweet_ids,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "platforms": ["telegram", "x"],
        "approval_required": signal["approval_required"]
    }

    published.append(published_entry)
    with open(PUBLISHED_PATH, "w") as f:
        json.dump(published, f, indent=2)

    print(f"  ✓ Logged to published_signals.json")


def main():
    parser = argparse.ArgumentParser(description=f"Publish {SIGNAL_ID}")
    parser.add_argument("--force", action="store_true", help="Force re-post even if already published (override dedup)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"{SIGNAL_ID} Publishing Script")
    print(f"{'='*60}\n")

    # Dedup checks
    skip_telegram = False
    skip_x = False
    if not args.force:
        if not should_post_to_platform(SIGNAL_ID, "telegram", PUBLISHED_PATH):
            print(f"[Dedup] SKIP Telegram — {SIGNAL_ID} already posted to Telegram. Use --force to override.")
            skip_telegram = True
        if not should_post_to_platform(SIGNAL_ID, "x", PUBLISHED_PATH):
            print(f"[Dedup] SKIP X — {SIGNAL_ID} already posted to X. Use --force to override.")
            skip_x = True
        if skip_telegram and skip_x:
            print(f"\n[Dedup] {SIGNAL_ID} already published to all platforms. Nothing to do.")
            sys.exit(0)
    else:
        print(f"[Dedup] --force flag set, skipping dedup checks.")

    # Post to platforms
    telegram_message_id = None
    x_tweet_ids = None

    print(f"\n[Posting] Publishing to platforms...")
    if not skip_telegram:
        telegram_message_id = post_telegram_msg()
    else:
        print(f"  [Telegram] Skipped (already posted)")

    if not skip_x:
        try:
            x_tweet_ids = post_x_thread()
        except Exception as e:
            print(f"X error: {e}")
            sys.exit(1)
    else:
        print(f"  [X] Skipped (already posted)")

    # Log to published_signals.json
    if telegram_message_id and x_tweet_ids:
        log_published(telegram_message_id, x_tweet_ids)

    # Sync dashboard
    print("[Dashboard] Syncing...")
    os.system(f"python3 /home/slova/ProbBrain/tools/sync_dashboard.py --signal-id {SIGNAL_ID}")

    print(f"\n{'='*60}")
    print(f"✓ {SIGNAL_ID} publishing complete!")
    if telegram_message_id:
        print(f"  Telegram: {telegram_message_id}")
    if x_tweet_ids:
        print(f"  X thread: {x_tweet_ids[0]}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
