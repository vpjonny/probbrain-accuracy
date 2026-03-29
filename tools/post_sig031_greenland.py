#!/usr/bin/env python3
"""
Post SIG-031 (Greenland acquisition) to Telegram and X
"""
import os
import sys
import httpx
import json
from datetime import datetime
from pathlib import Path

# Load .env file
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key] = val

# Config
CONFIG = {
    "telegram_bot_token": os.getenv("TELEGRAM_BOT_TOKEN"),
    "telegram_channel_id": os.getenv("TELEGRAM_CHANNEL_ID"),
    "x_consumer_key": os.getenv("X_CONSUMER_KEY"),
    "x_consumer_secret": os.getenv("X_CONSUMER_SECRET"),
    "x_access_token": os.getenv("X_ACCESS_TOKEN"),
    "x_access_token_secret": os.getenv("X_ACCESS_TOKEN_SECRET"),
}

# Verify all env vars are set
for key, val in CONFIG.items():
    if not val:
        print(f"✗ Missing env var: {key}", file=sys.stderr)
        sys.exit(1)

# Signal data
SIGNAL = {
    "signal_id": "SIG-031",
    "market_question": "Will the US acquire any part of Greenland in 2026?",
    "market_price_yes": 16.5,
    "our_estimate_yes": 5,
    "gap_pp": 11.5,
    "volume_millions": 9.1,
    "close_date": "2026-12-31",
    "confidence": "HIGH",
    "polymarket_slug": "will-the-us-acquire-any-part-of-greenland-in-2026",
    "affiliate_telegram": "https://dub.sh/pb-tg",
    "affiliate_x": "https://dub.sh/pb-x",
    "dashboard_url": "https://vpjonny.github.io/probbrain-accuracy/",
}

# Telegram message
TELEGRAM_MESSAGE = f"""🔴 HIGH CONFIDENCE — Bet NO

📊 {SIGNAL['market_question']}

Market: {SIGNAL['market_price_yes']}% YES | Our estimate: {SIGNAL['our_estimate_yes']}% YES

Gap: {SIGNAL['gap_pp']}pp (market overpricing YES)

Volume: ${SIGNAL['volume_millions']}M

Closes: {SIGNAL['close_date']}

Evidence:
• Greenland Ministry explicitly rejects sale/cession discussions
• Denmark reaffirms Greenland autonomy; no active negotiations
• Zero post-WWII precedent for NATO ally territory acquisition
• Greenland's trajectory is toward independence, not union

Counter-evidence: Market may be pricing in Trump administration negotiation attempts we've underweighted.

🔗 Trade on Polymarket: {SIGNAL['affiliate_telegram']}

⚠️ Not financial advice. Trade at your own risk.

📈 Accuracy track record: {SIGNAL['dashboard_url']}

🐦 Follow us on X: https://x.com/ProbBrain"""

# X thread tweets
X_TWEET_1 = f"""US Greenland acquisition: market prices {SIGNAL['market_price_yes']}% YES, we estimate {SIGNAL['our_estimate_yes']}%. Nine months left in 2026, zero NATO precedent, Greenland wants independence—not annexation. We're betting NO. {SIGNAL['affiliate_x']}"""

X_TWEET_2 = f"""Evidence:
• Greenland Ministry rejects cession talks
• Denmark reaffirms autonomy
• Zero post-WWII precedent for NATO territory acquisition
• Only 9 months til close

Counter: market may price Trump negotiation attempts higher.

⚠️ Not financial advice. Trade: {SIGNAL['affiliate_x']}"""

X_TWEET_3 = f"""We track every call publicly: {SIGNAL['dashboard_url']}

Get signals on Telegram: https://t.me/ProbBrain

Follow @ProbBrain for more market calls."""

def post_telegram():
    """Post to Telegram"""
    url = f"https://api.telegram.org/bot{CONFIG['telegram_bot_token']}/sendMessage"
    payload = {
        "chat_id": CONFIG["telegram_channel_id"],
        "text": TELEGRAM_MESSAGE,
        "parse_mode": "Markdown",
    }
    resp = httpx.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    msg_id = resp.json()["result"]["message_id"]
    print(f"✓ Telegram posted: message_id={msg_id}")
    return msg_id

def post_x():
    """Post X thread using tweepy"""
    try:
        import tweepy
    except ImportError:
        print("⚠ tweepy not installed, skipping X post")
        return None

    client = tweepy.Client(
        consumer_key=CONFIG["x_consumer_key"],
        consumer_secret=CONFIG["x_consumer_secret"],
        access_token=CONFIG["x_access_token"],
        access_token_secret=CONFIG["x_access_token_secret"],
    )

    # Post thread
    r1 = client.create_tweet(text=X_TWEET_1)
    tweet_1_id = r1.data["id"]
    print(f"✓ X tweet 1 posted: {tweet_1_id}")

    r2 = client.create_tweet(text=X_TWEET_2, in_reply_to_tweet_id=tweet_1_id)
    tweet_2_id = r2.data["id"]
    print(f"✓ X tweet 2 posted: {tweet_2_id}")

    r3 = client.create_tweet(text=X_TWEET_3, in_reply_to_tweet_id=tweet_2_id)
    tweet_3_id = r3.data["id"]
    print(f"✓ X tweet 3 posted: {tweet_3_id}")

    return [tweet_1_id, tweet_2_id, tweet_3_id]

def log_published():
    """Log to published_signals.json"""
    pub_file = "/home/slova/ProbBrain/data/published_signals.json"

    # Load existing
    if os.path.exists(pub_file):
        with open(pub_file) as f:
            published = json.load(f)
    else:
        published = []

    # Add new entry
    entry = {
        "signal_id": SIGNAL["signal_id"],
        "market_question": SIGNAL["market_question"],
        "our_estimate_yes": SIGNAL["our_estimate_yes"],
        "market_price_yes": SIGNAL["market_price_yes"],
        "gap_pp": SIGNAL["gap_pp"],
        "confidence": SIGNAL["confidence"],
        "close_date": SIGNAL["close_date"],
        "published_at": datetime.utcnow().isoformat() + "Z",
        "platforms": ["telegram", "x"],
    }

    published.append(entry)

    with open(pub_file, "w") as f:
        json.dump(published, f, indent=2)

    print(f"✓ Logged to published_signals.json")

if __name__ == "__main__":
    try:
        msg_id = post_telegram()
        tweet_ids = post_x()
        log_published()
        print("\n✓ SIG-031 published successfully")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise
