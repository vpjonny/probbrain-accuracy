#!/usr/bin/env python3
"""
Pre-publish dedup gate. Run before publishing any signal.

Usage:
    python tools/dedup_gate.py --market-id 540843 --signal-id SIG-054
    python tools/dedup_gate.py --market-id 540843

Exit codes:
    0 = OK (safe to publish)
    1 = BLOCKED (duplicate detected OR rate-limited)
    2 = ERROR (could not verify)
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SIGNALS_PATH = DATA_DIR / "signals.json"
PUBLISHED_PATH = DATA_DIR / "published_signals.json"

# HARDCODED: minimum seconds between any two published signals (30 minutes)
MIN_GAP_BETWEEN_POSTS_SEC = 1800


def load_known_market_ids() -> dict[str, list[str]]:
    """Load all known market_ids mapped to their signal_ids."""
    known: dict[str, list[str]] = {}
    for filepath in (PUBLISHED_PATH,):
        if not filepath.exists():
            continue
        try:
            with open(filepath) as f:
                data = json.load(f)
            for entry in data:
                mid = str(entry.get("market_id", ""))
                sid = entry.get("signal_id", "?")
                if mid:
                    known.setdefault(mid, []).append(sid)
        except (json.JSONDecodeError, IOError):
            continue
    return known


def check_rate_limit() -> tuple[bool, str]:
    """Check that at least MIN_GAP_BETWEEN_POSTS_SEC have passed since the last publish.

    Returns (ok, message). If ok is False, publishing should be blocked.
    """
    if not PUBLISHED_PATH.exists():
        return True, "No previous signals found."
    try:
        with open(PUBLISHED_PATH) as f:
            data = json.load(f)
        if not data:
            return True, "No previous signals found."

        # Find the most recent published_at timestamp
        latest_ts = None
        for entry in data:
            ts_str = entry.get("published_at", "")
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if latest_ts is None or ts > latest_ts:
                    latest_ts = ts
            except (ValueError, TypeError):
                continue

        if latest_ts is None:
            return True, "No parseable timestamps found."

        now = datetime.now(timezone.utc)
        elapsed = (now - latest_ts).total_seconds()

        if elapsed < MIN_GAP_BETWEEN_POSTS_SEC:
            remaining = int(MIN_GAP_BETWEEN_POSTS_SEC - elapsed)
            return False, (
                f"RATE LIMITED: Last signal was published {int(elapsed)}s ago. "
                f"Minimum gap is {MIN_GAP_BETWEEN_POSTS_SEC}s (30 min). "
                f"Wait {remaining}s before publishing."
            )
        return True, f"Rate limit OK: {int(elapsed)}s since last publish."
    except (json.JSONDecodeError, IOError) as exc:
        return True, f"Could not check rate limit ({exc}); allowing publish."


def main():
    parser = argparse.ArgumentParser(description="Pre-publish dedup gate")
    parser.add_argument("--market-id", required=True, help="Polymarket market ID to check")
    parser.add_argument("--signal-id", default="", help="Signal ID being published (for logging)")
    args = parser.parse_args()

    market_id = str(args.market_id)
    signal_id = args.signal_id or "unknown"

    # --- Rate limit check (HARDCODED 30-min gap) ---
    rate_ok, rate_msg = check_rate_limit()
    if not rate_ok:
        print(f"BLOCKED: {rate_msg}")
        print(f"Signal {signal_id} cannot be published yet. Try again later.")
        sys.exit(1)
    print(rate_msg)

    # --- Dedup check ---
    known = load_known_market_ids()

    if market_id in known:
        existing = known[market_id]
        print(f"BLOCKED: market_id {market_id} already exists as {', '.join(existing)}")
        print(f"Signal {signal_id} would be a duplicate. Do not publish.")
        sys.exit(1)
    else:
        print(f"OK: market_id {market_id} is new. Safe to publish as {signal_id}.")
        sys.exit(0)


if __name__ == "__main__":
    main()
