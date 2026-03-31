#!/usr/bin/env python3
"""
Common utilities for all signal posting scripts.
Prevents double-posting and ensures data integrity.
"""

import json
from typing import Optional, Dict, List


def check_signal_already_published(signal_id: str, published_signals_path: str = "/home/slova/ProbBrain/data/published_signals.json") -> Dict:
    """
    Check if a signal has already been published.

    Args:
        signal_id: e.g. "SIG-052"
        published_signals_path: path to published_signals.json

    Returns:
        {
            "already_published": bool,
            "telegram_message_id": Optional[int],
            "x_tweet_ids": Optional[list],
            "platforms_published": list
        }
    """
    try:
        with open(published_signals_path) as f:
            signals = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"already_published": False, "telegram_message_id": None, "x_tweet_ids": None, "platforms_published": []}

    # Find matching signal
    for sig in signals:
        if sig.get("signal_id") == signal_id or sig.get("id") == signal_id:
            platforms = sig.get("platforms", [])
            return {
                "already_published": True,
                "telegram_message_id": sig.get("telegram_message_id"),
                "x_tweet_ids": sig.get("x_tweet_ids"),
                "platforms_published": platforms
            }

    return {"already_published": False, "telegram_message_id": None, "x_tweet_ids": None, "platforms_published": []}


def should_post_to_platform(signal_id: str, platform: str, published_signals_path: str = "/home/slova/ProbBrain/data/published_signals.json") -> bool:
    """
    Determine if a signal should be posted to a specific platform.

    Args:
        signal_id: e.g. "SIG-052"
        platform: "telegram" or "x"
        published_signals_path: path to published_signals.json

    Returns:
        True if should post (not already published to this platform)
        False if should skip (already published to this platform)
    """
    status = check_signal_already_published(signal_id, published_signals_path)

    if not status["already_published"]:
        return True  # Never published before, post to this platform

    if platform not in status["platforms_published"]:
        return True  # Published before but not to this platform, post now

    return False  # Already published to this platform, SKIP


def log_posting_decision(signal_id: str, platforms: List[str], published_signals_path: str = "/home/slova/ProbBrain/data/published_signals.json"):
    """
    Log which platforms a signal will be posted to (or skipped).
    Used to prevent double-posting errors.
    """
    status = check_signal_already_published(signal_id, published_signals_path)

    print(f"\n[Idempotency Check] {signal_id}:")

    if not status["already_published"]:
        print(f"  ✓ New signal — will post to all requested platforms: {platforms}")
        return

    print(f"  ⚠ Signal already published")
    print(f"    - Platforms: {status['platforms_published']}")
    print(f"    - Telegram message ID: {status['telegram_message_id']}")
    print(f"    - X tweet IDs: {status['x_tweet_ids']}")

    # Show what will be skipped
    for platform in platforms:
        if should_post_to_platform(signal_id, platform, published_signals_path):
            print(f"  ✓ Will post to {platform} (not previously posted)")
        else:
            print(f"  ⊘ SKIP {platform} (already posted — prevent double-post)")


if __name__ == "__main__":
    # Test
    print("Testing posting_utils.py...")
    status = check_signal_already_published("SIG-052")
    print(f"SIG-052 status: {status}")
    print(f"Should post to Telegram: {should_post_to_platform('SIG-052', 'telegram')}")
    print(f"Should post to X: {should_post_to_platform('SIG-052', 'x')}")
