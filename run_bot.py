#!/usr/bin/env python3
"""
Entry point: start the Telegram bot.
Uses webhook if TELEGRAM_WEBHOOK_URL is set, otherwise falls back to polling.
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

from bot.server import start_bot

start_bot()
