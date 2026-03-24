#!/usr/bin/env python3
"""
Entry point: run the full scan → signal → publish pipeline once.
Usage: python run_pipeline.py [--dry-run] [--max-signals N]
"""
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

import argparse
from pipeline.run_pipeline import run

parser = argparse.ArgumentParser()
parser.add_argument("--dry-run", action="store_true", help="Skip publishing")
parser.add_argument("--max-signals", type=int, default=5)
args = parser.parse_args()

result = run(dry_run=args.dry_run, max_signals=args.max_signals)
print(result)
