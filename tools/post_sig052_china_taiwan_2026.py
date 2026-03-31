#!/usr/bin/env python3
"""
Post SIG-052: China Taiwan 2026 invasion
Signal: Market 567621 - "Will China invade Taiwan by end of 2026?"
Market price: 9.9% YES | Our estimate: 2% YES | Gap: 7.9pp
Confidence: MEDIUM | Direction: NO_UNDERPRICED
Volume: $536.3k | Closes: 2026-12-31
- Includes Polymarket market card screenshot on first tweet
- 2 hashtags at the end of the final tweet
"""

import httpx
import os
import sys
import json
from datetime import datetime
from dotenv import load_dotenv

# Add tools dir to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polymarket_screenshot import generate_and_upload_market_card

# Load .env file
load_dotenv('/home/slova/ProbBrain/.env')

# Load config
CONFIG_FILE = "/home/slova/ProbBrain/config/publisher.json"
with open(CONFIG_FILE) as f:
    config = json.load(f)

# Signal data
SIGNAL_ID = "SIG-052"
MARKET_ID = "567621"
MARKET_QUESTION = "Will China invade Taiwan by end of 2026?"
MARKET_YES_PRICE = 0.099
OUR_ESTIMATE_YES = 0.02
GAP_PCT = 7.9
VOLUME_USDC = 536279.0
CLOSES = "2026-12-31"
CONFIDENCE = "MEDIUM"
DIRECTION = "NO_UNDERPRICED"
POLYMARKET_SLUG = "will-china-invade-taiwan-by-end-of-2026"

EVIDENCE = [
    "US 2026 Annual Threat Assessment explicitly states China does NOT plan invasion in 2027",
    "Intelligence agencies consensus: no immediate invasion plans; 2030s identified as likely timeframe",
    "China views invasion costs as too high in near term; prefers non-force unification",
    "PLA logistics and training gaps; amphibious invasion assessed as unlikely before 2027-2030",
    "China's strategic timeline: 2049 deadline for 'national rejuvenation' (no near-term urgency)",
]

COUNTER_EVIDENCE = "Market volatility, geopolitical escalation, or unexpected military buildup could shift timeline; Xi's strategic patience historically short-lived under pressure."

AFFILIATE_TELEGRAM = config["affiliate_link_telegram"]
AFFILIATE_X = config["affiliate_link_twitter"]
DASHBOARD_URL = config["dashboard_url"]

# Twitter credentials
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# Telegram format
telegram_message = f"""🟡 MARKET SIGNAL

📊 Will China invade Taiwan by 2026?

Market: {MARKET_YES_PRICE*100:.1f}% YES | Our estimate: {OUR_ESTIMATE_YES*100:.1f}% YES

Gap: {GAP_PCT:.1f}pp (market overpricing YES)

Volume: ${VOLUME_USDC/1000:.0f}k

Closes: {CLOSES}

Evidence:

• US 2026 Threat Assessment rules out 2027 invasion; 2030s timeframe likely

• Intelligence consensus: no immediate invasion plans

• PLA logistics gaps; invasion window 2027-2030+

• China's 2049 strategic deadline suggests no 2026 rush

• Recent corruption scandals degrade PLA readiness

Counter-evidence: Geopolitical escalation or Xi strategic shift could accelerate timeline; market volatility remains a factor.

🔗 Trade on Polymarket: {AFFILIATE_TELEGRAM}

⚠️ Not financial advice. Trade at your own risk.

📈 Accuracy track record: {DASHBOARD_URL}

🐦 Follow us on X: https://x.com/ProbBrain"""

# X threads - hashtags only in final tweet
tweet_1 = f"""Market pricing China-Taiwan invasion at 9.9% by end of 2026.

Our estimate: 2%

Intelligence says 2030s, not 2026. Why market so high?"""

tweet_2 = f"""Evidence:

• US threat assessment rules out 2027 invasion
• PLA logistics gaps → 2027-2030+ window
• China's 2049 deadline = no near-term rush
• Recent corruption degraded readiness

Not financial advice. Trade at your own risk.

Trade: {AFFILIATE_X}"""

tweet_3 = f"""We track every call publicly → {DASHBOARD_URL}

Get signals on Telegram: https://t.me/ProbBrain

Follow @ProbBrain for more. #GeoPolitics #Taiwan"""

def post_telegram():
    """Post to Telegram"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")

    if not bot_token or not channel_id:
        print("⚠️  TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set")
        return None

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": channel_id,
        "text": telegram_message,
        "parse_mode": "Markdown"
    }

    try:
        resp = httpx.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        msg_id = resp.json().get("result", {}).get("message_id")
        print(f"✅ Telegram posted (message_id: {msg_id})")
        return msg_id
    except Exception as e:
        print(f"❌ Telegram failed: {e}")
        return None

def post_x(market_card_media_id: str = None):
    """Post thread to X with optional market card screenshot"""
    try:
        import tweepy
    except ImportError:
        print("⚠️  tweepy not installed")
        return None

    if not all([X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET]):
        print("⚠️  X credentials not set")
        return None

    try:
        client = tweepy.Client(
            consumer_key=X_CONSUMER_KEY,
            consumer_secret=X_CONSUMER_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET,
        )

        # Post main tweet with market card if available
        media_ids = None
        if market_card_media_id:
            media_ids = [market_card_media_id]

        r1 = client.create_tweet(text=tweet_1, media_ids=media_ids)
        tweet_1_id = r1.data["id"]
        print(f"✅ Tweet 1 posted (id: {tweet_1_id})")

        # Post reply 2
        r2 = client.create_tweet(text=tweet_2, in_reply_to_tweet_id=tweet_1_id)
        tweet_2_id = r2.data["id"]
        print(f"✅ Tweet 2 posted (id: {tweet_2_id})")

        # Post reply 3
        r3 = client.create_tweet(text=tweet_3, in_reply_to_tweet_id=tweet_2_id)
        tweet_3_id = r3.data["id"]
        print(f"✅ Tweet 3 posted (id: {tweet_3_id})")

        return [tweet_1_id, tweet_2_id, tweet_3_id]
    except Exception as e:
        print(f"❌ X failed: {e}")
        return None

def update_published_signals(telegram_msg_id, x_tweet_ids):
    """Log to published_signals.json"""

    with open("/home/slova/ProbBrain/data/published_signals.json") as f:
        signals = json.load(f)

    # Create entry
    entry = {
        "signal_id": SIGNAL_ID,
        "market_id": MARKET_ID,
        "question": MARKET_QUESTION,
        "market_yes_price": MARKET_YES_PRICE,
        "our_estimate_yes": OUR_ESTIMATE_YES,
        "gap_pct": GAP_PCT,
        "volume_usdc": VOLUME_USDC,
        "close_date": CLOSES,
        "confidence": CONFIDENCE,
        "direction": DIRECTION,
        "polymarket_slug": POLYMARKET_SLUG,
        "evidence": EVIDENCE,
        "counter_evidence": COUNTER_EVIDENCE,
        "telegram_message_id": telegram_msg_id,
        "x_tweet_ids": x_tweet_ids,
        "published_at": datetime.utcnow().isoformat() + "Z",
        "platforms": ["telegram", "x"]
    }

    signals.append(entry)

    with open("/home/slova/ProbBrain/data/published_signals.json", "w") as f:
        json.dump(signals, f, indent=2)

    print(f"✅ Updated published_signals.json")

def sync_dashboard() -> None:
    """Sync dashboard after publishing."""
    print(f"\n[Dashboard] Syncing accuracy dashboard...")
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, "/home/slova/ProbBrain/tools/sync_dashboard.py", "--signal-id", SIGNAL_ID],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0:
            print(f"  ✓ Dashboard synced")
        else:
            print(f"  ⚠ Dashboard sync had issues: {result.stderr}")
    except Exception as e:
        print(f"  ⚠ Dashboard sync skipped: {e}")

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print(f"{SIGNAL_ID} Publishing Script (CORRECTED)")
    print(f"{'='*60}\n")

    print(f"Publishing {SIGNAL_ID}: {MARKET_QUESTION}")
    print(f"Gap: {GAP_PCT}pp | Volume: ${VOLUME_USDC/1000:.0f}k | Confidence: {CONFIDENCE}")

    # Generate market card and upload to Twitter
    print(f"\n[Market Card] Generating and uploading screenshot...")
    try:
        import tweepy
        twitter_client = tweepy.Client(
            consumer_key=X_CONSUMER_KEY,
            consumer_secret=X_CONSUMER_SECRET,
            access_token=X_ACCESS_TOKEN,
            access_token_secret=X_ACCESS_TOKEN_SECRET,
        )
        media_id = generate_and_upload_market_card(
            market_question=MARKET_QUESTION,
            market_price_yes=MARKET_YES_PRICE,
            our_estimate=OUR_ESTIMATE_YES,
            gap_pct=GAP_PCT,
            confidence=CONFIDENCE,
            twitter_client=twitter_client,
            volume_usdc=VOLUME_USDC
        )
        print(f"  ✓ Market card uploaded (media_id: {media_id})")
    except Exception as e:
        print(f"  ⚠ Market card generation failed: {e}")
        media_id = None

    # Post to platforms
    print(f"\n[Posting] Publishing to platforms...")
    telegram_id = post_telegram()
    x_ids = post_x(media_id)

    if telegram_id or x_ids:
        update_published_signals(telegram_id, x_ids)
        print(f"✓ Logged to published_signals.json")
        sync_dashboard()
        print(f"\n{'='*60}")
        print(f"✅ {SIGNAL_ID} published successfully!")
        print(f"  Telegram: {telegram_id}")
        print(f"  X thread: {x_ids[0] if x_ids else 'N/A'}")
        print(f"{'='*60}\n")
    else:
        print(f"\n❌ Failed to post {SIGNAL_ID}")
