#!/usr/bin/env python3
"""Publish SIG-045 to Telegram and X."""
import os
import httpx
import json
from datetime import datetime

# Load env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# Signal data
SIGNAL_ID = "SIG-045"
MARKET_QUESTION = "Billionaire one-time wealth tax passes in California election 2026?"
MARKET_PRICE = 0.355
OUR_ESTIMATE = 0.45
GAP = 9.5
VOLUME_M = 2.78
CLOSE_DATE = "2026-11-03"
POLYMARKET_SLUG = "billionaire-one-time-wealth-tax-passes-in-california-election-2026"
MARKET_ID = 648383

# Affiliate links & dashboard
AFFILIATE_LINK = "https://dub.sh/pb-tg"
DASHBOARD_URL = "https://vpjonny.github.io/probbrain-accuracy/"

# ============================================================================
# TELEGRAM MESSAGE
# ============================================================================
telegram_message = f"""🟡 MARKET SIGNAL

📊 California billionaire wealth tax passes?

Market: 35.5% YES | Our estimate: 45% YES

Gap: 9.5pp (market underpricing YES)

Volume: ${VOLUME_M}M

Closes: {CLOSE_DATE}

Evidence:

• UC Berkeley IGS poll (Mar 9–15, 5000+ voters): 52% YES
• 700k+ signatures submitted (exceeds 546k threshold)
• March momentum: +4pp gain since January (48% → 52%)
• Historical precedent: 50%+ support → 52–60% passage rate

Counter-evidence: Strong opposition from Governor Newsom and CA Business Roundtable; 7 months remain for opposition campaign and typical 2–4pp erosion.

🔗 Trade on Polymarket: https://polymarket.com/market/{MARKET_ID}

⚠️ Not financial advice. Trade at your own risk.

📈 Accuracy track record: {DASHBOARD_URL}

🐦 Follow us on X: https://x.com/ProbBrain"""

# ============================================================================
# X THREAD
# ============================================================================
tweet_1 = f"California billionaire wealth tax ballot measure: market 35.5% YES, our estimate 45%. Recent polling at 52%+ with strong momentum—market significantly underpricing passage odds. 🔗"

tweet_2 = f"""Evidence:
• UC Berkeley poll (Mar 9–15): 52% YES
• 700k+ signatures (exceeds 546k threshold)
• Momentum: +4pp since January
• Historical: 50%+ support → 52–60% passage rate

Trade: https://polymarket.com/market/{MARKET_ID}

⚠️ Not financial advice. Trade at your own risk."""

tweet_3 = f"""We track every call publicly → {DASHBOARD_URL}

Get signals on Telegram: https://t.me/ProbBrain

Follow @ProbBrain for more."""

# ============================================================================
# POST TO TELEGRAM
# ============================================================================
print(f"[{SIGNAL_ID}] Posting to Telegram...")
url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": TELEGRAM_CHANNEL_ID,
    "text": telegram_message,
    "parse_mode": "Markdown"
}
try:
    resp = httpx.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    telegram_data = resp.json()
    telegram_message_id = telegram_data.get("result", {}).get("message_id")
    print(f"✓ Telegram posted (message_id: {telegram_message_id})")
except Exception as e:
    print(f"✗ Telegram failed: {e}")
    telegram_message_id = None

# ============================================================================
# POST TO X
# ============================================================================
print(f"[{SIGNAL_ID}] Posting to X...")
try:
    import tweepy
    client = tweepy.Client(
        consumer_key=X_CONSUMER_KEY,
        consumer_secret=X_CONSUMER_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )

    r1 = client.create_tweet(text=tweet_1)
    tweet_1_id = r1.data["id"]
    print(f"✓ Tweet 1 posted (id: {tweet_1_id})")

    r2 = client.create_tweet(text=tweet_2, in_reply_to_tweet_id=tweet_1_id)
    tweet_2_id = r2.data["id"]
    print(f"✓ Tweet 2 posted (id: {tweet_2_id})")

    r3 = client.create_tweet(text=tweet_3, in_reply_to_tweet_id=tweet_2_id)
    tweet_3_id = r3.data["id"]
    print(f"✓ Tweet 3 posted (id: {tweet_3_id})")

    x_tweet_ids = [tweet_1_id, tweet_2_id, tweet_3_id]
except Exception as e:
    print(f"✗ X posting failed: {e}")
    x_tweet_ids = []

# ============================================================================
# UPDATE published_signals.json
# ============================================================================
print(f"[{SIGNAL_ID}] Updating published_signals.json...")
published_file = "/home/slova/ProbBrain/data/published_signals.json"
try:
    with open(published_file, "r") as f:
        published = json.load(f)
except FileNotFoundError:
    published = []

signal_entry = {
    "signal_id": SIGNAL_ID,
    "market_id": MARKET_ID,
    "question": MARKET_QUESTION,
    "direction": "YES_UNDERPRICED",
    "confidence": "MEDIUM",
    "our_estimate": OUR_ESTIMATE,
    "market_price_at_signal": MARKET_PRICE,
    "gap_pct": GAP,
    "volume_m": VOLUME_M,
    "close_date": CLOSE_DATE,
    "polymarket_slug": POLYMARKET_SLUG,
    "published_at": datetime.utcnow().isoformat() + "Z",
    "platforms": ["telegram", "x"],
    "telegram_message_id": telegram_message_id,
    "x_tweet_ids": x_tweet_ids
}

published.append(signal_entry)
with open(published_file, "w") as f:
    json.dump(published, f, indent=2)
print(f"✓ published_signals.json updated")

# ============================================================================
# SYNC DASHBOARD
# ============================================================================
print(f"[{SIGNAL_ID}] Syncing dashboard...")
os.system("cd /home/slova/ProbBrain && python3 tools/sync_dashboard.py --signal-id SIG-045")

print(f"\n✓ {SIGNAL_ID} published to Telegram and X, dashboard synced.")
