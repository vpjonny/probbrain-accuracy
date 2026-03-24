"""
Post Edge Thread #2 to X as a 7-tweet thread.
Reads credentials from .env, posts via tweepy OAuth 1.0a.
"""
import os
import sys
import time
import logging
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

import tweepy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DASHBOARD_URL = "https://vpjonny.github.io/probbrain-accuracy/"

TWEETS = [
    # 1 — hook
    (
        'Before you look at a single piece of evidence about a specific event, '
        'there\'s one question you should always ask first:\n\n'
        '"What is the base rate for this category of event?"\n\n'
        'Most forecasters skip it. It\'s also the highest-leverage step in the process.\n\n'
        '[1/7]'
    ),
    # 2 — what is reference class forecasting
    (
        'The technique: reference class forecasting (Kahneman, Tversky, Flyvbjerg).\n\n'
        'The idea:\n'
        '1. Identify a class of comparable events\n'
        '2. Find the historical frequency (base rate)\n'
        '3. Use that as your starting probability\n'
        '4. Then — and only then — adjust for case-specific details\n\n'
        '[2/7]'
    ),
    # 3 — inside vs. outside view
    (
        'Kahneman called this the "outside view" vs. the "inside view."\n\n'
        'Inside view: Analyze the specific situation. Build a narrative.\n\n'
        'Outside view: What usually happens to situations like this one?\n\n'
        'The inside view feels more rigorous. It\'s usually less accurate.\n\n'
        '[3/7]'
    ),
    # 4 — choosing the reference class
    (
        'The hardest part isn\'t the math. It\'s choosing the right reference class.\n\n'
        'Too narrow: "Elections in this country under these conditions" → not enough data.\n'
        'Too wide: "All political events ever" → meaningless signal.\n\n'
        'Broad enough for signal. Narrow enough to matter.\n\n'
        '[4/7]'
    ),
    # 5 — worked example
    (
        'Concrete example: Market prices "ceasefire signed within 6 months" at 60%.\n\n'
        'Reference class: Formal ceasefire negotiations in active territorial conflicts since 1990.\n'
        'Historical frequency: ~35%.\n\n'
        "That's a 25-point gap before looking at a single case-specific detail.\n\n"
        '[5/7]'
    ),
    # 6 — how ProbBrain applies it
    (
        'Our process at ProbBrain:\n\n'
        '1. Category → historical base rate → starting prior\n'
        '2. Update with current evidence (polling, precedent, momentum)\n'
        '3. Compare final estimate to market price\n\n'
        'Steps 1–3 take 10 minutes. They prevent the most common forecasting error.\n\n'
        '[6/7]'
    ),
    # 7 — track record + dashboard
    (
        'We apply this framework to every call — and publish the results.\n\n'
        'Right or wrong, open or resolved. Brier scores and category breakdowns included.\n\n'
        'The outside view is only useful if you can audit whether it works.\n\n'
        f'\u2192 {DASHBOARD_URL}\n\n'
        '[7/7]'
    ),
]


def get_client() -> tweepy.Client:
    keys = {
        "consumer_key": os.getenv("X_CONSUMER_KEY", "").strip(),
        "consumer_secret": os.getenv("X_CONSUMER_SECRET", "").strip(),
        "access_token": os.getenv("X_ACCESS_TOKEN", "").strip(),
        "access_token_secret": os.getenv("X_ACCESS_TOKEN_SECRET", "").strip(),
    }
    missing = [k for k, v in keys.items() if not v]
    if missing:
        raise RuntimeError(f"Missing X credentials: {missing}")
    return tweepy.Client(**keys)


def post_thread(dry_run: bool = False) -> list[str]:
    for i, tweet in enumerate(TWEETS, 1):
        char_count = len(tweet)
        if char_count > 280:
            logger.warning("Tweet %d is %d chars (>280) — will be rejected by API", i, char_count)
        else:
            logger.info("Tweet %d: %d chars", i, char_count)

    if dry_run:
        logger.info("DRY RUN — thread content:")
        for i, tweet in enumerate(TWEETS, 1):
            print(f"\n--- Tweet {i} ({len(tweet)} chars) ---\n{tweet}")
        return []

    client = get_client()
    ids = []
    reply_to = None

    for i, text in enumerate(TWEETS, 1):
        kwargs = {"text": text}
        if reply_to:
            kwargs["in_reply_to_tweet_id"] = reply_to

        try:
            resp = client.create_tweet(**kwargs)
            tweet_id = resp.data["id"]
            ids.append(tweet_id)
            reply_to = tweet_id
            logger.info("Posted tweet %d/%d (id=%s)", i, len(TWEETS), tweet_id)
        except tweepy.TweepyException as exc:
            logger.error("Failed on tweet %d: %s", i, exc)
            raise

        if i < len(TWEETS):
            time.sleep(1)  # brief pause between tweets

    return ids


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        logger.info("Running in dry-run mode")
    ids = post_thread(dry_run=dry)
    if ids:
        logger.info("Thread posted successfully. Tweet IDs: %s", ids)
        print(f"THREAD_IDS={','.join(ids)}")
