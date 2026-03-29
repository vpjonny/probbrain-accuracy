#!/usr/bin/env python3
"""Post SIG-032: Trump out as President before 2027"""

import os
import sys
import json
from datetime import datetime
import httpx
import tweepy
from dotenv import load_dotenv

# Add tools to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polymarket_screenshot import generate_and_upload_market_card

# Load .env file
load_dotenv("/home/slova/ProbBrain/.env")

# Configuration
SIGNAL_ID = "SIG-032"
MARKET_QUESTION = "Trump out as President before 2027?"
MARKET_PRICE = 17.5
OUR_ESTIMATE = 2.0
GAP = 15.5
VOLUME = 5220972
CLOSE_DATE = "2026-12-31"
CONFIDENCE = "MEDIUM"
DIRECTION = "NO_UNDERPRICED"

# Load credentials from environment
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# Config URLs
TELEGRAM_AFFILIATE = "https://dub.sh/pb-tg"
DASHBOARD_URL = "https://vpjonny.github.io/probbrain-accuracy/"
POLYMARKET_URL = "https://polymarket.com/market/trump-out-as-president-before-2027"

# Evidence
EVIDENCE = [
    "Trump is 79 years old; modern medical care has eliminated in-office deaths (0 of 19 presidents since 1950)",
    "Republican Senate controls Congress; impeachment conviction politically impossible (requires 2/3 majority)",
    "No resignation catalysts evident; Trump actively governing Operation Epic Fury (Iran conflict)",
    "Assassination risk very low in modern era (~0.1% baseline across full term)",
    "Age-adjusted mortality for 79-year-old male over 9 months: ~1-2%",
    "Historical comparison: Only 4 presidents left office due to death/assassination/resignation (1841-1974); none since 1974"
]

COUNTER_EVIDENCE = "Unexpected health crises or political upheaval could accelerate timeline."

def build_telegram_message():
    """Build Telegram message."""
    volume_str = f"${VOLUME / 1_000_000:.1f}M"

    evidence_bullets = "\n".join([f"• {e}" for e in EVIDENCE])

    message = f"""🟡 MARKET SIGNAL

📊 {MARKET_QUESTION}

Market: {MARKET_PRICE}% YES | Our estimate: {OUR_ESTIMATE}% YES

Gap: {GAP}% (market overpricing YES)

Volume: {volume_str}

Closes: {CLOSE_DATE}

Evidence:
{evidence_bullets}

Counter-evidence: {COUNTER_EVIDENCE}

🔗 Trade on Polymarket: {TELEGRAM_AFFILIATE}

⚠️ Not financial advice. Trade at your own risk.

📈 Accuracy track record: {DASHBOARD_URL}

🐦 Follow us on X: https://x.com/ProbBrain"""

    return message

def build_x_thread():
    """Build X thread tweets."""
    # Tweet 1: Main hook
    tweet_1 = f"Market prices Trump out by Dec 31 at 17.5%, but base rate + GOP Senate control suggests 2%. Gap: 15.5pp—market overprices YES by 8.75x. We lean NO."

    # Tweet 2: Evidence + affiliate link
    tweet_2 = f"""Evidence:
• Trump 79; modern era eliminates in-office deaths
• GOP Senate rules out impeachment
• No resignation catalysts; Trump actively governing
• Assassination risk ~0.1% baseline
• 9-month mortality for 79yo: ~1-2%
• Historical: no president exited since 1974

Not financial advice. Trade at your own risk.
{TELEGRAM_AFFILIATE}"""

    # Tweet 3: Dashboard + follow + hashtags
    tweet_3 = f"""We track every call publicly → {DASHBOARD_URL}

Get signals on Telegram: https://t.me/ProbBrain

Follow @ProbBrain for more.

#Politics #Elections"""

    return tweet_1, tweet_2, tweet_3

def post_to_telegram(message):
    """Post message to Telegram."""
    if not BOT_TOKEN or not CHANNEL_ID:
        print("⚠️ TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set; skipping Telegram")
        return None

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    resp = httpx.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    result = resp.json()

    if result.get("ok"):
        message_id = result["result"]["message_id"]
        print(f"✓ Telegram posted (message_id: {message_id})")
        return message_id
    else:
        print(f"✗ Telegram error: {result}")
        return None

def post_to_x(tweet_1, tweet_2, tweet_3):
    """Post thread to X/Twitter with market card screenshot."""
    if not all([X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
        print("⚠️ X credentials not set; skipping X")
        return None, None, None

    client = tweepy.Client(
        consumer_key=X_CONSUMER_KEY,
        consumer_secret=X_CONSUMER_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )

    # Generate and upload market card
    print("🖼️ Generating market card screenshot...")
    media_id = generate_and_upload_market_card(
        market_question=MARKET_QUESTION,
        market_price_yes=MARKET_PRICE / 100.0,
        our_estimate=OUR_ESTIMATE / 100.0,
        gap_pct=GAP,
        confidence=CONFIDENCE,
        twitter_client=client,
        volume_usdc=VOLUME
    )

    # Post thread
    if media_id:
        r1 = client.create_tweet(text=tweet_1, media_ids=[media_id])
        print(f"✓ X Tweet 1 posted with market card (id: {r1.data['id']})")
    else:
        r1 = client.create_tweet(text=tweet_1)
        print(f"✓ X Tweet 1 posted without screenshot (id: {r1.data['id']})")

    r2 = client.create_tweet(text=tweet_2, in_reply_to_tweet_id=r1.data["id"])
    print(f"✓ X Tweet 2 posted (id: {r2.data['id']})")

    r3 = client.create_tweet(text=tweet_3, in_reply_to_tweet_id=r2.data["id"])
    print(f"✓ X Tweet 3 posted with hashtags (id: {r3.data['id']})")

    return r1.data["id"], r2.data["id"], r3.data["id"]

def log_published_signal(tg_msg_id, x_tweet_ids):
    """Log signal to published_signals.json."""
    published_file = "/home/slova/ProbBrain/data/published_signals.json"

    if os.path.exists(published_file):
        with open(published_file, "r") as f:
            published = json.load(f)
    else:
        published = []

    entry = {
        "signal_id": SIGNAL_ID,
        "market_question": MARKET_QUESTION,
        "market_price_yes": MARKET_PRICE / 100,
        "our_estimate_yes": OUR_ESTIMATE / 100,
        "confidence": CONFIDENCE,
        "gap_pct": GAP,
        "volume_usdc": VOLUME,
        "close_date": CLOSE_DATE,
        "telegram_message_id": tg_msg_id,
        "x_tweet_ids": x_tweet_ids,
        "published_at": datetime.utcnow().isoformat() + "Z"
    }

    published.append(entry)

    with open(published_file, "w") as f:
        json.dump(published, f, indent=2)

    print(f"✓ Logged to published_signals.json")

def main():
    print(f"Posting {SIGNAL_ID}: {MARKET_QUESTION}")
    print("=" * 60)

    # Build messages
    tg_message = build_telegram_message()
    x_tweets = build_x_thread()

    print("\n📱 Telegram message:")
    print("-" * 60)
    print(tg_message)
    print("-" * 60)

    print("\n🐦 X thread:")
    print("-" * 60)
    print("Tweet 1:", x_tweets[0])
    print("\nTweet 2:", x_tweets[1])
    print("\nTweet 3:", x_tweets[2])
    print("-" * 60)

    # Post to platforms
    print("\n📤 Posting...")
    tg_msg_id = post_to_telegram(tg_message)
    x_ids = post_to_x(*x_tweets)

    # Log
    log_published_signal(tg_msg_id, x_ids)

    print("\n✅ Done!")

if __name__ == "__main__":
    main()
