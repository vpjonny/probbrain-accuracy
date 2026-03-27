"""
Post SIG-018 to Telegram: Will Shai Gilgeous-Alexander win the 2025–26 NBA MVP?
X thread was posted at 16:11Z. Telegram was skipped due to incorrect daily limit (5 vs actual 40).
This script posts the Telegram copy only and updates published_signals.json.

Usage: python tools/post_sig018_telegram_2026_03_26.py [--dry-run]
"""
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent
PUBLISHED = BASE / "data" / "published_signals.json"
DRY_RUN = "--dry-run" in sys.argv

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
TELEGRAM_API = "https://api.telegram.org"

TELEGRAM_COPY = (
    "\U0001f534 HIGH \u2014 Bet YES | MARKET SIGNAL\n\n"
    "\U0001f4ca Will Shai Gilgeous-Alexander win the 2025\u201326 NBA MVP?\n\n"
    "Market: 81.5% YES | Our estimate: 93.8% YES\n"
    "Gap: 12.3pp (market underpricing YES)\n"
    "Volume: $2.1M\n"
    "Closes: 2026-06-10\n\n"
    "Evidence:\n"
    "\u2022 FanDuel -1500 (93.75% implied) \u2014 market consensus across all major books\n"
    "\u2022 BetMGM, DraftKings, OddsShark: consensus -850 to -1500\n"
    "\u2022 Nearest competitor Luka Doncic at +1000 (~9%) \u2014 not close\n"
    "\u2022 Polymarket multi-contract structure systematically underweights dominant frontrunner\n\n"
    "Counter-evidence: Season-ending injury remains the primary risk. Voter fatigue or a late-season "
    "surge by Doncic/Jokic could narrow the gap. The 18.5% residual in the market price already "
    "reflects these tail risks.\n\n"
    "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
    "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
    "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/\n"
    "\U0001f426 Follow us on X: https://x.com/ProbBrain"
)


def telegram_send(text: str) -> dict:
    url = f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "disable_web_page_preview": True}
    with httpx.Client(timeout=20) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


def update_published(tg_result: dict, posted_at: str):
    records = json.loads(PUBLISHED.read_text())
    # Find existing SIG-018 entry and update it to include telegram
    for rec in records:
        if rec.get("signal_id") == "SIG-018" and rec.get("actually_posted_at", "").startswith("2026-03-26"):
            rec["platforms"] = ["telegram", "x"]
            rec["telegram_copy"] = TELEGRAM_COPY
            rec["telegram_skipped_reason"] = None
            rec["telegram_message_id"] = tg_result.get("result", {}).get("message_id") if tg_result else None
            rec["telegram_posted_at"] = posted_at
            rec["our_calibrated_estimate"] = 0.938  # Fix 93% → 93.8%
            break
    PUBLISHED.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    logger.info("published_signals.json updated — SIG-018 now includes Telegram")


def main():
    logger.info("=== SIG-018 Telegram posting script (DRY_RUN=%s) ===", DRY_RUN)

    # Rate limit check
    records = json.loads(PUBLISHED.read_text())
    all_times = [p.get("actually_posted_at") for p in records if p.get("actually_posted_at")]
    tg_times = [p.get("telegram_posted_at") for p in records if p.get("telegram_posted_at")]
    all_post_times = [t for t in all_times + tg_times if t]
    if all_post_times:
        last_post = datetime.fromisoformat(max(all_post_times))
        now = datetime.now(timezone.utc)
        elapsed = (now - last_post).total_seconds()
        if elapsed < 1800 and not DRY_RUN:
            logger.error("Rate limit: %.0fs since last post (need 1800). Aborting.", elapsed)
            sys.exit(1)
        logger.info("Gap since last post: %.0fs (minimum 1800)", elapsed)

    # Count today's Telegram posts
    today_tg = sum(1 for p in records if "telegram" in (p.get("platforms") or [])
                   and p.get("actually_posted_at", "").startswith("2026-03-26"))
    logger.info("Telegram posts today: %d / 40", today_tg)
    if today_tg >= 40 and not DRY_RUN:
        logger.error("Telegram daily limit reached (%d/40). Aborting.", today_tg)
        sys.exit(1)

    logger.info("Posting SIG-018 to Telegram...")
    if DRY_RUN:
        logger.info("DRY RUN Telegram:\n%s", TELEGRAM_COPY)
        tg_result = {"ok": True, "result": {"message_id": -1}}
    else:
        tg_result = telegram_send(TELEGRAM_COPY)
        logger.info("Telegram OK — message_id=%s", tg_result.get("result", {}).get("message_id"))

    posted_at = datetime.now(timezone.utc).isoformat()
    update_published(tg_result, posted_at)
    logger.info("SIG-018 Telegram posted at %s", posted_at)
    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
