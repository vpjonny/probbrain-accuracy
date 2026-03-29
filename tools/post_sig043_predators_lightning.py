#!/usr/bin/env python3
"""
Post SIG-043 (Predators vs. Lightning) to Telegram and X.
WARNING: Market closes 2026-03-29T21:00 (closes today).
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
    "signal_id": "SIG-043",
    "market": "Predators vs. Lightning",
    "market_price_yes": 0.355,
    "our_estimate": 0.38,
    "gap_pct": 2.5,
    "confidence": "MEDIUM",
    "volume_usdc": 949495.9869170007,
    "close_date": "2026-03-29",
    "market_id": "1483889",
    "polymarket_slug": "nhl-nsh-tb-2026-03-29",
}

EVIDENCE = [
    "Lightning: 45-21-6 (96 pts, home), Predators: 34-30-9 (77 pts, away)",
    "Lightning on winning streak, Predators on losing streak",
    "Star player differential: Kucherov 121 pts vs O'Reilly 66 pts",
    "Lightning 8-2 in last 10 H2H meetings",
    "7.5 betting spread implies ~25-26% for Predators vs Polymarket 22.5%",
]

COUNTER_EVIDENCE = "Playoff hockey contains inherent variance; away teams occasionally perform above expected probability, and short-term streaks (winning/losing) can reverse mid-series. However, team quality differential and matchup history favor Lightning."

# ============================================================================
# TELEGRAM MESSAGE
# ============================================================================

telegram_message = f"""🟡 MEDIUM — Lean YES

📊 Predators vs. Lightning

Market: {SIGNAL['market_price_yes']*100:.1f}% YES | Our estimate: {SIGNAL['our_estimate']*100:.1f}% YES

Gap: {SIGNAL['gap_pct']:.1f}pp (market underpricing YES)

Volume: ${SIGNAL['volume_usdc']/1e6:.2f}M

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

tweet_1 = f"Lightning (45-21-6, home) vs Predators (34-30-9, away). Market says {SIGNAL['market_price_yes']*100:.1f}% for Predators, but 7.5-point spread implies ~25-26% probability. Gap: {SIGNAL['gap_pct']:.1f}pp."

tweet_2 = f"""Evidence:
• Lightning: 96 pts, home; Predators: 77 pts, away
• Lightning on streak; Predators on losing streak
• Kucherov (121 pts) vs O'Reilly (66 pts) star differential
• Lightning 8-2 in last 10 meetings

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
os.system("cd /home/slova/ProbBrain && python3 tools/sync_dashboard.py --signal-id SIG-043")
print("✓ Dashboard synced")

print("\n✅ All done! SIG-043 published.")
print(f"   Telegram: message_id={tg_message_id}")
print(f"   X: tweets {tweet_1_id} → {tweet_2_id} → {tweet_3_id}")
