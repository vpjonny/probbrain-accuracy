#!/usr/bin/env python3
"""
Post SIG-034: Tennessee Volunteers vs. Michigan Wolverines
Elite Eight college basketball signal
"""

import os
import json
from datetime import datetime
import httpx
import tweepy

# Signal data
SIGNAL = {
    "signal_id": "SIG-034",
    "market_question": "Tennessee Volunteers vs. Michigan Wolverines (Elite Eight)",
    "market_price_yes": 0.225,
    "our_estimate_yes": 0.26,
    "gap_pct": 3.5,
    "confidence": "MEDIUM",
    "volume_usd": 2442108.52,
    "closes": "2026-03-29T16:00:00Z",
    "polymarket_slug": "cbb-tenn-mich-2026-03-29",
}

# Config
AFFILIATE_LINK_TELEGRAM = "https://dub.sh/pb-tg"
AFFILIATE_LINK_X = "https://dub.sh/pb-x"
DASHBOARD_URL = "https://vpjonny.github.io/probbrain-accuracy/"
TELEGRAM_JOIN_LINK = "https://t.me/ProbBrain"

# Telegram message
TELEGRAM_MESSAGE = """🟡 MARKET SIGNAL

📊 Tennessee Volunteers vs. Michigan Wolverines (Elite Eight)

Market: 22.5% YES | Our estimate: 26% YES

Gap: 3.5% (market underpricing YES)

Volume: $2.4M

Closes: 2026-03-29

Evidence:

• Michigan #1 seed, 34-3 overall record, #3 ranked
• Tournament dominance: +21, +23, +13 point margins in recent wins
• Tennessee #6 seed, 25-11 overall, Cinderella story
• Betting line: Michigan -7.5 (implies ~25-26% for Tennessee)
• Expert predictions all favor Michigan by 10+ points

Counter-evidence: Elite Eight basketball is inherently volatile; Tennessee's tournament success demonstrates they can compete with top seeds.

🔗 Trade on Polymarket: {affiliate_link}

⚠️ Not financial advice. Trade at your own risk.

📈 Accuracy track record: {dashboard_url}

🐦 Follow us on X: https://x.com/ProbBrain
""".format(
    affiliate_link=AFFILIATE_LINK_TELEGRAM,
    dashboard_url=DASHBOARD_URL,
)

# X thread
X_TWEET_1 = "Tennessee trading at 22.5% vs. Michigan in Elite Eight — our estimate: 26%. Michigan's dominance (#1 seed, +21, +23, +13 margins) suggests Tennessee is slightly underpriced. 3.5pp gap."

X_TWEET_2 = """Evidence:
• Michigan: 34-3 record, #3 ranked, 7.5-point favorite
• Tennessee: 25-11, Cinderella story
• Betting consensus ~25-26% for Tennessee vs. Polymarket 22.5%
• Expert predictions all favor Michigan

Trade: {affiliate_link}
⚠️ Not financial advice.""".format(
    affiliate_link=AFFILIATE_LINK_X
)

X_TWEET_3 = """We track every call publicly: {dashboard_url}

Get signals on Telegram: {telegram_link}

Follow @ProbBrain for more.""".format(
    dashboard_url=DASHBOARD_URL,
    telegram_link=TELEGRAM_JOIN_LINK,
)


def post_telegram():
    """Post to Telegram"""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")

    if not bot_token or not channel_id:
        print("❌ Telegram credentials missing")
        return None

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": channel_id,
        "text": TELEGRAM_MESSAGE,
        "parse_mode": "Markdown",
    }

    try:
        resp = httpx.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        message_id = data["result"]["message_id"]
        print(f"✅ Telegram posted (message ID: {message_id})")
        return message_id
    except Exception as e:
        print(f"❌ Telegram failed: {e}")
        return None


def post_x():
    """Post X thread"""
    client = tweepy.Client(
        consumer_key=os.getenv("X_CONSUMER_KEY"),
        consumer_secret=os.getenv("X_CONSUMER_SECRET"),
        access_token=os.getenv("X_ACCESS_TOKEN"),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET"),
    )

    try:
        # Tweet 1
        r1 = client.create_tweet(text=X_TWEET_1)
        tweet_1_id = r1.data["id"]
        print(f"✅ X Tweet 1 posted (ID: {tweet_1_id})")

        # Tweet 2
        r2 = client.create_tweet(text=X_TWEET_2, in_reply_to_tweet_id=tweet_1_id)
        tweet_2_id = r2.data["id"]
        print(f"✅ X Tweet 2 posted (ID: {tweet_2_id})")

        # Tweet 3
        r3 = client.create_tweet(text=X_TWEET_3, in_reply_to_tweet_id=tweet_2_id)
        tweet_3_id = r3.data["id"]
        print(f"✅ X Tweet 3 posted (ID: {tweet_3_id})")

        return [tweet_1_id, tweet_2_id, tweet_3_id]
    except Exception as e:
        print(f"❌ X failed: {e}")
        return None


def main():
    print(f"Publishing SIG-034...")
    print()

    # Post to Telegram
    telegram_message_id = post_telegram()
    print()

    # Post to X
    x_tweet_ids = post_x()
    print()

    # Log to published_signals.json
    if telegram_message_id or x_tweet_ids:
        published_entry = {
            "signal_id": "SIG-034",
            "published_at": datetime.utcnow().isoformat() + "Z",
            "platforms": [],
            "telegram_message_id": telegram_message_id,
            "x_tweet_ids": x_tweet_ids,
        }

        if telegram_message_id:
            published_entry["platforms"].append("telegram")
        if x_tweet_ids:
            published_entry["platforms"].append("x")

        # Read existing
        try:
            with open("/home/slova/ProbBrain/data/published_signals.json") as f:
                published = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            published = []

        # Append
        published.append(published_entry)

        # Write back
        with open("/home/slova/ProbBrain/data/published_signals.json", "w") as f:
            json.dump(published, f, indent=2)

        print(f"✅ Logged to published_signals.json")
        print(f"\nPosted to: {', '.join(published_entry['platforms'])}")


if __name__ == "__main__":
    main()
