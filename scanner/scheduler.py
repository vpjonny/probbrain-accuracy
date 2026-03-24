"""
Scheduler: run the market scanner every 2 hours, 7am–11pm UTC.
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from .polymarket import fetch_markets, save_snapshot

logger = logging.getLogger(__name__)


def run_scan(output_dir: str = "data/scans") -> str:
    """Fetch, filter, and snapshot markets. Returns the snapshot path."""
    logger.info("Scanner run started")
    markets = fetch_markets(filtered=True)
    path = save_snapshot(markets, output_dir=output_dir)
    logger.info("Scanner run complete: %d markets → %s", len(markets), path)
    return str(path)


def start_scheduler(output_dir: str = "data/scans") -> None:
    """
    Start the blocking APScheduler.
    Fires every 2 hours, only between 07:00 and 23:00 UTC.
    """
    scheduler = BlockingScheduler(timezone="UTC")

    # Every 2h at :00, hours 7, 9, 11, 13, 15, 17, 19, 21, 23
    trigger = CronTrigger(hour="7,9,11,13,15,17,19,21,23", minute=0, timezone="UTC")
    scheduler.add_job(run_scan, trigger=trigger, kwargs={"output_dir": output_dir}, id="scanner")

    logger.info("Scanner scheduler starting (every 2h, 07–23 UTC)")
    scheduler.start()


def should_run_now() -> bool:
    """Return True if current UTC hour is in the 7am–11pm window."""
    hour = datetime.now(timezone.utc).hour
    return 7 <= hour <= 23
