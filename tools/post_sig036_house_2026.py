#!/usr/bin/env python3
"""
Post SIG-036 (House control 2026) to Telegram and X.
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
    "signal_id": "SIG-036",
    "market": "Will the Republican Party control the House after the 2026 Midterm elections?",
    "market_price_yes": 0.155,
    "our_estimate": 0.31,
    "gap_pct": 15.5,
    "confidence": "MEDIUM",
    "volume_usdc": 1985461.8658799909,
    "close_date": "2026-11-03",
    "market_id": "562803",
    "polymarket_slug": "will-the-republican-party-control-the-house-after-the-2026-midterm-elections",
}

EVIDENCE = [
    "Race to the WH March 2026: Democrats at 69% odds to win House, Republicans at ~31%",
    "Democrats need only 3 net seat flips to gain majority (218 needed, current GOP narrow advantage)",
    "Cook Political Report 2026 House ratings: 42 battleground districts (12% of total), Democrats hold 22, Republicans hold 20",
    "Historical midterm pattern: Party holding presidency loses 20-35 seats on average. Trump won 2024, faces headwind in 2026.",
    "Democrats have individual-donor fundraising advantage, indicating engaged base and momentum from recent special elections",
    "Current GOP House majority: narrow and vulnerable to even modest swing (need to hold all but ~9 seats)",
]

COUNTER_EVIDENCE = "Forecasts made 7-8 months pre-election can shift 5-10pp based on economic conditions, scandal, or campaign dynamics—market pricing may reflect appropriate caution about long-term volatility."

# ============================================================================
# TELEGRAM MESSAGE
# ============================================================================

telegram_message = f"""🟡 MEDIUM MARKET SIGNAL

📊 Will Republicans control the House in 2026?

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

• {EVIDENCE[5]}

Counter-evidence: {COUNTER_EVIDENCE}

🔗 Trade on Polymarket: {AFFILIATE_TG}

⚠️ Not financial advice. Trade at your own risk.

📈 Accuracy track record: {DASHBOARD_URL}

🐦 Follow us on X: https://x.com/ProbBrain
"""

# ============================================================================
# X THREAD
# ============================================================================

tweet_1 = f"Republicans polling at ~31% to control House in 2026 per latest forecasts, but the market says 15.5%. That's a {SIGNAL['gap_pct']:.1f}pp gap—market may be underpricing GOP odds."

tweet_2 = f"""• Race to the WH: Republicans ~31% to hold House
• Cook Political: 42 battlegrounds, Dems in 22, GOP in 20
• Historical pattern: President's party loses 20-35 seats in midterms
• Dem donor advantage signals momentum

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
    "paperclip_issue": "PRO-377",
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
os.system("cd /home/slova/ProbBrain && python3 tools/sync_dashboard.py --signal-id SIG-036")
print("✓ Dashboard synced")

print("\n✅ All done! SIG-036 published.")
print(f"   Telegram: message_id={tg_message_id}")
print(f"   X: tweets {tweet_1_id} → {tweet_2_id} → {tweet_3_id}")
