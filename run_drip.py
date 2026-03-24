#!/usr/bin/env python3
"""
Entry point: run the onboarding drip processor once.

Checks subscribers.json for anyone due for their next drip message
and sends it via Telegram. Safe to call daily via cron.

Run manually:   python run_drip.py
Via cron:       0 9 * * * /path/to/venv/bin/python /home/slova/ProbBrain/run_drip.py
"""
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)

sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv()

from bot.drip import run_drip

result = run_drip()
logging.getLogger(__name__).info(
    "Drip run complete — sent=%d skipped=%d errors=%d",
    result["sent"],
    result["skipped"],
    result["errors"],
)
sys.exit(1 if result["errors"] > 0 else 0)
