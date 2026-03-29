#!/usr/bin/env python3
"""
Post SIG-034 (Tennessee Volunteers vs. Michigan Wolverines) to Telegram and X.
WARNING: Market closes 2026-03-29T16:00 (may already be closed).
"""

import os
import json
import httpx
import tweepy
from datetime import datetime
from dotenv import load_dotenv

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

# Signal data
SIGNAL = {
    "signal_id": "SIG-034",
    "market": "Tennessee Volunteers vs. Michigan Wolverines",
    "market_price_yes": 0.225,
    "our_estimate": 0.26,
    "gap_pct": 3.5,
    "confidence": "MEDIUM",
    "volume_usdc": 2442108.520329002,
    "close_date": "2026-03-29",
    "market_id": "1753593",
    "polymarket_slug": "cbb-tenn-mich-2026-03-29",
}

EVIDENCE = [
    "Michigan: 34-3 (1-seed, #3 ranked), Tennessee: 25-11 (6-seed, #23-25 ranked)",
    "Tournament dominance: Michigan won by +21, +23, +13 in prior games",
    "Michigan 7.5-point favorite (implies ~25-26% for Tennessee)",
    "Expert predictions all favor Michigan by 10+ points",
    "Michigan 7-5 all-time, 4 straight recent wins vs Tennessee",
]

COUNTER_EVIDENCE = "Tennessee's experience in tournament play and double-digit seeding upsets in March Madness history provide non-zero probability, though Michigan's dominant run and ranking advantage strongly favor the higher seed."

# ============================================================================
# TELEGRAM MESSAGE
# ============================================================================

telegram_message = f"""🟡 MEDIUM — Lean YES

📊 Tennessee Volunteers vs. Michigan Wolverines

Market: {SIGNAL['market_price_yes']*100:.1f}% YES | Our estimate: {SIGNAL['our_estimate']*100:.1f}% YES

Gap: {SIGNAL['gap_pct']:.1f}pp (market underpricing YES)

Volume: ${SIGNAL['volume_usdc']/1e6:.1f}M

Closes: {SIGNAL['close_date']}

Evidence:

• {EVIDENCE[0]}

• {EVIDENCE[1]}

• {EVIDENCE[2]}

• {EVIDENCE[3]}

• {EVIDENCE[4]}

Counter-evidence: {COUNTER_EVIDENCE}

🔗 Trade on Polymarket: {AFFILIATE_TG}

⚠️ Not financial advice. Trade at your own risk.

📈 Accuracy track record: {DASHBOARD_URL}

🐦 Follow us on X: https://x.com/ProbBrain
"""

# ============================================================================
# X THREAD
# ============================================================================

tweet_1 = f"Michigan (1-seed, 34-3) vs Tennessee (6-seed, 25-11). Market says {SIGNAL['market_price_yes']*100:.1f}% for Tennessee, but 7.5-point favorites typically carry ~25-26% underdog probability. Gap: {SIGNAL['gap_pct']:.1f}pp."

tweet_2 = f"""Evidence:
• Michigan: 34-3 record, #3 ranked, dominant tournament run
• Tennessee: 25-11 record, #23-25 ranked
• Michigan: +21, +23, +13 wins in previous tournament games
• 7-5 all-time, 4 straight wins vs Tennessee

{AFFILIATE_X}

⚠️ Not financial advice. Trade at your own risk."""

tweet_3 = f"""We track every call publicly → {DASHBOARD_URL}

Get signals on Telegram: https://t.me/ProbBrain

Follow @ProbBrain for more."""

# ============================================================================
# POST TO TELEGRAM
# ============================================================================

print("[1/4] Posting to Telegram...")
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
# POST TO X
# ============================================================================

print("[2/4] Posting to X...")
client = tweepy.Client(
    consumer_key=X_CONSUMER_KEY,
    consumer_secret=X_CONSUMER_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_TOKEN_SECRET,
)

r1 = client.create_tweet(text=tweet_1)
tweet_1_id = r1.data["id"]
print(f"✓ Tweet 1 posted (ID: {tweet_1_id})")

r2 = client.create_tweet(text=tweet_2, in_reply_to_tweet_id=tweet_1_id)
tweet_2_id = r2.data["id"]
print(f"✓ Tweet 2 posted (ID: {tweet_2_id})")

r3 = client.create_tweet(text=tweet_3, in_reply_to_tweet_id=tweet_2_id)
tweet_3_id = r3.data["id"]
print(f"✓ Tweet 3 posted (ID: {tweet_3_id})")

# ============================================================================
# LOG TO published_signals.json
# ============================================================================

print("[3/4] Logging to published_signals.json...")

# Read existing published signals
published_file = "/home/slova/ProbBrain/data/published_signals.json"
with open(published_file, "r") as f:
    published = json.load(f)

# Add new entry
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
    "evidence": EVIDENCE,
    "counter_evidence": COUNTER_EVIDENCE,
    "direction": "YES_UNDERPRICED",
    "approval_required": False,
    "paperclip_issue": "PRO-383",
}

published.append(entry)

# Write back
with open(published_file, "w") as f:
    json.dump(published, f, indent=2)

print(f"✓ Logged to published_signals.json")

# ============================================================================
# SYNC DASHBOARD
# ============================================================================

print("[4/4] Syncing dashboard...")
os.system("cd /home/slova/ProbBrain && python3 tools/sync_dashboard.py --signal-id SIG-034")
print("✓ Dashboard synced")

print("\n✅ All done! SIG-034 published.")
print(f"   Telegram: message_id={tg_message_id}")
print(f"   X: tweets {tweet_1_id} → {tweet_2_id} → {tweet_3_id}")
