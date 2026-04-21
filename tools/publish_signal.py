#!/usr/bin/env python3
"""
One-command signal publisher.

Usage:
    python tools/publish_signal.py --signal-id SIG-073

Does everything: dedup gate, format, Telegram post, X thread, data file
updates, dashboard sync, and git commit+push. Loads .env automatically.

Exit codes:
    0 = published successfully
    1 = blocked (dedup/rate limit)
    2 = error
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"
ENV_FILE = ROOT / ".env"


def load_dotenv():
    """Load .env file into os.environ if not already set."""
    if not ENV_FILE.exists():
        return
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")
            if key and key not in os.environ:
                os.environ[key] = value


def load_signal(signal_id: str) -> dict | None:
    """Load signal from signals.json."""
    with open(DATA_DIR / "signals.json") as f:
        signals = json.load(f)
    for s in signals:
        if s.get("signal_id") == signal_id:
            return s
    return None


def run_dedup_gate(market_id: str, signal_id: str) -> bool:
    """Returns True if OK to publish, False if blocked."""
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "dedup_gate.py"),
         "--market-id", market_id, "--signal-id", signal_id],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    print(result.stdout.strip())
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        return False
    return True


def publish_telegram(message: str, image_path: str | None = None) -> int | None:
    """Post to Telegram. Returns message_id or None.
    If image_path is provided, sends a photo with caption instead of text."""
    import httpx
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID", "")
    if not bot_token or not channel_id:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHANNEL_ID not set", file=sys.stderr)
        return None

    # Send text message first
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    resp = httpx.post(url, json={
        "chat_id": channel_id,
        "text": message,
        "disable_web_page_preview": True
    })
    result = resp.json()
    if not result.get("ok"):
        print(f"ERROR: Telegram API failed: {result}", file=sys.stderr)
        return None
    msg_id = result["result"]["message_id"]
    print(f"Telegram: message_id={msg_id}")

    # Send market card photo as a reply if provided
    if image_path and Path(image_path).exists():
        photo_url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        with open(image_path, "rb") as img:
            photo_resp = httpx.post(photo_url, data={
                "chat_id": channel_id,
                "reply_to_message_id": str(msg_id),
            }, files={"photo": (Path(image_path).name, img, "image/jpeg")},
            timeout=60.0)
        photo_result = photo_resp.json()
        if photo_result.get("ok"):
            print(f"Telegram: photo sent as reply to msg {msg_id}")
        else:
            print(f"WARNING: Telegram photo failed (text was sent): {photo_result}", file=sys.stderr)

    return msg_id


def publish_x(signal: dict, image_path: str | None = None) -> list[str] | None:
    """Post X thread. Returns list of 3 tweet IDs or None."""
    sys.path.insert(0, str(ROOT))
    from pipeline.x_publisher import build_thread, post_thread, upload_media

    evidence = signal.get("evidence", [])[:3]  # X thread uses top 3
    thread = build_thread(
        question=signal["question"],
        market_yes_pct=round(signal.get("market_yes_price", signal.get("market_price", 0)) * 100, 1),
        our_estimate_pct=round(signal.get("our_estimate", signal.get("our_calibrated_estimate", 0)) * 100, 1),
        gap_pct=signal["gap_pct"],
        direction=signal["direction"],
        confidence=signal["confidence"],
        evidence=evidence,
        close_date=signal["close_date"],
        volume_usdc=signal.get("volume_usdc", 0)
    )

    # Upload media if image provided
    tweet1_media_ids = None
    if image_path and Path(image_path).exists():
        media_id = upload_media(image_path)
        if media_id:
            tweet1_media_ids = [media_id]
            print(f"X: uploaded media_id={media_id}")

    tweet_ids = post_thread(thread, tweet1_media_ids=tweet1_media_ids)
    if tweet_ids is None or len(tweet_ids) != 3:
        print(f"ERROR: X posting failed: {tweet_ids}", file=sys.stderr)
        return None
    print(f"X: tweet_ids={tweet_ids}")
    return tweet_ids


def _mark_telegram_published(signal_id: str, signal: dict, telegram_msg_id: int):
    """Mark signal as published immediately after Telegram succeeds.
    This prevents duplicate posts if X fails later."""
    # Add minimal entry to published_signals.json for dedup
    with open(DATA_DIR / "published_signals.json") as f:
        published = json.load(f)
    
    # Check if already marked (shouldn't happen, but be safe)
    if any(p.get("signal_id") == signal_id for p in published):
        return
    
    entry = {
        "signal_id": signal_id,
        "market_id": signal["market_id"],
        "telegram_message_id": telegram_msg_id,
        "published_at": datetime.now(timezone.utc).isoformat(),
        "_partial": True,  # Flag that X may not have completed
    }
    published.append(entry)
    with open(DATA_DIR / "published_signals.json", "w") as f:
        json.dump(published, f, indent=2)
    print(f"Marked {signal_id} as published (dedup protection)")


def update_data_files(signal_id: str, signal: dict, telegram_msg_id: int, tweet_ids: list[str] | None):
    """Update published_signals.json, signals.json, pending_signals.json."""
    # Update the existing entry in published_signals.json (added by _mark_telegram_published)
    with open(DATA_DIR / "published_signals.json") as f:
        published = json.load(f)

    # Find and update the partial entry, or append new
    entry = {
        "signal_id": signal_id,
        "market_id": signal["market_id"],
        "question": signal["question"],
        "category": signal.get("category", "general"),
        "direction": signal["direction"],
        "confidence": signal["confidence"],
        "market_yes_pct": round(signal.get("market_yes_price", signal.get("market_price", 0)) * 100, 1),
        "our_estimate_pct": round(signal.get("our_estimate", signal.get("our_calibrated_estimate", 0)) * 100, 1),
        "gap_pct": signal["gap_pct"],
        "close_date": signal["close_date"],
        "volume_usdc": signal.get("volume_usdc", 0),
        "telegram_message_id": telegram_msg_id,
        "x_tweet_ids": {
            "tweet_1": tweet_ids[0] if tweet_ids else None,
            "tweet_2": tweet_ids[1] if tweet_ids and len(tweet_ids) > 1 else None,
            "tweet_3": tweet_ids[2] if tweet_ids and len(tweet_ids) > 2 else None,
        } if tweet_ids else None,
        "published_at": datetime.now(timezone.utc).isoformat(),
    }
    
    # Replace partial entry or append
    found = False
    for i, p in enumerate(published):
        if p.get("signal_id") == signal_id:
            published[i] = entry
            found = True
            break
    if not found:
        published.append(entry)
    
    with open(DATA_DIR / "published_signals.json", "w") as f:
        json.dump(published, f, indent=2)

    # Mark as published in signals.json (surgical edit)
    with open(DATA_DIR / "signals.json") as f:
        signals = json.load(f)
    for s in signals:
        if s.get("signal_id") == signal_id:
            s["status"] = "published"
            break
    with open(DATA_DIR / "signals.json", "w") as f:
        json.dump(signals, f, indent=2)

    # Remove from pending (surgical)
    pending_path = DATA_DIR / "pending_signals.json"
    if pending_path.exists():
        with open(pending_path) as f:
            pending = json.load(f)
        pending = [p for p in pending if p.get("signal_id") != signal_id]
        with open(pending_path, "w") as f:
            json.dump(pending, f, indent=2)

    print(f"Data files updated. Total published: {len(published)}")


def sync_and_push(signal_id: str):
    """Sync dashboard and git commit+push."""
    subprocess.run(
        [sys.executable, str(ROOT / "tools" / "sync_dashboard.py"),
         "--signal-id", signal_id],
        cwd=str(ROOT)
    )


def main():
    parser = argparse.ArgumentParser(description="Publish a signal end-to-end")
    parser.add_argument("--signal-id", required=True, help="Signal ID (e.g. SIG-073)")
    parser.add_argument("--image-path", default=None, help="Path to market card image for tweet 1 and Telegram")
    args = parser.parse_args()

    load_dotenv()

    signal = load_signal(args.signal_id)
    if not signal:
        print(f"ERROR: {args.signal_id} not found in signals.json", file=sys.stderr)
        sys.exit(2)

    market_id = signal.get("market_id", "")
    if not market_id:
        print(f"ERROR: {args.signal_id} has no market_id", file=sys.stderr)
        sys.exit(2)

    # Step 1: Dedup gate
    if not run_dedup_gate(market_id, args.signal_id):
        print("BLOCKED by dedup gate")
        sys.exit(1)

    # Step 2: Format Telegram message
    sys.path.insert(0, str(ROOT))
    from bot.templates import format_ns_signal

    evidence = signal.get("evidence", [])
    counter = signal.get("counter_evidence", [])
    if isinstance(counter, list):
        counter = "; ".join(counter)

    message = format_ns_signal(
        question=signal["question"],
        market_yes_pct=round(signal.get("market_yes_price", signal.get("market_price", 0)) * 100, 1),
        our_estimate_pct=round(signal.get("our_estimate", signal.get("our_calibrated_estimate", 0)) * 100, 1),
        gap_pct=signal["gap_pct"],
        direction=signal["direction"],
        confidence=signal["confidence"],
        evidence=evidence,
        counter_evidence=counter,
        close_date=signal["close_date"],
        volume_usdc=signal.get("volume_usdc", 0)
    )

    # Step 3: Publish to Telegram
    telegram_msg_id = publish_telegram(message, image_path=args.image_path)
    if telegram_msg_id is None:
        print("FAILED: Telegram publish failed", file=sys.stderr)
        sys.exit(2)

    # Step 3.5: Mark as published IMMEDIATELY after Telegram succeeds
    # This prevents duplicate posts if X fails later
    _mark_telegram_published(args.signal_id, signal, telegram_msg_id)

    # Step 4: Publish to X (best effort - Telegram already marked)
    tweet_ids = None
    try:
        tweet_ids = publish_x(signal, image_path=args.image_path)
        if tweet_ids is None:
            print("WARNING: X publish failed (Telegram was posted, continuing...)", file=sys.stderr)
    except Exception as e:
        print(f"WARNING: X publish error: {e} (Telegram was posted, continuing...)", file=sys.stderr)

    # Step 5: Update data files with full info (including X if it worked)
    update_data_files(args.signal_id, signal, telegram_msg_id, tweet_ids)

    # Step 6: Sync dashboard and push
    sync_and_push(args.signal_id)

    print(f"\nSUCCESS: {args.signal_id} published to Telegram (msg {telegram_msg_id}) and X ({tweet_ids[0]})")


if __name__ == "__main__":
    main()
