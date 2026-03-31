#!/usr/bin/env python3
"""
Publish SIG-048 (Bitcoin $1M before GTA VI) to Telegram and X
CEO-approved signal with 48.35pp gap
- Includes Polymarket market card screenshot on first tweet
- 2 hashtags at the end of the final tweet
"""

import argparse
import os
import sys
import json
from datetime import datetime, timezone
import httpx
import tweepy

# Add tools dir to path for local imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polymarket_screenshot import generate_and_upload_market_card
from posting_utils import should_post_to_platform

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
    """Format tweets for X thread with hashtags only in final tweet"""
    tweet1 = f"Bitcoin hitting $1M by GTA VI release?\n\nMarket: 48.85% YES | Our: 0.5% | 48.35pp gap\n\nMarket vastly overprices extreme crypto appreciation in 4-month window. 🧵"

    evidence_text = "\n".join(f"• {e}" for e in EVIDENCE)

    tweet2 = f"""Evidence:
{evidence_text}

Counter: Bitcoin volatility + past bull runs show 1000%+ moves possible (though historical base rate for quarterly rallies is near zero).

Trade on Polymarket: {AFFILIATE_LINK}
⚠️ Not financial advice."""

    tweet3 = f"""We track every call publicly → {DASHBOARD_URL}

Get signals on Telegram: https://t.me/ProbBrain
Follow @ProbBrain for more. #Bitcoin #Crypto"""

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

def post_x(market_card_media_id: str = None):
    """Post thread to X with optional market card screenshot"""
    client = tweepy.Client(
        consumer_key=X_CONSUMER_KEY,
        consumer_secret=X_CONSUMER_SECRET,
        access_token=X_ACCESS_TOKEN,
        access_token_secret=X_ACCESS_TOKEN_SECRET,
    )

    tweet1, tweet2, tweet3 = format_x_tweets()

    # Post thread with market card on first tweet if available
    media_ids = None
    if market_card_media_id:
        media_ids = [market_card_media_id]

    r1 = client.create_tweet(text=tweet1, media_ids=media_ids)
    r2 = client.create_tweet(text=tweet2, in_reply_to_tweet_id=r1.data["id"])
    r3 = client.create_tweet(text=tweet3, in_reply_to_tweet_id=r2.data["id"])

    return [r1.data["id"], r2.data["id"], r3.data["id"]]

def log_published(telegram_msg_id: int, x_tweet_ids: list) -> None:
    """Log to published_signals.json"""
    with open("/home/slova/ProbBrain/data/published_signals.json", "r") as f:
        signals = json.load(f)

    # Update existing SIG-048 entry or create new one
    signal_entry = None
    for sig in signals:
        if sig.get("signal_id") == SIGNAL_ID:
            signal_entry = sig
            break

    if not signal_entry:
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
        }
        signals.append(signal_entry)

    # Update with posting info
    signal_entry["published_at"] = datetime.now(timezone.utc).isoformat()
    signal_entry["platforms"] = ["telegram", "x"]
    signal_entry["telegram_message_id"] = telegram_msg_id
    signal_entry["x_tweet_ids"] = {
        "tweet_1": x_tweet_ids[0],
        "tweet_2": x_tweet_ids[1],
        "tweet_3": x_tweet_ids[2]
    }
    signal_entry["status"] = "published"
    signal_entry["resolved"] = False
    signal_entry["outcome"] = None
    signal_entry["brier_score"] = None

    with open("/home/slova/ProbBrain/data/published_signals.json", "w") as f:
        json.dump(signals, f, indent=2)

def check_rate_limit(published_signals_path: str) -> bool:
    """Check if 30 minutes have passed since last post."""
    try:
        with open(published_signals_path) as f:
            sigs = json.load(f)
        if not sigs:
            return True

        last_sig = sigs[-1]
        last_posted = last_sig.get('published_at') or last_sig.get('actually_posted_at')
        if not last_posted:
            return True

        last_time = datetime.fromisoformat(last_posted.replace('Z', '+00:00'))
        now = datetime.now(last_time.tzinfo if last_time.tzinfo else timezone.utc)
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

def sync_dashboard() -> None:
    """Sync dashboard after publishing."""
    print(f"[Dashboard] Syncing accuracy dashboard...")
    try:
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
    parser = argparse.ArgumentParser(description=f"Publish {SIGNAL_ID}")
    parser.add_argument("--force", action="store_true", help="Force re-post even if already published (override dedup)")
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"{SIGNAL_ID} Publishing Script")
    print(f"{'='*60}\n")

    published_path = "/home/slova/ProbBrain/data/published_signals.json"

    # Check rate limit
    print(f"[Rate Limit] Checking 30-min gap...")
    if not check_rate_limit(published_path):
        print(f"\n✗ Rate limit check failed. Do not post.")
        sys.exit(1)

    # Dedup checks
    skip_telegram = False
    skip_x = False
    if not args.force:
        if not should_post_to_platform(SIGNAL_ID, "telegram", published_path):
            print(f"[Dedup] SKIP Telegram — {SIGNAL_ID} already posted to Telegram. Use --force to override.")
            skip_telegram = True
        if not should_post_to_platform(SIGNAL_ID, "x", published_path):
            print(f"[Dedup] SKIP X — {SIGNAL_ID} already posted to X. Use --force to override.")
            skip_x = True
        if skip_telegram and skip_x:
            print(f"\n[Dedup] {SIGNAL_ID} already published to all platforms. Nothing to do.")
            sys.exit(0)
    else:
        print(f"[Dedup] --force flag set, skipping dedup checks.")

    # Generate market card and upload to Twitter
    media_id = None
    if not skip_x:
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
                our_estimate=OUR_ESTIMATE_YES,
                gap_pct=GAP_PP,
                confidence=CONFIDENCE,
                twitter_client=twitter_client,
                volume_usdc=VOLUME_USDC
            )
            print(f"  ✓ Market card uploaded (media_id: {media_id})")
        except Exception as e:
            print(f"  ⚠ Market card generation failed: {e}")
            media_id = None

    # Post to platforms
    tg_id = None
    x_ids = None

    print(f"\n[Posting] Publishing to platforms...")
    if not skip_telegram:
        try:
            tg_id = post_telegram()
        except Exception as e:
            print(f"✗ Publishing failed at Telegram: {e}")
            sys.exit(1)
    else:
        print(f"  [Telegram] Skipped (already posted)")

    if not skip_x:
        try:
            x_ids = post_x(media_id)
        except Exception as e:
            print(f"✗ Publishing failed at X: {e}")
            sys.exit(1)
    else:
        print(f"  [X] Skipped (already posted)")

    # Log to published_signals.json
    if tg_id and x_ids:
        try:
            log_published(tg_id, x_ids)
            print(f"✓ Logged to published_signals.json")
        except Exception as e:
            print(f"⚠ Logging failed: {e}")

    # Sync dashboard
    sync_dashboard()

    print(f"\n{'='*60}")
    print(f"✓ {SIGNAL_ID} publishing complete!")
    if tg_id:
        print(f"  Telegram: {tg_id}")
    if x_ids:
        print(f"  X thread: {x_ids[0]}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
