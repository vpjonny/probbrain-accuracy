#!/usr/bin/env python3
"""
Pipeline health monitor: detects silent failures by checking whether
the pipeline has run recently during active hours.
Usage: python tools/monitor_pipeline_health.py
"""
import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
PUBLISHED_PATH = ROOT / "data" / "published_signals.json"
SCANS_DIR = ROOT / "data" / "scans"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
TELEGRAM_API = "https://api.telegram.org"

ACTIVE_HOURS_UTC = range(7, 24)  # 7am-11pm UTC
MAX_SCAN_GAP_HOURS = 4
MAX_PUBLISH_GAP_HOURS = 8

SYSTEMD_UNITS = [
    "probbrain-scanner.service",
    "probbrain-pipeline.timer",
    "probbrain-bot.service",
    "probbrain-drip.timer",
    "probbrain-resolve.timer",
]


def is_active_hours() -> bool:
    return datetime.now(timezone.utc).hour in ACTIVE_HOURS_UTC


def check_last_scan() -> dict:
    if not SCANS_DIR.exists():
        return {"status": "error", "detail": "scans directory missing"}
    import re
    scans = sorted(
        [f for f in SCANS_DIR.glob("*.json") if re.match(r"\d{4}-\d{2}-\d{2}", f.stem)],
    )
    if not scans:
        return {"status": "error", "detail": "no timestamped scan files found"}
    latest = scans[-1]
    ts = datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc)
    age_hours = (datetime.now(timezone.utc) - ts).total_seconds() / 3600
    status = "ok" if age_hours < MAX_SCAN_GAP_HOURS else "stale"
    return {"status": status, "latest_scan": latest.name, "age_hours": round(age_hours, 1)}


def check_last_publish() -> dict:
    if not PUBLISHED_PATH.exists():
        return {"status": "error", "detail": "published_signals.json missing"}
    try:
        signals = json.loads(PUBLISHED_PATH.read_text())
        if not signals:
            return {"status": "ok", "detail": "no published signals yet"}
        latest_ts = None
        for s in signals:
            ts_str = s.get("published_at") or s.get("actually_posted_at", "")
            if not ts_str:
                continue
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if latest_ts is None or ts > latest_ts:
                    latest_ts = ts
            except (ValueError, TypeError):
                continue
        if latest_ts is None:
            return {"status": "ok", "detail": "no timestamps found"}
        age_hours = (datetime.now(timezone.utc) - latest_ts).total_seconds() / 3600
        status = "ok" if age_hours < MAX_PUBLISH_GAP_HOURS else "stale"
        return {"status": status, "age_hours": round(age_hours, 1)}
    except (json.JSONDecodeError, KeyError):
        return {"status": "error", "detail": "could not parse published_signals.json"}


def check_systemd_units() -> list:
    problems = []
    for unit in SYSTEMD_UNITS:
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", unit],
                capture_output=True, text=True, timeout=5,
            )
            state = result.stdout.strip()
            if unit.endswith(".timer"):
                if state not in ("active", "waiting"):
                    problems.append({"unit": unit, "state": state})
            elif unit.endswith(".service"):
                if state != "active":
                    problems.append({"unit": unit, "state": state})
        except (subprocess.SubprocessError, FileNotFoundError):
            problems.append({"unit": unit, "state": "check_failed"})
    return problems


def send_alert(issues: list) -> None:
    if not issues:
        return
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.warning("No Telegram credentials; printing to stdout")
        for i in issues:
            print(f"  ALERT: {i}")
        return

    lines = [f"🚨 *Pipeline health: {len(issues)} issue\\(s\\)*\n"]
    for i in issues:
        lines.append(f"• {i}")
    text = "\n".join(lines)

    url = f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": True,
    }
    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("Sent pipeline health alert")
    except httpx.HTTPError as exc:
        logger.error("Failed to send Telegram alert: %s", exc)


def main():
    issues = []

    if is_active_hours():
        scan = check_last_scan()
        if scan["status"] == "stale":
            issues.append(f"Scanner stale: last scan {scan.get('age_hours', '?')}h ago \\({scan.get('latest_scan', '?')}\\)")
        elif scan["status"] == "error":
            issues.append(f"Scanner error: {scan.get('detail', 'unknown')}")
        logger.info("Scan check: %s", scan)

        publish = check_last_publish()
        if publish["status"] == "stale":
            issues.append(f"Publisher stale: last publish {publish.get('age_hours', '?')}h ago")
        elif publish["status"] == "error":
            issues.append(f"Publisher error: {publish.get('detail', 'unknown')}")
        logger.info("Publish check: %s", publish)
    else:
        logger.info("Outside active hours (7-23 UTC); skipping freshness checks")

    unit_problems = check_systemd_units()
    for p in unit_problems:
        issues.append(f"Systemd unit *{p['unit']}* is {p['state']}")
    if not unit_problems:
        logger.info("All systemd units healthy")

    if issues:
        logger.warning("Found %d pipeline health issues", len(issues))
        send_alert(issues)
    else:
        logger.info("Pipeline healthy — all checks passed")


if __name__ == "__main__":
    main()
