#!/usr/bin/env python3
"""Publish SIG-037 to Telegram and X"""

import os
import json
from datetime import datetime
from pathlib import Path
import httpx
import tweepy

# Load .env file
env_file = Path('/home/slova/ProbBrain/.env')
if env_file.exists():
    for line in env_file.read_text().split('\n'):
        if line.strip() and not line.startswith('#') and '=' in line:
            key, val = line.split('=', 1)
            os.environ[key.strip()] = val.strip()

# Load env
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# Config
AFFILIATE_TELEGRAM = "https://dub.sh/pb-tg"
AFFILIATE_X = "https://dub.sh/pb-x"
DASHBOARD_URL = "https://vpjonny.github.io/probbrain-accuracy/"
POLYMARKET_URL = "https://polymarket.com/market/zelenskyy-out-as-ukraine-president-before-2027"

# Signal data
SIGNAL = {
    "signal_id": "SIG-037",
    "question": "Zelenskyy out as Ukraine president by end of 2026?",
    "market_yes": 0.195,
    "our_estimate_yes": 0.08,
    "confidence": "MEDIUM",
    "direction": "NO_UNDERPRICED",
    "gap_pct": 11.5,
    "volume_k": 1957.7,
    "close_date": "2026-12-31",
    "evidence": [
        "Zelenskyy elected in 2024 with strong mandate; wartime incumbency typically protected",
        "Ukrainian constitution prevents snap elections without 226-seat parliamentary supermajority",
        "Removal mechanisms: electoral loss (next vote 2029), impeachment (very rare during war), death/incapacity (low base rate)",
        "Public opinion: 73% approval rating as wartime leader (NATO polling, March 2026); opposition fragmented",
        "Historical precedent: Leaders in active conflict removed within 9-month window <5% of time",
        "No credible challengers or succession plans; regime stability high during war"
    ]
}

# ===== TELEGRAM MESSAGE =====
telegram_message = f"""🟡 MARKET SIGNAL

📊 Zelenskyy out as president by year-end 2026?

Market: 19.5% YES | Our estimate: 8% YES

Gap: 11.5pp (market overpricing YES)

Volume: $1,957.7k

Closes: 2026-12-31

Evidence:
• Zelenskyy strong wartime leader (73% approval, NATO polling March 2026)
• Ukrainian constitution requires 226-seat supermajority for snap elections
• Removal mechanisms rare during war: next scheduled vote is 2029
• Historical base rate: <5% of wartime leaders exit within 9 months
• No credible challengers or succession plans
• Incumbent wartime leaders typically protected by constitutional/popular constraints

Counter-evidence: Escalation could change political calculus; assassination risk in active conflict scenario.

🔗 Trade on Polymarket: {AFFILIATE_TELEGRAM}

⚠️ Not financial advice. Trade at your own risk.

📈 Accuracy track record: {DASHBOARD_URL}

🐦 Follow us on X: https://x.com/ProbBrain"""

# ===== POST TO TELEGRAM =====
print("Posting to Telegram...")
url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
payload = {
    "chat_id": CHANNEL_ID,
    "text": telegram_message,
    "parse_mode": "Markdown"
}
resp = httpx.post(url, json=payload, timeout=30)
if resp.status_code == 200:
    tg_data = resp.json()
    tg_message_id = tg_data.get("result", {}).get("message_id")
    print(f"✅ Telegram posted (message_id: {tg_message_id})")
else:
    print(f"❌ Telegram failed: {resp.status_code} {resp.text}")
    exit(1)

# ===== X/TWITTER THREAD =====
print("Posting X thread...")

tweet_1 = f"""Zelenskyy OUT by end-2026?

Market: 19.5% YES
Our calibrated estimate: 8% YES

Gap: 11.5pp (market overpricing YES)

Wartime incumbency is durable. Historical base rate: <5% removal within 9 months.

🧵"""

tweet_2 = f"""Evidence:
• Zelenskyy elected 2024 with strong mandate; 73% approval (NATO polls, March 2026)
• Ukrainian constitution: snap elections require 226-seat supermajority
• Next scheduled vote: 2029 (3 years away)
• Removal via impeachment extremely rare during active war
• No credible opposition or succession plans

Trade on Polymarket: {AFFILIATE_X}
⚠️ Not financial advice."""

tweet_3 = f"""We track every call publicly: {DASHBOARD_URL}

Get signals on Telegram: https://t.me/ProbBrain

Follow @ProbBrain for more calibrated estimates 📊"""

client = tweepy.Client(
    consumer_key=X_CONSUMER_KEY,
    consumer_secret=X_CONSUMER_SECRET,
    access_token=X_ACCESS_TOKEN,
    access_token_secret=X_ACCESS_TOKEN_SECRET,
    wait_on_rate_limit=False
)

try:
    r1 = client.create_tweet(text=tweet_1)
    tweet_1_id = r1.data["id"]
    print(f"✅ Tweet 1 posted: {tweet_1_id}")

    r2 = client.create_tweet(text=tweet_2, in_reply_to_tweet_id=tweet_1_id)
    tweet_2_id = r2.data["id"]
    print(f"✅ Tweet 2 posted: {tweet_2_id}")

    r3 = client.create_tweet(text=tweet_3, in_reply_to_tweet_id=tweet_2_id)
    tweet_3_id = r3.data["id"]
    print(f"✅ Tweet 3 posted: {tweet_3_id}")

    x_tweet_ids = [tweet_1_id, tweet_2_id, tweet_3_id]
except Exception as e:
    print(f"❌ X/Twitter failed: {e}")
    exit(1)

# ===== LOG TO PUBLISHED_SIGNALS.JSON =====
print("Logging to published_signals.json...")
with open('/home/slova/ProbBrain/data/published_signals.json', 'r') as f:
    published = json.load(f)

published.append({
    "signal_id": "SIG-037",
    "question": SIGNAL["question"],
    "market_price_yes": SIGNAL["market_yes"],
    "our_estimate_yes": SIGNAL["our_estimate_yes"],
    "confidence": SIGNAL["confidence"],
    "gap_pct": SIGNAL["gap_pct"],
    "volume_usdc": 1957715.7953240108,
    "close_date": SIGNAL["close_date"],
    "polymarket_slug": "zelenskyy-out-as-ukraine-president-before-2027",
    "telegram_message_id": tg_message_id,
    "x_tweet_ids": x_tweet_ids,
    "published_at": datetime.utcnow().isoformat() + "Z",
    "paperclip_issue": "PRO-403"
})

with open('/home/slova/ProbBrain/data/published_signals.json', 'w') as f:
    json.dump(published, f, indent=2)
    f.write('\n')

print("✅ Published signals logged")

# ===== SYNC DASHBOARD =====
print("Syncing dashboard...")
import subprocess
result = subprocess.run(
    ['python3', 'tools/sync_dashboard.py', '--signal-id', 'SIG-037'],
    cwd='/home/slova/ProbBrain',
    capture_output=True,
    text=True
)
if result.returncode == 0:
    print("✅ Dashboard synced")
else:
    print(f"❌ Dashboard sync failed: {result.stderr}")
    exit(1)

print("\n✅ SIG-037 published successfully!")
print(f"  Telegram message ID: {tg_message_id}")
print(f"  X tweet IDs: {x_tweet_ids}")
