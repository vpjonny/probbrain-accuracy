#!/usr/bin/env python3
"""
Post SIG-035 (House control 2026 — Democrats) to Telegram and X.
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
    "signal_id": "SIG-035",
    "market": "Will the Democratic Party control the House after the 2026 Midterm elections?",
    "market_price_yes": 0.845,
    "our_estimate": 0.69,
    "gap_pct": 15.5,
    "confidence": "MEDIUM",
    "volume_usdc": 2036468.5228530061,
    "close_date": "2026-11-03",
    "market_id": "562802",
    "polymarket_slug": "will-the-democratic-party-control-the-house-after-the-2026-midterm-elections",
}

EVIDENCE = [
    "Democrats only need 3 net seat flips for majority; GOP majority is narrow and vulnerable",
    "Cook Political Report: 42 battleground districts, Democrats hold 22, Republicans hold 20",
    "Party holding presidency (Trump) historically loses 20-35 seats in midterms",
    "Democrat fundraising advantage signals engaged base and recent special election momentum",
    "Market prices Dem dominance at 84.5%, but forecasts place odds around 69%",
]

COUNTER_EVIDENCE = "7-8 months remain until election; gerrymandering gives GOP structural advantage in many districts, limiting Democratic gains despite favorable momentum."

# ============================================================================
# TELEGRAM MESSAGE
# ============================================================================

telegram_message = f"""🟡 MARKET SIGNAL

📊 Will Democrats control House post-2026 midterms?

Market: {SIGNAL['market_price_yes']*100:.1f}% YES | Our estimate: {SIGNAL['our_estimate']*100:.1f}% YES

Gap: {SIGNAL['gap_pct']:.1f}pp (market overpricing YES)

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

tweet_1 = f"Democrats at 69% to control House 2026 per latest forecasts, but market says 84.5%. That's a {SIGNAL['gap_pct']:.1f}pp gap—market may be overpricing Dem dominance."

tweet_2 = f"""Evidence:
• Democrats need 3 net flips for majority
• Cook: 42 battlegrounds; D hold 22, R hold 20
• Midterm pattern: party in power loses 20-35 seats
• Strong D fundraising + momentum

{AFFILIATE_X}

⚠️ Not financial advice."""

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
    "direction": "NO_UNDERPRICED",
    "approval_required": False,
    "paperclip_issue": "PRO-378",
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
os.system("cd /home/slova/ProbBrain && python3 tools/sync_dashboard.py --signal-id SIG-035")
print("✓ Dashboard synced")

print("\n✅ All done! SIG-035 published.")
print(f"   Telegram: message_id={tg_message_id}")
print(f"   X: tweets {tweet_1_id} → {tweet_2_id} → {tweet_3_id}")
