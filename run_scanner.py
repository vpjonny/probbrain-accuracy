#!/usr/bin/env python3
"""
Entry point: run market scanner once and save snapshot.
Usage: python run_scanner.py [--no-filter]
"""
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).parent))

from scanner.polymarket import fetch_markets, save_snapshot

filtered = "--no-filter" not in sys.argv
markets = fetch_markets(filtered=filtered)
path = save_snapshot(markets)

print(f"Saved {len(markets)} markets to {path}")
print(json.dumps(markets[0].to_dict(), indent=2) if markets else "No markets found")
