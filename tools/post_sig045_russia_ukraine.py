#!/usr/bin/env python3
"""
Publish SIG-045: Russia-Ukraine Ceasefire (45.5% gap, HIGH confidence, CEO approved)
Market 540816 | Closes 2026-07-31
"""

import json
import os
from datetime import datetime
import httpx
import tweepy

# Load environment
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# Signal data
SIGNAL = {
    "signal_id": "SIG-045",
    "market_id": "540816",
    "question": "Russia-Ukraine Ceasefire before GTA VI?",
    "market_price_yes": 0.535,
    "our_estimate": 0.08,
    "gap_pct": 45.5,
    "confidence": "HIGH",
    "volume_usdc": 1407040,
    "close_date": "2026-07-31",
    "polymarket_slug": "russia-ukraine-ceasefire-before-gta-vi",
    "evidence": [
        "US-brokered talks on hold (March 10) due to Middle East escalation",
        "Moscow Times (March 27): negotiations extending conflict, no momentum toward resolution",
        "Russia demands Ukrainian territorial withdrawal from Donetsk; Kyiv refuses concessions without security guarantees"
    ],
}

# Config
with open("config/publisher.json") as f:
    config = json.load(f)

AFFILIATE_TG = config["affiliate_link_telegram"]
AFFILIATE_X = config["affiliate_link_twitter"]
DASHBOARD_URL = config["dashboard_url"]

# Telegram message
telegram_msg = f"""🔴 HIGH — Bet NO

📊 Russia-Ukraine Ceasefire before GTA VI?

Market: {SIGNAL['market_price_yes']*100:.1f}% YES | Our estimate: {SIGNAL['our_estimate']*100:.1f}% YES

Gap: {SIGNAL['gap_pct']}% (market overpricing YES)

Volume: ${SIGNAL['volume_usdc']/1000000:.2f}M

Closes: {SIGNAL['close_date']}

Evidence:

• {SIGNAL['evidence'][0]}

• {SIGNAL['evidence'][1]}

• {SIGNAL['evidence'][2]}

Counter-evidence: Some analysts argue humanitarian corridors and prisoner exchanges could precede formal ceasefire; Russia and US both stated commitment to diplomatic process.

🔗 Trade on Polymarket: {AFFILIATE_TG}

⚠️ Not financial advice. Trade at your own risk.

📈 Accuracy track record: {DASHBOARD_URL}

🐦 Follow us on X: https://x.com/ProbBrain
"""

# X thread
tweet_1 = f"Market prices Russia-Ukraine ceasefire at 53.5% by July 31. Our estimate: 8%. Why? Talks stalled, territorial demands irreconcilable, recent escalations. 45pp gap. HIGH confidence. #Geopolitics"

tweet_2 = f"""Evidence:
• US-brokered talks on hold (March 10)
• Moscow Times: negotiations extending conflict, not resolving
• Russia demands Donetsk; Ukraine refuses concessions

🔗 {AFFILIATE_X}

⚠️ Not financial advice. Trade at your own risk."""

tweet_3 = f"""We track every call publicly → {DASHBOARD_URL}

Get signals on Telegram: https://t.me/ProbBrain

Follow @ProbBrain for more."""

# Post to Telegram
print("[Telegram] Posting signal...", end=" ", flush=True)
try:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": telegram_msg, "parse_mode": "Markdown"}
    resp = httpx.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    tg_response = resp.json()
    telegram_msg_id = tg_response["result"]["message_id"]
    print(f"✓ Message {telegram_msg_id}")
except Exception as e:
    print(f"✗ Failed: {e}")
    exit(1)

# Post to X
print("[X] Posting thread...", end=" ", flush=True)
try:
    client = tweepy.Client(
        consumer_key=X_CONSUMER_KEY,
        consumer_secret=X_CONSUMER_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )
    r1 = client.create_tweet(text=tweet_1)
    r2 = client.create_tweet(text=tweet_2, in_reply_to_tweet_id=r1.data["id"])
    r3 = client.create_tweet(text=tweet_3, in_reply_to_tweet_id=r2.data["id"])
    x_tweet_ids = [r1.data["id"], r2.data["id"], r3.data["id"]]
    print(f"✓ Thread {x_tweet_ids[0]}")
except Exception as e:
    print(f"✗ Failed: {e}")
    exit(1)

# Update published_signals.json
print("[Data] Updating published_signals.json...", end=" ", flush=True)
with open("data/published_signals.json") as f:
    published = json.load(f)

published_entry = {
    "signal_id": SIGNAL["signal_id"],
    "market_id": SIGNAL["market_id"],
    "question": SIGNAL["question"],
    "category": "geopolitics",
    "direction": "NO_UNDERPRICED",
    "confidence": SIGNAL["confidence"],
    "market_yes_price": SIGNAL["market_price_yes"],
    "our_calibrated_estimate": SIGNAL["our_estimate"],
    "gap_pct": SIGNAL["gap_pct"],
    "volume_usdc": SIGNAL["volume_usdc"],
    "close_date": SIGNAL["close_date"],
    "polymarket_slug": SIGNAL["polymarket_slug"],
    "published_at": datetime.utcnow().isoformat() + "Z",
    "telegram_message_id": telegram_msg_id,
    "x_tweet_ids": x_tweet_ids,
    "x_account": "@ProbBrain",
    "telegram_channel": "@ProbBrain",
    "evidence": SIGNAL["evidence"],
    "platforms": ["telegram", "x"],
    "telegram_link": AFFILIATE_TG,
    "x_link": AFFILIATE_X,
}

published.append(published_entry)
with open("data/published_signals.json", "w") as f:
    json.dump(published, f, indent=2)
print(f"✓ {len(published)} signals")

# Remove from pending
print("[Data] Removing from pending_signals.json...", end=" ", flush=True)
with open("data/pending_signals.json") as f:
    pending = json.load(f)
pending = [s for s in pending if s.get("signal_id") != "SIG-045"]
with open("data/pending_signals.json", "w") as f:
    json.dump(pending, f, indent=2)
print(f"✓ {len(pending)} remaining")

# Sync dashboard
print("[Dashboard] Syncing...", end=" ", flush=True)
os.system("python3 tools/sync_dashboard.py --signal-id SIG-045 > /dev/null 2>&1")
print("✓ Done")

# Summary
print("\n✅ SIG-045 published successfully")
print(f"  Telegram: {telegram_msg_id}")
print(f"  X thread: {x_tweet_ids[0]}")
print(f"  Dashboard: {DASHBOARD_URL}")
