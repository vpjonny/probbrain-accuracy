#!/usr/bin/env python3
"""
SIG-041: U.S. Invasion of Cuba 2026
Properly formatted Telegram + X posting with hard-coded message format.
"""

import os
import json
import httpx
import tweepy
from datetime import datetime

# Load environment
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# Signal data
SIGNAL_ID = "SIG-041"
MARKET_QUESTION = "Will the U.S. invade Cuba in 2026?"
MARKET_PRICE_YES = 23.5
OUR_ESTIMATE_YES = 45.0
GAP_PCT = 21.5
VOLUME_K = 1219  # $1,219k
CLOSE_DATE = "2026-12-31"
POLYMARKET_SLUG = "will-the-us-invade-cuba-in-2026"

# Hard-coded per board feedback
TELEGRAM_MESSAGE = """🟡 MEDIUM — Lean YES

MARKET SIGNAL

📊 Will the U.S. invade Cuba in 2026?

Market: 23.5% YES | Our estimate: 45% YES
Gap: 21.5% (market underpricing YES)
Volume: $1,219k
Closes: 2026-12-31

Evidence:
• Trump admin explicitly stated Cuba is next military target after Venezuela (March 28, 2026)
• Secretary of State Marco Rubio publicly declared objective is 'regime change' (March 2026)

Counter-evidence: Full invasion requires Congressional declaration (politically difficult with midterms 8 months away), logistics/troop mobilization (~6-12 months typical), and international coalition backing (lacking).

🔗 Trade on Polymarket: https://dub.sh/pb-tg

⚠️ Not financial advice. Trade at your own risk.
📈 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/
🐦 Follow us on X: https://x.com/ProbBrain"""

# X thread tweets
TWEET_1 = f"""Market thinks 23.5% chance of U.S. invasion of Cuba in 2026.

Our estimate: 45%

Gap: 21.5% — market underpricing invasion risk given Trump admin's explicit regime-change rhetoric and military positioning. #Polymarket"""

TWEET_2 = f"""Evidence:
• Trump admin stated Cuba is next military target (Mar 28)
• Secretary Rubio declared 'regime change' objective
• U.S. warships positioned; naval ops in Florida Strait

But: Full invasion needs Congressional declaration (tough midterm politics), logistics (6-12 mo), coalition (lacking)

Trade: https://dub.sh/pb-x

⚠️ Not financial advice."""

TWEET_3 = f"""We track every call publicly → https://vpjonny.github.io/probbrain-accuracy/

Get signals on Telegram: https://t.me/ProbBrain

Follow @ProbBrain for more."""

def post_telegram():
    """Post to Telegram with hard-coded format."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": TELEGRAM_MESSAGE,
        "parse_mode": "Markdown"
    }
    resp = httpx.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    msg_id = resp.json()["result"]["message_id"]
    print(f"✓ Telegram posted (message_id={msg_id})")
    return msg_id

def post_twitter():
    """Post X thread with hard-coded tweets."""
    client = tweepy.Client(
        consumer_key=X_CONSUMER_KEY,
        consumer_secret=X_CONSUMER_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )

    r1 = client.create_tweet(text=TWEET_1)
    tid1 = r1.data["id"]
    print(f"✓ X tweet 1 posted (id={tid1})")

    r2 = client.create_tweet(text=TWEET_2, in_reply_to_tweet_id=tid1)
    tid2 = r2.data["id"]
    print(f"✓ X tweet 2 posted (id={tid2})")

    r3 = client.create_tweet(text=TWEET_3, in_reply_to_tweet_id=tid2)
    tid3 = r3.data["id"]
    print(f"✓ X tweet 3 posted (id={tid3})")

    return [tid1, tid2, tid3]

def update_published_signals(telegram_msg_id, x_tweet_ids):
    """Log signal to published_signals.json."""
    with open("data/published_signals.json") as f:
        published = json.load(f)

    entry = {
        "signal_id": SIGNAL_ID,
        "signal_number": 41,
        "market_id": "1107878",
        "question": MARKET_QUESTION,
        "market_price_yes": MARKET_PRICE_YES,
        "our_estimate": OUR_ESTIMATE_YES,
        "gap_pct": GAP_PCT,
        "volume_usdc": 1219171.0790540301,
        "close_date": CLOSE_DATE,
        "confidence": "MEDIUM",
        "direction": "YES_UNDERPRICED",
        "platforms": ["telegram", "x"],
        "telegram_message_id": telegram_msg_id,
        "x_tweet_ids": x_tweet_ids,
        "published_at": datetime.utcnow().isoformat() + "Z",
        "polymarket_slug": POLYMARKET_SLUG
    }

    published.append(entry)
    with open("data/published_signals.json", "w") as f:
        json.dump(published, f, indent=2)

    print(f"✓ Logged to published_signals.json")

if __name__ == "__main__":
    try:
        print(f"Publishing {SIGNAL_ID}: {MARKET_QUESTION}")
        print(f"Gap: {GAP_PCT}% | Confidence: MEDIUM | Needs approval: {GAP_PCT >= 20}")
        print()

        # Post to platforms
        msg_id = post_telegram()
        tweet_ids = post_twitter()

        # Log
        update_published_signals(msg_id, tweet_ids)

        print("\n✓ All systems posted successfully")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
