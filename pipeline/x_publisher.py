"""
X (Twitter) Publisher: post signal threads via Twitter API v1.1 OAuth 1.0a.

Requires all four credentials in .env:
  X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET

Thread format (3 tweets):
  Tweet 1 — core insight + probability gap (<200 chars, no hashtags)
  Tweet 2 — evidence bullets + affiliate link + disclaimer
  Tweet 3 — accuracy dashboard link
"""
import logging
import os
from dataclasses import dataclass
from typing import Optional

import tweepy

logger = logging.getLogger(__name__)

DUB_LINK_X = os.getenv("DUB_LINK_TWITTER", "https://dub.sh/pb-x")
DASHBOARD_URL = "https://vpjonny.github.io/probbrain-accuracy/"
TELEGRAM_INVITE_URL = os.getenv("DUB_LINK_TELEGRAM_CHANNEL", "https://dub.sh/pb-tg")


def _client() -> tweepy.Client:
    consumer_key = os.getenv("X_CONSUMER_KEY", "").strip()
    consumer_secret = os.getenv("X_CONSUMER_SECRET", "").strip()
    access_token = os.getenv("X_ACCESS_TOKEN", "").strip()
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET", "").strip()

    missing = [
        name for name, val in [
            ("X_CONSUMER_KEY", consumer_key),
            ("X_CONSUMER_SECRET", consumer_secret),
            ("X_ACCESS_TOKEN", access_token),
            ("X_ACCESS_TOKEN_SECRET", access_token_secret),
        ] if not val
    ]
    if missing:
        raise RuntimeError(f"Missing X credentials: {', '.join(missing)}")

    return tweepy.Client(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )


@dataclass
class XThreadContent:
    tweet1: str   # main tweet, <200 chars
    tweet2: str   # evidence + link
    tweet3: str   # dashboard + disclaimer


def build_thread(
    question: str,
    market_yes_pct: float,
    our_estimate_pct: float,
    gap_pct: float,
    direction: str,
    confidence: str,
    evidence: list[str],
    close_date: str,
    volume_usdc: float,
    dub_link: str = "",
) -> XThreadContent:
    """Format signal data into a 3-tweet thread."""
    link = dub_link or DUB_LINK_X
    badge = "HIGH" if confidence.upper() == "HIGH" else "MEDIUM"
    direction_label = "overpriced" if direction == "NO_UNDERPRICED" else "underpriced"

    gap_sign = "+" if gap_pct >= 0 else ""
    tweet1 = (
        f"[{badge}] {question[:90]} "
        f"Market: {market_yes_pct:.0f}% YES. "
        f"Our estimate: {our_estimate_pct:.0f}%. "
        f"Gap: {gap_sign}{gap_pct:.1f}pp — market appears {direction_label}."
    )
    # Trim to 280 chars hard limit (tweet1 target is <200 but apply safety trim)
    tweet1 = tweet1[:280]

    vol_str = f"${volume_usdc / 1_000:.0f}k" if volume_usdc < 1_000_000 else f"${volume_usdc / 1_000_000:.1f}M"
    footer = f"\n\nVol: {vol_str} | Closes: {close_date}\n{link}\nNot financial advice."
    # Fit evidence bullets within Twitter's 280-char limit
    header = "Evidence:\n"
    body = ""
    for e in evidence[:4]:
        line = f"• {e}\n"
        if len(header) + len(body) + len(line) + len(footer) > 280:
            break
        body += line
    tweet2 = header + body + footer

    tweet3 = (
        f"We track every call publicly.\n"
        f"Accuracy record: {DASHBOARD_URL}\n\n"
        f"Join us on Telegram: {TELEGRAM_INVITE_URL}"
    )

    return XThreadContent(tweet1=tweet1, tweet2=tweet2, tweet3=tweet3)


def post_thread(thread: XThreadContent, dry_run: bool = False) -> Optional[list[str]]:
    """
    Post a 3-tweet thread. Returns list of tweet IDs, or None on failure.
    Set dry_run=True to log without posting (useful for approval checks).
    """
    if dry_run:
        logger.info("DRY RUN — X thread would be:\n\nTweet 1:\n%s\n\nTweet 2:\n%s\n\nTweet 3:\n%s",
                    thread.tweet1, thread.tweet2, thread.tweet3)
        return None

    client = _client()
    ids = []

    try:
        r1 = client.create_tweet(text=thread.tweet1)
        t1_id = r1.data["id"]
        ids.append(t1_id)
        logger.info("Posted tweet 1 (id=%s)", t1_id)

        r2 = client.create_tweet(text=thread.tweet2, in_reply_to_tweet_id=t1_id)
        t2_id = r2.data["id"]
        ids.append(t2_id)
        logger.info("Posted tweet 2 (id=%s)", t2_id)

        r3 = client.create_tweet(text=thread.tweet3, in_reply_to_tweet_id=t2_id)
        t3_id = r3.data["id"]
        ids.append(t3_id)
        logger.info("Posted tweet 3 (id=%s)", t3_id)

    except tweepy.TweepyException as exc:
        logger.error("X posting failed: %s", exc)
        return None

    return ids
