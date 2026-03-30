#!/usr/bin/env python3
"""
Publish SIG-048 (Bitcoin $1M before GTA VI) to Telegram and X
CEO-approved signal with 48.35pp gap
"""

import os
import json
from datetime import datetime, timezone
import httpx
import tweepy
from PIL import Image, ImageDraw, ImageFont
import requests
from io import BytesIO

# Signal data
SIGNAL_ID = "SIG-048"
SIGNAL_NUMBER = 48
MARKET_QUESTION = "Will Bitcoin hit $1M before GTA VI?"
MARKET_ID = "540844"
POLYMARKET_SLUG = "will-bitcoin-hit-1m-before-gta-vi-872"
MARKET_PRICE_YES = 0.4885
OUR_ESTIMATE_YES = 0.005
GAP_PP = 48.35
CONFIDENCE = "HIGH"
DIRECTION = "NO_UNDERPRICED"
CLOSE_DATE = "2026-08-22"  # GTA VI release date (estimated)
VOLUME_USDC = 75000  # Approx

EVIDENCE = [
    "Expert consensus 2026: $75K-$225K (Standard Chartered, CNBC survey)",
    "$1M targets are for 2030, not 2026 (Cathie Wood, Ark)",
    "Would require 1,328% increase in 4 months - no precedent",
    "No credible analyst forecasts $1M by mid-2026"
]

COUNTER_EVIDENCE = "Bitcoin volatility and past bull runs ($20K to $65K+) show extreme appreciation possible, though historical base rate for 1000%+ quarterly rallies is near zero."

# Load config and env
config = json.load(open("/home/slova/ProbBrain/config/publisher.json"))
AFFILIATE_LINK = config["affiliate_link_telegram"]
DASHBOARD_URL = config["dashboard_url"]

# Telegram setup
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Twitter setup
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

def format_telegram_message():
    """Format message for Telegram"""
    market_price_pct = int(MARKET_PRICE_YES * 100)
    our_estimate_pct = int(OUR_ESTIMATE_YES * 100)

    evidence_bullets = "\n".join(f"• {e}" for e in EVIDENCE)

    msg = f"""🔴 HIGH — Bet NO

📊 {MARKET_QUESTION}

Market: {market_price_pct}% YES | Our estimate: {our_estimate_pct}% YES
Gap: {GAP_PP:.1f}pp (market overpricing YES)
Volume: ${VOLUME_USDC/1000:.0f}k
Closes: {CLOSE_DATE}

Evidence:
{evidence_bullets}

Counter-evidence: {COUNTER_EVIDENCE}

🔗 Trade on Polymarket: {AFFILIATE_LINK}

⚠️ Not financial advice. Trade at your own risk.
📈 Accuracy track record: {DASHBOARD_URL}
🐦 Follow us on X: https://x.com/ProbBrain
"""
    return msg

def format_x_tweets():
    """Format tweets for X thread"""
    tweet1 = f"Bitcoin hitting $1M by GTA VI release? Market: 48.85% YES | Our estimate: 0.5% YES | 48.35pp gap\n\nMarket vastly overprices extreme crypto appreciation. 🧵 #Bitcoin #Prediction"

    evidence_text = "\n".join(f"• {e}" for e in EVIDENCE)

    tweet2 = f"""Evidence:
{evidence_text}

Counter: Bitcoin volatility + past bull runs show 1000%+ moves possible (though historical base rate for quarterly rallies is near zero).

Trade on Polymarket: {AFFILIATE_LINK}
⚠️ Not financial advice."""

    tweet3 = f"""We track every call publicly → {DASHBOARD_URL}

Get signals on Telegram: https://t.me/ProbBrain
Follow @ProbBrain for more. #Markets"""

    return tweet1, tweet2, tweet3

def post_telegram():
    """Post to Telegram"""
    msg = format_telegram_message()
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": msg, "parse_mode": "Markdown"}

    resp = httpx.post(url, json=payload, timeout=30)
    if resp.status_code == 200:
        result = resp.json()
        return result['result']['message_id']
    else:
        raise Exception(f"Telegram failed: {resp.text}")

def post_x():
    """Post thread to X"""
    client = tweepy.Client(
        consumer_key=X_CONSUMER_KEY,
        consumer_secret=X_CONSUMER_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )

    tweet1, tweet2, tweet3 = format_x_tweets()

    # Post thread
    r1 = client.create_tweet(text=tweet1)
    r2 = client.create_tweet(text=tweet2, in_reply_to_tweet_id=r1.data["id"])
    r3 = client.create_tweet(text=tweet3, in_reply_to_tweet_id=r2.data["id"])

    return [r1.data["id"], r2.data["id"], r3.data["id"]]

def log_published():
    """Log to published_signals.json"""
    with open("/home/slova/ProbBrain/data/published_signals.json", "r") as f:
        signals = json.load(f)

    signal_entry = {
        "id": SIGNAL_ID,
        "signal_id": SIGNAL_ID,
        "signal_number": SIGNAL_NUMBER,
        "market_id": MARKET_ID,
        "polymarket_slug": POLYMARKET_SLUG,
        "market_question": MARKET_QUESTION,
        "question": MARKET_QUESTION,
        "category": "crypto",
        "direction": DIRECTION,
        "confidence": CONFIDENCE,
        "market_price": MARKET_PRICE_YES,
        "our_estimate": OUR_ESTIMATE_YES,
        "our_calibrated_estimate": OUR_ESTIMATE_YES,
        "gap_pct": GAP_PP,
        "volume_usdc": VOLUME_USDC,
        "close_date": CLOSE_DATE,
        "evidence": EVIDENCE,
        "counter_evidence": COUNTER_EVIDENCE,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "platforms": ["telegram", "x"],
        "telegram_message_id": None,
        "x_tweet_ids": [],
        "status": "pending",
        "resolved": False,
        "outcome": None,
        "brier_score": None
    }

    signals.append(signal_entry)

    with open("/home/slova/ProbBrain/data/published_signals.json", "w") as f:
        json.dump(signals, f, indent=2)

def main():
    print(f"Publishing {SIGNAL_ID}...")

    # Post to Telegram
    tg_id = post_telegram()
    print(f"✓ Telegram message ID: {tg_id}")

    # Post to X
    x_ids = post_x()
    print(f"✓ X thread IDs: {x_ids}")

    # Log to published_signals.json
    log_published()
    print(f"✓ Logged to published_signals.json")

    print(f"\n{SIGNAL_ID} published to both platforms!")

if __name__ == "__main__":
    main()
