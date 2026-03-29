#!/usr/bin/env python3
"""
Core signal posting function with automated Polymarket market card generation.

This is the standard workflow used by all Signal Publisher posting scripts.
Market cards are automatically generated and attached to the first tweet.

Usage:
  from post_signal_core import post_signal

  post_signal(
      signal_id="SIG-123",
      market_question="Will X happen by date?",
      market_price_yes=0.515,
      our_estimate=0.04,
      gap_pct=47.5,
      confidence="HIGH",
      volume_usdc=1234567,
      close_date="2026-07-01",
      polymarket_slug="market-slug",
      market_id="123456",
      evidence=["point 1", "point 2"],
      counter_evidence="opposing view",
      telegram_message=None,  # Optional, generated if None
      tweet_1=None,           # Optional, generated if None
      tweet_2=None,           # Optional, generated if None
      tweet_3=None,           # Optional, generated if None
      direction="YES_UNDERPRICED",
      approval_required=False,
      paperclip_issue="PRO-###"
  )
"""

import os
import json
import httpx
import tweepy
from datetime import datetime
from dotenv import load_dotenv
import sys

# Add tools to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from polymarket_screenshot import generate_and_upload_market_card

# Load .env
load_dotenv("/home/slova/ProbBrain/.env")

# Credentials
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
X_CONSUMER_KEY = os.getenv("X_CONSUMER_KEY")
X_CONSUMER_SECRET = os.getenv("X_CONSUMER_SECRET")
X_ACCESS_TOKEN = os.getenv("X_ACCESS_TOKEN")
X_ACCESS_TOKEN_SECRET = os.getenv("X_ACCESS_TOKEN_SECRET")

# Config
AFFILIATE_TG = "https://dub.sh/pb-tg"
AFFILIATE_X = "https://dub.sh/pb-x"
DASHBOARD_URL = "https://vpjonny.github.io/probbrain-accuracy/"

def post_signal(
    signal_id: str,
    market_question: str,
    market_price_yes: float,
    our_estimate: float,
    gap_pct: float,
    confidence: str,
    volume_usdc: float,
    close_date: str,
    polymarket_slug: str,
    market_id: str,
    evidence: list,
    counter_evidence: str,
    direction: str,
    approval_required: bool = False,
    paperclip_issue: str = None,
    telegram_message: str = None,
    tweet_1: str = None,
    tweet_2: str = None,
    tweet_3: str = None,
    dry_run: bool = False
) -> dict:
    """
    Post a signal to Telegram and X with automated market card screenshot.

    This is the standard workflow. Market cards are ALWAYS generated and attached
    to the first tweet unless explicitly disabled.

    Args:
        signal_id: Signal identifier (e.g., "SIG-123")
        market_question: Market question text
        market_price_yes: Market price (0-1 or 0-100)
        our_estimate: Our estimate (0-1 or 0-100)
        gap_pct: Gap in percentage points
        confidence: HIGH or MEDIUM
        volume_usdc: Market volume in USDC
        close_date: Market close date (YYYY-MM-DD or ISO format)
        polymarket_slug: Polymarket URL slug
        market_id: Polymarket market ID
        evidence: List of evidence points (strings)
        counter_evidence: One sentence acknowledging opposing view
        direction: YES_UNDERPRICED or NO_UNDERPRICED
        approval_required: Boolean
        paperclip_issue: Paperclip issue ID (e.g., "PRO-123")
        telegram_message: Optional custom Telegram message. If None, auto-generated.
        tweet_1: Optional custom first tweet. If None, generic used.
        tweet_2: Optional custom second tweet.
        tweet_3: Optional custom third tweet.
        dry_run: If True, don't actually post (just show what would be posted)

    Returns:
        dict with posting results:
        {
            "signal_id": "SIG-123",
            "status": "success" or "error",
            "telegram_message_id": "12345",
            "x_tweet_ids": ["id1", "id2", "id3"],
            "market_card_included": True/False,
            "error": "error message if any"
        }
    """
    result = {
        "signal_id": signal_id,
        "status": "success",
        "telegram_message_id": None,
        "x_tweet_ids": [],
        "market_card_included": False,
        "error": None
    }

    try:
        # ============================================================================
        # TELEGRAM MESSAGE
        # ============================================================================

        if telegram_message is None:
            # Auto-generate
            badge = "🔴 HIGH" if confidence == "HIGH" else "🟡 MEDIUM"
            direction_text = "YES" if our_estimate > market_price_yes else "NO"
            gap_direction = "overpricing" if gap_pct > 0 else "underpricing"

            evidence_text = "\n\n".join([f"• {e}" for e in evidence])

            telegram_message = f"""{badge} — Bet {direction_text}

📊 {market_question}

Market: {market_price_yes*100:.1f}% YES | Our estimate: {our_estimate*100:.1f}% YES

Gap: {gap_pct:.1f}pp (market {gap_direction} YES)

Volume: ${volume_usdc/1e6:.2f}M

Closes: {close_date}

Evidence:

{evidence_text}

Counter-evidence: {counter_evidence}

🔗 Trade on Polymarket: {AFFILIATE_TG}

⚠️ Not financial advice. Trade at your own risk.

📈 Accuracy track record: {DASHBOARD_URL}

🐦 Follow us on X: https://x.com/ProbBrain
"""

        if not dry_run:
            print(f"[1/5] Posting to Telegram...")
            url_tg = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload_tg = {
                "chat_id": CHANNEL_ID,
                "text": telegram_message,
                "parse_mode": "Markdown"
            }
            resp_tg = httpx.post(url_tg, json=payload_tg, timeout=30)
            resp_tg.raise_for_status()
            result["telegram_message_id"] = str(resp_tg.json()["result"]["message_id"])
            print(f"✓ Telegram message posted (ID: {result['telegram_message_id']})")
        else:
            print(f"[DRY RUN] Telegram message ready (chars: {len(telegram_message)})")

        # ============================================================================
        # X THREAD (WITH AUTOMATED MARKET CARD)
        # ============================================================================

        print("[2/5] Preparing X thread with market card...")

        if not dry_run:
            client = tweepy.Client(
                consumer_key=X_CONSUMER_KEY,
                consumer_secret=X_CONSUMER_SECRET,
                access_token=X_ACCESS_TOKEN,
                access_token_secret=X_ACCESS_TOKEN_SECRET,
            )

            # AUTOMATED: Always generate and upload market card
            print("[3/5] Generating market card screenshot...")
            media_id = generate_and_upload_market_card(
                market_question=market_question,
                market_price_yes=market_price_yes,
                our_estimate=our_estimate,
                gap_pct=gap_pct,
                confidence=confidence,
                twitter_client=client,
                volume_usdc=volume_usdc
            )

            if media_id:
                result["market_card_included"] = True
                print(f"✓ Market card generated and uploaded")
            else:
                print(f"⚠️ Market card generation skipped, posting without it")

            # Default tweets if not provided
            if tweet_1 is None:
                tweet_1 = f"{market_question}\n\nMarket: {market_price_yes*100:.1f}% YES | Our estimate: {our_estimate*100:.1f}% YES | Gap: {gap_pct:.1f}pp [thread]"
            if tweet_2 is None:
                tweet_2 = f"Evidence:\n• {evidence[0]}\n• {evidence[1] if len(evidence) > 1 else 'See full analysis'}\n\n{AFFILIATE_X}\n\n⚠️ Not financial advice."
            if tweet_3 is None:
                tweet_3 = f"We track every call publicly → {DASHBOARD_URL}\n\nGet signals on Telegram: https://t.me/ProbBrain\n\nFollow @ProbBrain for more."

            # Post tweets
            print("[4/5] Posting to X...")

            # Tweet 1 with media
            if media_id:
                r1 = client.create_tweet(text=tweet_1, media_ids=[media_id])
                print(f"✓ Tweet 1 posted with market card")
            else:
                r1 = client.create_tweet(text=tweet_1)
                print(f"✓ Tweet 1 posted (no market card)")

            tweet_1_id = r1.data["id"]
            result["x_tweet_ids"].append(str(tweet_1_id))

            r2 = client.create_tweet(text=tweet_2, in_reply_to_tweet_id=tweet_1_id)
            tweet_2_id = r2.data["id"]
            result["x_tweet_ids"].append(str(tweet_2_id))
            print(f"✓ Tweet 2 posted")

            r3 = client.create_tweet(text=tweet_3, in_reply_to_tweet_id=tweet_2_id)
            tweet_3_id = r3.data["id"]
            result["x_tweet_ids"].append(str(tweet_3_id))
            print(f"✓ Tweet 3 posted")
        else:
            print(f"[DRY RUN] X thread ready (3 tweets, market card enabled)")

        # ============================================================================
        # LOG TO published_signals.json
        # ============================================================================

        if not dry_run:
            print("[5/5] Logging to published_signals.json...")

            published_file = "/home/slova/ProbBrain/data/published_signals.json"
            with open(published_file, "r") as f:
                published = json.load(f)

            entry = {
                "signal_id": signal_id,
                "market_id": market_id,
                "market_question": market_question,
                "market_price_yes": market_price_yes,
                "our_estimate": our_estimate,
                "gap_pct": gap_pct,
                "confidence": confidence,
                "volume_usdc": volume_usdc,
                "close_date": close_date,
                "polymarket_slug": polymarket_slug,
                "published_at": datetime.utcnow().isoformat() + "Z",
                "telegram_message_id": str(result["telegram_message_id"]) if result["telegram_message_id"] else None,
                "x_tweet_ids": result["x_tweet_ids"],
                "x_has_market_card": result["market_card_included"],
                "evidence": evidence,
                "counter_evidence": counter_evidence,
                "direction": direction,
                "approval_required": approval_required,
                "paperclip_issue": paperclip_issue,
            }

            published.append(entry)

            with open(published_file, "w") as f:
                json.dump(published, f, indent=2)

            print(f"✓ Logged to published_signals.json")

            # ============================================================================
            # SYNC DASHBOARD
            # ============================================================================

            print("[5/5] Syncing dashboard...")
            os.system(f"cd /home/slova/ProbBrain && python3 tools/sync_dashboard.py --signal-id {signal_id}")
            print("✓ Dashboard synced")

            # Summary
            print(f"\n✅ {signal_id} posted successfully")
            print(f"   Telegram: {result['telegram_message_id']}")
            print(f"   X tweets: {' → '.join(result['x_tweet_ids'])}")
            print(f"   Market card: {'✓ Included' if result['market_card_included'] else '✗ Skipped'}")

    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        print(f"\n✗ Error: {e}")

    return result


if __name__ == "__main__":
    # Example usage
    result = post_signal(
        signal_id="SIG-TEST",
        market_question="Test market question?",
        market_price_yes=0.5,
        our_estimate=0.3,
        gap_pct=20,
        confidence="MEDIUM",
        volume_usdc=1000000,
        close_date="2026-12-31",
        polymarket_slug="test-market",
        market_id="999999",
        evidence=["Evidence 1", "Evidence 2", "Evidence 3"],
        counter_evidence="Counter-argument",
        direction="NO_UNDERPRICED",
        approval_required=False,
        paperclip_issue="PRO-999",
        dry_run=True  # Test mode
    )

    print(f"\nResult: {json.dumps(result, indent=2)}")
