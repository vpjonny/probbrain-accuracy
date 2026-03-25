#!/usr/bin/env python3
"""
Entry point: start the blocking APScheduler for the market scanner.

Schedule: every 2 hours at :03, hours 7,9,11,13,15,17,19,21,23 UTC
Run via systemd: systemctl --user start probbrain-scanner.service
Run manually:   python run_scheduler.py
"""
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    stream=sys.stdout,
)

sys.path.insert(0, str(Path(__file__).parent))

from scanner.scheduler import start_scheduler

start_scheduler(output_dir="data/scans")
