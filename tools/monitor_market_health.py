#!/usr/bin/env python3
"""
Market health checker: scans published signals against Polymarket API,
flags closed/delisted/resolved markets that we still link to.
Usage: python tools/monitor_market_health.py
"""
import json
import logging
import os
import time
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
RESOLVED_PATH = ROOT / "data" / "resolved.json"
REPORT_PATH = ROOT / "data" / "market_health_report.json"

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
BUILDERS_API_KEY = os.getenv("POLYMARKET_BUILDERS_API_KEY", "")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "")
TELEGRAM_API = "https://api.telegram.org"


def load_json(path: Path) -> list:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, KeyError):
        return []


def get_resolved_ids(resolved: list) -> set:
    return {s.get("signal_id") for s in resolved if s.get("signal_id")}


def check_market(market_id: str, client: httpx.Client) -> dict | None:
    headers = {}
    if BUILDERS_API_KEY:
        headers["X-Polymarket-Builder-Api-Key"] = BUILDERS_API_KEY
    try:
        resp = client.get(f"{GAMMA_API_BASE}/markets/{market_id}", headers=headers)
        if resp.status_code == 404:
            return {"status": "delisted"}
        resp.raise_for_status()
        data = resp.json()
        return {
            "status": "active" if data.get("active") else "inactive",
            "closed": data.get("closed", False),
            "resolved": data.get("resolved", False),
            "end_date": data.get("endDate"),
        }
    except httpx.HTTPError as exc:
        logger.warning("API error for market %s: %s", market_id, exc)
        return None


def run_health_check() -> dict:
    published = load_json(PUBLISHED_PATH)
    resolved_ids = get_resolved_ids(load_json(RESOLVED_PATH))

    if not published:
        logger.info("No published signals to check")
        return {"checked": 0, "issues": []}

    issues = []
    checked = 0

    with httpx.Client(timeout=15) as client:
        for sig in published:
            sid = sig.get("signal_id", "?")
            mid = sig.get("market_id")

            if sid in resolved_ids:
                continue

            if not mid:
                continue

            market = check_market(str(mid), client)
            checked += 1

            if market is None:
                continue

            if market["status"] == "delisted":
                issues.append({"signal_id": sid, "market_id": mid, "problem": "delisted"})
            elif market.get("closed"):
                issues.append({"signal_id": sid, "market_id": mid, "problem": "closed"})
            elif market.get("resolved"):
                issues.append({"signal_id": sid, "market_id": mid, "problem": "resolved_but_untracked"})

            time.sleep(0.3)

    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total_published": len(published),
        "checked": checked,
        "skipped_resolved": len(resolved_ids),
        "issues_found": len(issues),
        "issues": issues,
    }

    REPORT_PATH.write_text(json.dumps(report, indent=2))
    logger.info("Checked %d markets, found %d issues", checked, len(issues))
    return report


def send_alert(report: dict) -> None:
    issues = report.get("issues", [])
    if not issues:
        return
    if not BOT_TOKEN or not CHANNEL_ID:
        logger.warning("No Telegram credentials; printing issues to stdout")
        for i in issues:
            print(f"  {i['signal_id']}: {i['problem']}")
        return

    lines = [f"🔍 *Market health check: {len(issues)} issue\\(s\\)*\n"]
    for i in issues:
        lines.append(f"• *{i['signal_id']}* — {i['problem']} \\(market {i['market_id']}\\)")

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
        logger.info("Sent market health alert")
    except httpx.HTTPError as exc:
        logger.error("Failed to send Telegram alert: %s", exc)


def main():
    report = run_health_check()
    if report["issues_found"] > 0:
        send_alert(report)
    else:
        logger.info("All markets healthy")


if __name__ == "__main__":
    main()
