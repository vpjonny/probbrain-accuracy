#!/usr/bin/env python3
"""
Post SIG-030 (Iranian regime fall by June 30) to Telegram and X.
"""

import os
import sys
import json
import httpx
import tweepy
from datetime import datetime
from dotenv import load_dotenv

# Add tools to path for imports
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

# Signal data
SIGNAL = {
    "signal_id": "SIG-030",
    "market": "Will the Iranian regime fall by June 30?",
    "market_price_yes": 0.195,
    "our_estimate": 0.075,
    "gap_pct": 12.0,
    "confidence": "MEDIUM",
    "volume_usdc": 22254903.092957396,
    "close_date": "2026-06-30",
    "market_id": "958443",
    "polymarket_slug": "will-the-iranian-regime-fall-by-june-30",
}

EVIDENCE = [
    "Iran in active military conflict with Israel (Operation Epic Fury, Feb 28 start)",
    "Iran fired 300+ ballistic missiles at central Israel; Israel struck IRGC targets in Isfahan",
    "Regime remains operational; Khamenei and IRGC leadership directing operations",
    "No major popular uprising or internal military coup in progress; IRGC controls security apparatus",
    "Modern regime collapses: ~5% base rate over 6-month windows; Iran-specific: 0 collapses since 1979",
    "Even escalated conflict rarely triggers regime collapse within 3 months (typically takes years)",
]

COUNTER_EVIDENCE = "Despite active military escalation and operational strikes exchanged, regime collapse historically requires either internal military coup, widespread popular uprising, or complete military defeat—none evident in current conflict dynamics. 40+ years of regime survival through multiple crises (Iraq war, sanctions, internal dissent) suggests resilience."

# ============================================================================
# TELEGRAM MESSAGE
# ============================================================================

telegram_message = f"""🟡 MEDIUM — Lean NO

📊 Will the Iranian regime fall by June 30?

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

tweet_1 = f"Market: Iranian regime collapse by 2026-06-30 at {SIGNAL['market_price_yes']*100:.1f}% YES. Our estimate: {SIGNAL['our_estimate']*100:.1f}%. Gap: {SIGNAL['gap_pct']:.1f}pp. Base rate for regime collapse over 6 months is ~5%; current escalation raises it to 7.5%. Iran has survived 40+ years and multiple crises."

tweet_2 = f"""Evidence:
• Iran in active military conflict with Israel (Operation Epic Fury)
• Fired 300+ ballistic missiles; Israel struck IRGC targets
• Regime remains operational; Khamenei and IRGC directing ops
• No major uprising or military coup in progress
• Historical base rate: 0 regime collapses in Iran since 1979

{AFFILIATE_X}

⚠️ Not financial advice. Trade at your own risk."""

tweet_3 = f"""We track every call publicly → {DASHBOARD_URL}

Get signals on Telegram: https://t.me/ProbBrain

Follow @ProbBrain for more.

#Iran #MiddleEast"""

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

# Generate and upload market card
print("🖼️ Generating market card screenshot...")
media_id = generate_and_upload_market_card(
    market_question=SIGNAL["market"],
    market_price_yes=SIGNAL["market_price_yes"],
    our_estimate=SIGNAL["our_estimate"],
    gap_pct=SIGNAL["gap_pct"],
    confidence=SIGNAL["confidence"],
    twitter_client=client,
    volume_usdc=SIGNAL["volume_usdc"]
)

if media_id:
    r1 = client.create_tweet(text=tweet_1, media_ids=[media_id])
    print(f"✓ Tweet 1 posted with market card (ID: {r1.data['id']})")
else:
    r1 = client.create_tweet(text=tweet_1)
    print(f"✓ Tweet 1 posted without screenshot (ID: {r1.data['id']})")
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
os.system("cd /home/slova/ProbBrain && python3 tools/sync_dashboard.py --signal-id SIG-030")
print("✓ Dashboard synced")

print("\n✅ All done! SIG-030 published.")
print(f"   Telegram: message_id={tg_message_id}")
print(f"   X: tweets {tweet_1_id} → {tweet_2_id} → {tweet_3_id}")
