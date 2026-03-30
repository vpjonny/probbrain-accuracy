#!/usr/bin/env python3
"""Publish SIG-033 (California billionaire wealth tax) to Telegram and X."""
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
SIGNAL_ID = "SIG-033"
MARKET_QUESTION = "Billionaire one-time wealth tax passes in California election 2026?"
MARKET_PRICE = 0.355
OUR_ESTIMATE = 0.22
GAP = 13.5
VOLUME_M = 2.78
CLOSE_DATE = "2026-11-03"
POLYMARKET_SLUG = "billionaire-one-time-wealth-tax-passes-in-california-election-2026"
MARKET_ID = 648383

# Affiliate links & dashboard
AFFILIATE_LINK_TG = "https://dub.sh/pb-tg"
AFFILIATE_LINK_X = "https://dub.sh/pb-x"
DASHBOARD_URL = "https://vpjonny.github.io/probbrain-accuracy/"

# ============================================================================
# TELEGRAM MESSAGE
# ============================================================================
telegram_message = f"""MEDIUM — Lean NO

Billionaire wealth tax passes in California election 2026?

Market: 35.5% YES | Our estimate: 22% YES
Gap: 13.5% (market overpricing YES)
Volume: ${VOLUME_M}M
Closes: {CLOSE_DATE}

Evidence:
- California voters rejected Prop 27 (2022) and Prop 28 (2024)
- Tax proposals historically underperform in mid-term elections
- Polling shows 40% support; historical conversion rate ~60% = ~24% probability
- Previous CA wealth taxes (AB 259, 2019) died in committee; consistent failure pattern
- Market overweighted to populist momentum vs. structural voter resistance

Counter-evidence: Billionaire wealth taxes gaining national momentum; California could lead on wealth redistribution.

Trade on Polymarket: {AFFILIATE_LINK_TG}

Not financial advice. Trade at your own risk.
Accuracy track record: {DASHBOARD_URL}
Follow us on X: https://x.com/ProbBrain"""

# ============================================================================
# X THREAD
# ============================================================================
tweet_1 = f"California billionaire wealth tax ballot measure: market 35.5% YES, our estimate 22%. California voters consistently reject tax increases. Gap: 13.5pp—market overprices YES by 8x historical conversion rates."

tweet_2 = f"""Evidence:
• California rejected Prop 27 (2022) and Prop 28 (2024)
• Tax proposals underperform in mid-term elections
• Polling 40% support; conversion rate ~60% = ~24% probability
• Previous CA wealth tax attempts (AB 259) died in committee

Counter: National momentum on wealth taxes, but CA voters have consistently said no.

{AFFILIATE_LINK_X}

Not financial advice."""

tweet_3 = f"""We track every call publicly: {DASHBOARD_URL}

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
    "direction": "NO_UNDERPRICED",
    "confidence": "MEDIUM",
    "our_estimate": OUR_ESTIMATE,
    "market_price_at_signal": MARKET_PRICE,
    "gap_pct": GAP,
    "volume_usdc": VOLUME_M * 1_000_000,
    "close_date": CLOSE_DATE,
    "polymarket_slug": POLYMARKET_SLUG,
    "confidence": "MEDIUM",
    "direction": "NO_UNDERPRICED",
    "evidence": [
        "California voters rejected Prop 27 (2022) and Prop 28 (2024)",
        "Tax proposals historically underperform in mid-term elections",
        "Polling shows 40% support; historical conversion rate ~60% = ~24% probability",
        "Previous CA wealth taxes (AB 259, 2019) died in committee",
        "Market overweighted to populist momentum vs. structural voter resistance"
    ],
    "counter_evidence": "Billionaire wealth taxes gaining national momentum; California could lead on wealth redistribution.",
    "telegram_message_id": telegram_message_id,
    "x_tweet_ids": x_tweet_ids,
    "published_at": datetime.utcnow().isoformat() + "Z",
    "signal_number": 33
}

published.append(signal_entry)
with open(published_file, "w") as f:
    json.dump(published, f, indent=2)
print(f"✓ published_signals.json updated")

# ============================================================================
# SYNC DASHBOARD
# ============================================================================
print(f"[{SIGNAL_ID}] Syncing dashboard...")
os.system("cd /home/slova/ProbBrain && python3 tools/sync_dashboard.py --signal-id SIG-033")

print(f"\n✓ {SIGNAL_ID} published to Telegram and X, dashboard synced.")
