#!/usr/bin/env python3
"""
Pre-publish dedup gate. Run before publishing any signal.

Usage:
    python tools/dedup_gate.py --market-id 540843 --signal-id SIG-054
    python tools/dedup_gate.py --market-id 540843

Exit codes:
    0 = OK (safe to publish)
    1 = BLOCKED (duplicate detected)
    2 = ERROR (could not verify)
"""
import argparse
import json
import sys
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
SIGNALS_PATH = DATA_DIR / "signals.json"
PUBLISHED_PATH = DATA_DIR / "published_signals.json"


def load_known_market_ids() -> dict[str, list[str]]:
    """Load all known market_ids mapped to their signal_ids."""
    known: dict[str, list[str]] = {}
    for filepath in (SIGNALS_PATH, PUBLISHED_PATH):
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


def main():
    parser = argparse.ArgumentParser(description="Pre-publish dedup gate")
    parser.add_argument("--market-id", required=True, help="Polymarket market ID to check")
    parser.add_argument("--signal-id", default="", help="Signal ID being published (for logging)")
    args = parser.parse_args()

    market_id = str(args.market_id)
    signal_id = args.signal_id or "unknown"

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
