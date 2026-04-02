#!/usr/bin/env python3
"""
Monitor resolved.json for changes and auto-sync dashboard when detected.

This script watches the resolved.json file and triggers sync_dashboard.py
whenever it changes. It can be run as a background daemon or called periodically.

Usage:
    python tools/monitor_resolved.py              # One-time check
    python tools/monitor_resolved.py --watch      # Continuous monitoring
"""
import json
import subprocess
import sys
import time
import hashlib
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

ROOT = Path(__file__).resolve().parent.parent
RESOLVED_PATH = ROOT / "data" / "resolved.json"
STATE_PATH = ROOT / ".claude" / "resolved_sync_state.json"


def get_file_hash(path: Path) -> str:
    """Compute hash of file content to detect changes."""
    if not path.exists():
        return ""
    return hashlib.md5(path.read_bytes()).hexdigest()


def load_state() -> dict:
    """Load last known sync state."""
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"last_hash": "", "last_sync_at": None}


def save_state(state: dict):
    """Save current sync state."""
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))


def sync_dashboard():
    """Run sync_dashboard.py if resolved.json has changed."""
    current_hash = get_file_hash(RESOLVED_PATH)
    state = load_state()

    if current_hash == state.get("last_hash"):
        logger.debug("resolved.json unchanged")
        return False

    logger.info("resolved.json changed, syncing dashboard...")
    try:
        result = subprocess.run(
            ["python", str(ROOT / "tools" / "sync_dashboard.py")],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            logger.info("✓ Dashboard synced successfully")
            state["last_hash"] = current_hash
            state["last_sync_at"] = datetime.now().isoformat()
            save_state(state)
            return True
        else:
            logger.error(f"✗ Dashboard sync failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("✗ Dashboard sync timeout")
        return False
    except Exception as e:
        logger.error(f"✗ Error during sync: {e}")
        return False


def watch_continuous():
    """Continuously monitor for changes every 10 seconds."""
    logger.info("Starting continuous monitoring of resolved.json")
    logger.info("Press Ctrl+C to stop")

    try:
        while True:
            sync_dashboard()
            time.sleep(10)
    except KeyboardInterrupt:
        logger.info("Monitor stopped")


def main():
    if "--watch" in sys.argv:
        watch_continuous()
    else:
        # One-time check
        if sync_dashboard():
            sys.exit(0)
        else:
            sys.exit(1)


if __name__ == "__main__":
    main()
