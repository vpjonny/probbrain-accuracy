#!/usr/bin/env python3
"""
Template for posting signals to Telegram and X with Polymarket market card screenshot.

To use this for a new signal:
1. Copy this file to post_sig### _<name>.py
2. Update SIGNAL dict with market data
3. Update EVIDENCE and COUNTER_EVIDENCE lists
4. Update tweet text
5. Run: python3 tools/post_sig###_<name>.py

This template includes market card screenshot generation (NEW FEATURE).
"""

import os
import json
import httpx
import tweepy
from datetime import datetime
from dotenv import load_dotenv

# Add tools to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polymarket_screenshot import generate_and_upload_market_card

# Load .env file
load_dotenv("/home/slova/ProbBrain/.env")

# Load credentials
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# Affiliate and dashboard links
AFFILIATE_TG = "https://dub.sh/pb-tg"
AFFILIATE_X = "https://dub.sh/pb-x"
DASHBOARD_URL = "https://vpjonny.github.io/probbrain-accuracy/"

# ============================================================================
# SIGNAL DATA — UPDATE THIS FOR YOUR SIGNAL
# ============================================================================

SIGNAL = {
    "signal_id": "SIG-XXX",
    "market": "Your market question here",
    "market_price_yes": 0.515,  # As decimal 0-1
    "our_estimate": 0.04,
    "gap_pct": 47.5,
    "confidence": "HIGH",  # HIGH or MEDIUM
    "volume_usdc": 1234567.89,
    "close_date": "2026-07-01",
    "market_id": "123456",
    "polymarket_slug": "market-slug-here",
}

EVIDENCE = [
    "Evidence point 1",
    "Evidence point 2",
    "Evidence point 3",
]

COUNTER_EVIDENCE = "One sentence acknowledging the opposing view."

# ============================================================================
# TELEGRAM MESSAGE
# ============================================================================

badge = "🔴 HIGH" if SIGNAL["confidence"] == "HIGH" else "🟡 MEDIUM"
telegram_message = f"""{badge} — Bet {'YES' if SIGNAL['our_estimate'] > SIGNAL['market_price_yes'] else 'NO'}

📊 {SIGNAL['market']}

Market: {SIGNAL['market_price_yes']*100:.1f}% YES | Our estimate: {SIGNAL['our_estimate']*100:.1f}% YES

Gap: {SIGNAL['gap_pct']:.1f}pp (market {'overpricing' if SIGNAL['gap_pct'] > 0 else 'underpricing'} YES)

Volume: ${SIGNAL['volume_usdc']/1e6:.2f}M

Closes: {SIGNAL['close_date']}

Evidence:

• {EVIDENCE[0]}

• {EVIDENCE[1]}

• {EVIDENCE[2]}

Counter-evidence: {COUNTER_EVIDENCE}

🔗 Trade on Polymarket: {AFFILIATE_TG}

⚠️ Not financial advice. Trade at your own risk.

📈 Accuracy track record: {DASHBOARD_URL}

🐦 Follow us on X: https://x.com/ProbBrain
"""

# ============================================================================
# X THREAD
# ============================================================================

tweet_1 = f"Your core insight here. [thread]"

tweet_2 = f"""Evidence:
• {EVIDENCE[0]}
• {EVIDENCE[1]}
• {EVIDENCE[2]}

{AFFILIATE_X}

⚠️ Not financial advice. Trade at your own risk."""

tweet_3 = f"""We track every call publicly → {DASHBOARD_URL}

Get signals on Telegram: https://t.me/ProbBrain

Follow @ProbBrain for more."""

# ============================================================================
# POST TO TELEGRAM
# ============================================================================

print("[1/5] Posting to Telegram...")
url_tg = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload_tg = {
    "chat_id": CHANNEL_ID,
    "text": telegram_message,
    "parse_mode": "Markdown"
}
resp_tg = httpx.post(url_tg, json=payload_tg, timeout=30)
resp_tg.raise_for_status()
tg_message_id = resp_tg.json()["result"]["message_id"]
print(f"✓ Telegram message posted (ID: {tg_message_id})")

# ============================================================================
# POST TO X (WITH MARKET CARD SCREENSHOT)
# ============================================================================

print("[2/5] Posting to X...")
client = tweepy.Client(
    consumer_key=X_CONSUMER_KEY,
    consumer_secret=X_CONSUMER_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_TOKEN_SECRET,
)

# Generate and upload market card
print("[3/5] Generating market card screenshot...")
media_id = generate_and_upload_market_card(
    market_question=SIGNAL["market"],
    market_price_yes=SIGNAL["market_price_yes"],
    our_estimate=SIGNAL["our_estimate"],
    gap_pct=SIGNAL["gap_pct"],
    confidence=SIGNAL["confidence"],
    twitter_client=client,
    volume_usdc=SIGNAL["volume_usdc"]
)

# Post tweets
if media_id:
    r1 = client.create_tweet(text=tweet_1, media_ids=[media_id])
    print(f"✓ Tweet 1 posted with market card (ID: {r1.data['id']})")
else:
    r1 = client.create_tweet(text=tweet_1)
    print(f"✓ Tweet 1 posted (ID: {r1.data['id']}, no screenshot)")

tweet_1_id = r1.data["id"]

r2 = client.create_tweet(text=tweet_2, in_reply_to_tweet_id=tweet_1_id)
tweet_2_id = r2.data["id"]
print(f"✓ Tweet 2 posted (ID: {tweet_2_id})")

r3 = client.create_tweet(text=tweet_3, in_reply_to_tweet_id=tweet_2_id)
tweet_3_id = r3.data["id"]
print(f"✓ Tweet 3 posted (ID: {tweet_3_id})")

# ============================================================================
# LOG TO published_signals.json
# ============================================================================

print("[4/5] Logging to published_signals.json...")

published_file = "/home/slova/ProbBrain/data/published_signals.json"
with open(published_file, "r") as f:
    published = json.load(f)

entry = {
    "signal_id": SIGNAL["signal_id"],
    "market_id": SIGNAL["market_id"],
    "market_question": SIGNAL["market"],
    "market_price_yes": SIGNAL["market_price_yes"],
    "our_estimate": SIGNAL["our_estimate"],
    "gap_pct": SIGNAL["gap_pct"],
    "confidence": SIGNAL["confidence"],
    "volume_usdc": SIGNAL["volume_usdc"],
    "close_date": SIGNAL["close_date"],
    "polymarket_slug": SIGNAL["polymarket_slug"],
    "published_at": datetime.utcnow().isoformat() + "Z",
    "telegram_message_id": str(tg_message_id),
    "x_tweet_ids": [str(tweet_1_id), str(tweet_2_id), str(tweet_3_id)],
    "x_has_market_card": media_id is not None,
    "evidence": EVIDENCE,
    "counter_evidence": COUNTER_EVIDENCE,
    "direction": "YES_UNDERPRICED",  # Update as needed
    "approval_required": False,
    "paperclip_issue": "PRO-###",  # Update with actual issue
}

published.append(entry)

with open(published_file, "w") as f:
    json.dump(published, f, indent=2)

print(f"✓ Logged to published_signals.json")

# ============================================================================
# SYNC DASHBOARD
# ============================================================================

print("[5/5] Syncing dashboard...")
os.system(f"cd /home/slova/ProbBrain && python3 tools/sync_dashboard.py --signal-id {SIGNAL['signal_id']}")
print("✓ Dashboard synced")

print(f"\n✅ All done! {SIGNAL['signal_id']} published with market card screenshot.")
print(f"   Telegram: message_id={tg_message_id}")
print(f"   X: tweets {tweet_1_id} → {tweet_2_id} → {tweet_3_id}")
print(f"   Market card: {'✓ Included' if media_id else '✗ Skipped'}")
