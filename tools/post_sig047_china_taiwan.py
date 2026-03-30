#!/usr/bin/env python3
"""
Post SIG-047 (China invades Taiwan before GTA VI) to Telegram and X.
- Market: 540820
- Gap: 37pp (HIGH confidence)
- Rate limit check: respects 30-min minimum between posts
- Screenshot: includes Polymarket market card on X thread
"""

import os
import sys
import json
from datetime import datetime
import httpx
import tweepy
from pathlib import Path

# Add tools dir to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polymarket_screenshot import generate_and_upload_market_card

# Load environment and config
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# Signal data
SIGNAL_ID = "SIG-047"
MARKET_ID = "540820"
MARKET_QUESTION = "Will China invade Taiwan before GTA VI releases?"
MARKET_PRICE_YES = 0.52
OUR_ESTIMATE = 0.15
GAP_PCT = 37.0
CONFIDENCE = "HIGH"
VOLUME_USDC = 1519480
CLOSE_DATE = "2026-07-31"
POLYMARKET_SLUG = "china-invades-taiwan-before-gta-vi"

TELEGRAM_MESSAGE = """🔴 HIGH MARKET SIGNAL

📊 Will China invade Taiwan before GTA VI releases?

Market: 52% YES | Our estimate: 15% YES
Gap: 37pp (market overpricing YES)
Volume: $1.5M
Closes: 2026-07-31

Evidence:
• US intelligence (March 26, 2026): invasion unlikely, not currently planned
• Economic constraints: slowdown, property crisis, unemployment
• Military view: amphibious assault risky and complex
• Expert consensus: 2026 not assessed as conflict year

Counter-evidence: Market prices non-zero escalation risk; military modernization concerns, but logistics and US nuclear umbrella weigh against 2026 invasion.

🔗 Trade on Polymarket: https://dub.sh/pb-tg

⚠️ Not financial advice. Trade at your own risk.
📈 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/
🐦 Follow us on X: https://x.com/ProbBrain"""

def check_rate_limit(published_signals_path: str) -> bool:
    """Check if 30 minutes have passed since last post."""
    try:
        with open(published_signals_path) as f:
            sigs = json.load(f)
        if not sigs:
            return True

        last_sig = sigs[-1]
        last_posted = last_sig.get('actually_posted_at') or last_sig.get('telegram_posted_at')
        if not last_posted:
            return True

        last_time = datetime.fromisoformat(last_posted.replace('Z', '+00:00'))
        now = datetime.now(last_time.tzinfo)
        gap_sec = (now - last_time).total_seconds()

        print(f"  Last post: {last_posted}")
        print(f"  Gap: {gap_sec/60:.1f} min")

        if gap_sec < 1800:  # 30 min minimum
            print(f"  ✗ Rate limit violated: need {1800-gap_sec:.0f}s more before next post")
            return False

        print(f"  ✓ Rate limit OK (gap > 30 min)")
        return True
    except Exception as e:
        print(f"  Warning: could not check rate limit: {e}")
        return True

def post_telegram(message: str) -> int:
    """Post to Telegram. Returns message_id."""
    print(f"[Telegram] Posting SIG-047...")

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        resp = httpx.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        msg_id = data['result']['message_id']
        print(f"  ✓ Posted to Telegram (message_id: {msg_id})")
        return msg_id
    except Exception as e:
        print(f"  ✗ Telegram post failed: {e}")
        raise

def post_x_thread(market_card_media_id: str = None) -> list:
    """Post X thread with market card screenshot. Returns [tweet_1_id, tweet_2_id, tweet_3_id]."""
    print(f"[X] Posting SIG-047 thread...")

    client = tweepy.Client(
        consumer_key=X_CONSUMER_KEY,
        consumer_secret=X_CONSUMER_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )

    # Tweet 1: Core insight + gap + screenshot
    tweet_1_text = f"🚨 Market pricing China-Taiwan invasion at 52%. Our estimate: 15%. That's a 37pp gap.\n\nWhy? US intelligence says invasion unlikely in 2026. Economic constraints + military risks don't support near-term action.\n\nFull analysis thread 👇 #Geopolitics #ProbabilisticForecasting"

    media_ids = None
    if market_card_media_id:
        media_ids = [market_card_media_id]

    try:
        r1 = client.create_tweet(text=tweet_1_text, media_ids=media_ids)
        tweet_1_id = r1.data['id']
        print(f"  ✓ Tweet 1 posted (ID: {tweet_1_id})")

        # Tweet 2: Evidence + link
        tweet_2_text = f"Evidence:\n• US intel (March 26): 'not currently planning' invasion; 'imminent attack unlikely'\n• Economic headwinds: slowdown, property crisis, youth unemployment\n• Military view: amphibious assault is 'highly risky and complex'\n• Expert consensus: 2026 not assessed as conflict year\n\nTrade on Polymarket: https://dub.sh/pb-x"

        r2 = client.create_tweet(text=tweet_2_text, in_reply_to_tweet_id=tweet_1_id)
        tweet_2_id = r2.data['id']
        print(f"  ✓ Tweet 2 posted (ID: {tweet_2_id})")

        # Tweet 3: Dashboard + follow + join Telegram
        tweet_3_text = f"We track every call publicly → https://vpjonny.github.io/probbrain-accuracy/\n\nGet signals on Telegram: https://t.me/ProbBrain\nFollow @ProbBrain for more market-driven forecasts.\n\n⚠️ Not financial advice. Trade at your own risk."

        r3 = client.create_tweet(text=tweet_3_text, in_reply_to_tweet_id=tweet_2_id)
        tweet_3_id = r3.data['id']
        print(f"  ✓ Tweet 3 posted (ID: {tweet_3_id})")

        return [tweet_1_id, tweet_2_id, tweet_3_id]
    except Exception as e:
        print(f"  ✗ X thread posting failed: {e}")
        raise

def log_published_signal(telegram_msg_id: int, x_tweet_ids: list) -> None:
    """Log signal to published_signals.json."""
    print(f"[Logging] Recording SIG-047 to published_signals.json...")

    published_path = "/home/slova/ProbBrain/data/published_signals.json"

    try:
        with open(published_path) as f:
            published = json.load(f)
    except FileNotFoundError:
        published = []

    signal_entry = {
        "signal_id": SIGNAL_ID,
        "market_id": MARKET_ID,
        "polymarket_slug": POLYMARKET_SLUG,
        "question": MARKET_QUESTION,
        "category": "geopolitics",
        "direction": "NO_UNDERPRICED",
        "confidence": CONFIDENCE,
        "market_price": MARKET_PRICE_YES,
        "market_price_at_signal": MARKET_PRICE_YES,
        "our_estimate": OUR_ESTIMATE,
        "our_calibrated_estimate": OUR_ESTIMATE,
        "gap_pct": GAP_PCT,
        "volume_usdc": VOLUME_USDC,
        "close_date": CLOSE_DATE,
        "evidence": [
            "US intelligence (March 26, 2026): invasion unlikely, not currently planned",
            "Economic constraints: slowdown, property crisis, unemployment",
            "Military view: amphibious assault risky and complex",
            "Expert consensus: 2026 not assessed as conflict year"
        ],
        "counter_evidence": "Market prices non-zero escalation risk; military modernization concerns, but logistics and US nuclear umbrella weigh against 2026 invasion.",
        "status": "published",
        "resolved": False,
        "outcome": None,
        "brier_score": None,
        "signal_number": 47,
        "platforms": ["telegram", "x"],
        "telegram_message_id": telegram_msg_id,
        "telegram_posted_at": datetime.utcnow().isoformat() + "Z",
        "x_tweet_ids": {
            "tweet_1": x_tweet_ids[0],
            "tweet_2": x_tweet_ids[1],
            "tweet_3": x_tweet_ids[2]
        },
        "x_posted_at": datetime.utcnow().isoformat() + "Z"
    }

    published.append(signal_entry)

    with open(published_path, 'w') as f:
        json.dump(published, f, indent=2)

    print(f"  ✓ SIG-047 logged to published_signals.json")

def sync_dashboard() -> None:
    """Sync dashboard after publishing."""
    print(f"[Dashboard] Syncing accuracy dashboard...")

    try:
        # Run the sync script
        import subprocess
        result = subprocess.run(
            [sys.executable, "/home/slova/ProbBrain/tools/sync_dashboard.py", "--signal-id", SIGNAL_ID],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print(f"  ✓ Dashboard synced")
        else:
            print(f"  ⚠ Dashboard sync had issues: {result.stderr}")
    except Exception as e:
        print(f"  ⚠ Dashboard sync skipped: {e}")

def main():
    print(f"\n{'='*60}")
    print(f"SIG-047 Publishing Script")
    print(f"{'='*60}\n")

    published_path = "/home/slova/ProbBrain/data/published_signals.json"

    # Check rate limit
    print(f"[Rate Limit] Checking 30-min gap...")
    if not check_rate_limit(published_path):
        print(f"\n✗ Rate limit check failed. Do not post.")
        sys.exit(1)

    # Generate market card and upload to Twitter
    print(f"\n[Market Card] Generating and uploading screenshot...")
    twitter_client = tweepy.Client(
        consumer_key=X_CONSUMER_KEY,
        consumer_secret=X_CONSUMER_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )

    try:
        media_id = generate_and_upload_market_card(
            market_question=MARKET_QUESTION,
            market_price_yes=MARKET_PRICE_YES,
            our_estimate=OUR_ESTIMATE,
            gap_pct=GAP_PCT,
            confidence=CONFIDENCE,
            twitter_client=twitter_client,
            volume_usdc=VOLUME_USDC
        )
        print(f"  ✓ Market card uploaded (media_id: {media_id})")
    except Exception as e:
        print(f"  ⚠ Market card generation failed: {e}")
        media_id = None

    # Post to Telegram
    print(f"\n[Posting] Publishing to platforms...")
    try:
        telegram_msg_id = post_telegram(TELEGRAM_MESSAGE)
    except Exception as e:
        print(f"✗ Publishing failed at Telegram: {e}")
        sys.exit(1)

    # Post to X
    try:
        x_tweet_ids = post_x_thread(media_id)
    except Exception as e:
        print(f"✗ Publishing failed at X: {e}")
        sys.exit(1)

    # Log to published_signals.json
    try:
        log_published_signal(telegram_msg_id, x_tweet_ids)
    except Exception as e:
        print(f"⚠ Logging failed: {e}")

    # Sync dashboard
    sync_dashboard()

    print(f"\n{'='*60}")
    print(f"✓ SIG-047 published successfully!")
    print(f"  Telegram: {telegram_msg_id}")
    print(f"  X thread: {x_tweet_ids[0]}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
