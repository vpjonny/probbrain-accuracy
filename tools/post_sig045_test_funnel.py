#!/usr/bin/env python3
"""Publish SIG-045 (test funnel validation) to Telegram and X with market card screenshot."""
import os
import httpx
import json
from datetime import datetime
import time
from dotenv import load_dotenv
import sys

# Add tools to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polymarket_screenshot import generate_and_upload_market_card

# Load .env
load_dotenv()

# Load env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# Signal data (SIG-045)
SIGNAL_ID = "SIG-045"
MARKET_QUESTION = "Test signal for funnel validation"
MARKET_PRICE = 0.35
OUR_ESTIMATE = 0.15
CONFIDENCE = "MEDIUM"
GAP_PCT = 20.0
VOLUME = 100000
CLOSE_DATE = "2026-04-30"
POLYMARKET_SLUG = "test-signal-funnel"
DIRECTION = "NO_UNDERPRICED"

DASHBOARD_URL = "https://vpjonny.github.io/probbrain-accuracy/"
DUB_TELEGRAM = "https://dub.sh/pb-tg"
DUB_TWITTER = "https://dub.sh/pb-x"

# Format Telegram message
telegram_msg = f"""🟡 MARKET SIGNAL

{MARKET_QUESTION}

Market: 35% YES | Our estimate: 15% YES
Gap: 20% (market overpricing YES)
Volume: $100k
Closes: {CLOSE_DATE}

Evidence:
• This is a test signal for funnel validation

Counter-evidence: Market pricing reflects some interest despite test nature.

🔗 Trade on Polymarket: {DUB_TELEGRAM}

⚠️ Not financial advice. Trade at your own risk.
📈 Accuracy track record: {DASHBOARD_URL}
🐦 Follow us on X: https://x.com/ProbBrain"""

# Post to Telegram
print("[Telegram] Posting message...")
try:
    resp = httpx.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHANNEL_ID,
            "text": telegram_msg,
            "parse_mode": "Markdown",
        },
        timeout=30,
    )
    tg_result = resp.json()
    if resp.status_code == 200:
        telegram_msg_id = tg_result["result"]["message_id"]
        print(f"✓ Telegram posted (message_id: {telegram_msg_id})")
    else:
        print(f"✗ Telegram failed: {tg_result}")
        exit(1)
except Exception as e:
    print(f"✗ Telegram error: {e}")
    exit(1)

# Post X thread using tweepy
print("[X] Posting thread...")
try:
    import tweepy

    client = tweepy.Client(
        consumer_key=X_CONSUMER_KEY,
        consumer_secret=X_CONSUMER_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
        wait_on_rate_limit=True,
    )

    # Generate market card screenshot
    print("[X] Generating market card screenshot...")
    media_id = generate_and_upload_market_card(
        market_question=MARKET_QUESTION,
        market_price_yes=MARKET_PRICE,
        our_estimate=OUR_ESTIMATE,
        gap_pct=GAP_PCT,
        confidence=CONFIDENCE,
        twitter_client=client,
        volume_usdc=VOLUME,
    )

    # Tweet 1: Core insight with market card
    tweet_1 = f"{MARKET_QUESTION}\n\nMarket: 35% YES | Our: 15% YES\nGap: 20pp (overpricing YES)"

    if media_id:
        r1 = client.create_tweet(text=tweet_1, media_ids=[media_id])
        print(f"✓ Tweet 1 posted with market card (id: {r1.data['id']})")
    else:
        r1 = client.create_tweet(text=tweet_1)
        print(f"✓ Tweet 1 posted without screenshot (id: {r1.data['id']})")
    tweet_1_id = r1.data["id"]

    time.sleep(1)  # Rate limit safety

    # Tweet 2: Evidence
    tweet_2 = f"""Evidence:
• This is a test signal for funnel validation

Not financial advice. Trade at your own risk.

Trade on Polymarket: {DUB_TWITTER}"""

    r2 = client.create_tweet(text=tweet_2, in_reply_to_tweet_id=tweet_1_id)
    tweet_2_id = r2.data["id"]
    print(f"✓ Tweet 2 posted (id: {tweet_2_id})")

    time.sleep(1)  # Rate limit safety

    # Tweet 3: Dashboard + Telegram + follow + hashtags (always 2)
    tweet_3 = f"""We track every call publicly:
{DASHBOARD_URL}

Get signals on Telegram: https://t.me/ProbBrain
Follow @ProbBrain for more.

#Markets #Prediction"""

    r3 = client.create_tweet(text=tweet_3, in_reply_to_tweet_id=tweet_2_id)
    tweet_3_id = r3.data["id"]
    print(f"✓ Tweet 3 posted (id: {tweet_3_id})")

    x_tweet_ids = [tweet_1_id, tweet_2_id, tweet_3_id]

except Exception as e:
    print(f"✗ X error: {e}")
    exit(1)

# Log to published_signals.json
print("[Data] Logging to published_signals.json...")
try:
    with open("data/published_signals.json", "r") as f:
        published = json.load(f)
except FileNotFoundError:
    published = []

# Add signal entry
signal_entry = {
    "signal_id": SIGNAL_ID,
    "market_id": "1234567",
    "question": MARKET_QUESTION,
    "market_yes_price": MARKET_PRICE,
    "our_calibrated_estimate": OUR_ESTIMATE,
    "gap_pct": GAP_PCT,
    "volume_usdc": VOLUME,
    "close_date": CLOSE_DATE,
    "polymarket_slug": POLYMARKET_SLUG,
    "confidence": CONFIDENCE,
    "direction": DIRECTION,
    "evidence": ["This is a test signal for funnel validation"],
    "counter_evidence": "Market pricing reflects some interest despite test nature.",
    "telegram_message_id": telegram_msg_id,
    "x_tweet_ids": x_tweet_ids,
    "x_has_market_card": media_id is not None,
    "x_thread_includes_hashtags": True,
    "published_at": datetime.utcnow().isoformat() + "Z",
    "signal_number": 45,
}

published.append(signal_entry)

with open("data/published_signals.json", "w") as f:
    json.dump(published, f, indent=2)

print(f"✓ Logged to published_signals.json")
print(f"\n✅ {SIGNAL_ID} published successfully!")
print(f"  Telegram: {telegram_msg_id}")
print(f"  X thread: {tweet_1_id} → {tweet_2_id} → {tweet_3_id}")
