"""
Post SIG-019: Will the Colorado Avalanche win the 2026 NHL Stanley Cup? (YES_UNDERPRICED)
Sourced from PRO-237 task description.
Content reviewed by Content Creator (PRO-238) — APPROVED with edits.
X thread reviewed by Twitter Engager (PRO-239) — APPROVED with edits.

Edits applied from review:
  - Removed Kadri acquisition claim (not in Research Agent evidence; flagged as potentially wrong)
  - Added NFA disclaimer to X thread tweet 2
  - Added dashboard link in X thread tweet 3
  - Added affiliate link to X thread tweet 2
  - SportsBettingDime cited as source without @mention (unverified attribution)

Signal checks:
  - Volume: $13,214,197 — passes $50k liquidity gate ✓
  - Gap: 8.8pp — approval_required: false (< 20pp) ✓
  - Confidence: MEDIUM ✓
  - Close: 2026-06-30 (~96 days — not long-horizon) ✓
  - Evidence: present ✓

This script:
1. Posts SIG-019 to Telegram then X
2. Updates data/published_signals.json
3. Pushes dashboard
4. PATCHes PRO-237 to done via Paperclip API

Usage: python tools/post_sig019_avalanche_nhl_2026_03_26.py [--dry-run]
"""
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

import httpx
import tweepy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent
PUBLISHED = BASE / "data" / "published_signals.json"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID", "").strip()
TELEGRAM_API = "https://api.telegram.org"

PAPERCLIP_API_URL = os.getenv("PAPERCLIP_API_URL", "").strip()
PAPERCLIP_API_KEY = os.getenv("PAPERCLIP_API_KEY", "").strip()
PAPERCLIP_RUN_ID = os.getenv("PAPERCLIP_RUN_ID", "").strip()
PRO_237_ID = "866412f9-6fba-4844-9fe7-020713e6385a"

DRY_RUN = "--dry-run" in sys.argv

# Final copy — incorporates Content Creator (PRO-238) and Twitter Engager (PRO-239) feedback.
# Tweet 1: 162 chars ✓  Tweet 2: ~248 Twitter-weighted chars ✓ (URL counted as 23 by Twitter)
SIGNAL = {
    "signal_number": 19,
    "signal_id": "SIG-019",
    "market_id": "colorado-avalanche-2026-nhl-stanley-cup",
    "question": "Will the Colorado Avalanche win the 2026 NHL Stanley Cup?",
    "category": "sports",
    "direction": "YES_UNDERPRICED",
    "confidence": "MEDIUM",
    "our_estimate": 0.278,
    "market_price_at_signal": 0.190,
    "gap_pct": 8.8,
    "volume_usdc": 13214197,
    "close_date": "2026-06-30",
    "paperclip_issue": "PRO-237",
    "evidence": [
        "SportsBettingDime: Avalanche +260 post-trade-deadline (27.8% implied), best odds in NHL",
        "NHL standings (March 26): Colorado 47-13-10, 104 pts — best record in entire NHL",
    ],
    "telegram_copy": (
        "\U0001f7e1 MEDIUM \u2014 Lean YES | MARKET SIGNAL\n\n"
        "\U0001f4ca Will the Colorado Avalanche win the 2026 NHL Stanley Cup?\n\n"
        "Market: 19% YES | Our estimate: 27.8% YES\n"
        "Gap: 8.8pp (market underpricing YES)\n"
        "Volume: $13,214k\n"
        "Closes: 2026-06-30\n\n"
        "Evidence:\n"
        "\u2022 SportsBettingDime: Avalanche +260 post-trade-deadline (27.8% implied), best odds in NHL\n"
        "\u2022 NHL standings (March 26): Colorado 47-13-10, 104 pts \u2014 best record in entire NHL\n\n"
        "Counter-evidence: The Stanley Cup is a two-month playoff gauntlet where even the "
        "league\u2019s best regular-season team faces significant bracket uncertainty \u2014 "
        "Colorado must navigate four rounds of seven-game series against motivated opponents.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/"
    ),
    "x_thread_copy": {
        "tweet_1": (
            "Colorado Avalanche: best record in the NHL (47-13-10). "
            "Polymarket prices them at 19% to win the Stanley Cup. "
            "Sportsbooks imply 27.8%. That\u2019s an 8.8pp gap. [thread]"
        ),
        "tweet_2": (
            "Avalanche YES underpriced at 19%:\n\n"
            "\u2022 SportsBettingDime: +260 post-deadline \u2192 27.8% implied\n"
            "\u2022 NHL standings: 47-13-10, 104 pts \u2014 best record in the league\n\n"
            "Market: 19% | Our: 27.8% | Gap: 8.8pp\n\n"
            "Trade: https://dub.sh/pb-x\n\n"
            "Not financial advice."
        ),
        "tweet_3": (
            "We track every call publicly.\n"
            "Accuracy dashboard: https://vpjonny.github.io/probbrain-accuracy/\n\n"
            "Join us on Telegram: https://t.me/ProbBrain\n"
            "Follow @ProbBrain for more signals."
        ),
    },
}


def telegram_send(text: str) -> dict:
    url = f"{TELEGRAM_API}/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHANNEL_ID, "text": text, "disable_web_page_preview": True}
    with httpx.Client(timeout=20) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        return resp.json()


def x_post_thread(tweet1: str, tweet2: str, tweet3: str) -> list:
    client = tweepy.Client(
        consumer_key=os.getenv("X_CONSUMER_KEY", "").strip(),
        consumer_secret=os.getenv("X_CONSUMER_SECRET", "").strip(),
        access_token=os.getenv("X_ACCESS_TOKEN", "").strip(),
        access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET", "").strip(),
    )
    ids = []
    r1 = client.create_tweet(text=tweet1)
    t1 = r1.data["id"]
    ids.append(str(t1))
    logger.info("X tweet 1 posted (id=%s)", t1)
    time.sleep(2)

    r2 = client.create_tweet(text=tweet2, in_reply_to_tweet_id=t1)
    t2 = r2.data["id"]
    ids.append(str(t2))
    logger.info("X tweet 2 posted (id=%s)", t2)
    time.sleep(2)

    r3 = client.create_tweet(text=tweet3, in_reply_to_tweet_id=t2)
    t3 = r3.data["id"]
    ids.append(str(t3))
    logger.info("X tweet 3 posted (id=%s)", t3)
    return ids


def update_published(sig: dict, tg_result: dict, x_ids: list, posted_at: str, platforms: list):
    records = json.loads(PUBLISHED.read_text())
    tg_skipped = "telegram" not in platforms
    entry = {
        "signal_number": sig["signal_number"],
        "signal_id": sig["signal_id"],
        "market_id": sig["market_id"],
        "question": sig["question"],
        "category": sig["category"],
        "direction": sig["direction"],
        "confidence": sig["confidence"],
        "market_yes_price": sig["market_price_at_signal"],
        "our_calibrated_estimate": sig["our_estimate"],
        "gap_pct": sig["gap_pct"],
        "volume_usdc": sig["volume_usdc"],
        "close_date": sig["close_date"],
        "approved_by": "auto-PRO-237",
        "platforms": platforms,
        "telegram_link": "https://dub.sh/pb-tg",
        "x_link": "https://dub.sh/pb-x",
        "x_account": "@ProbBrain",
        "telegram_channel": "@ProbBrain",
        "evidence": sig["evidence"],
        "telegram_copy": None if tg_skipped else sig["telegram_copy"],
        "telegram_skipped_reason": "Telegram daily limit reached (6/5 signals posted today)" if tg_skipped else None,
        "x_thread_copy": sig["x_thread_copy"],
        "telegram_message_id": tg_result.get("result", {}).get("message_id") if tg_result else None,
        "x_tweet_ids": {
            "tweet_1": x_ids[0] if len(x_ids) > 0 else None,
            "tweet_2": x_ids[1] if len(x_ids) > 1 else None,
            "tweet_3": x_ids[2] if len(x_ids) > 2 else None,
        },
        "paperclip_issue": sig["paperclip_issue"],
        "actually_posted_at": posted_at,
    }
    records.append(entry)
    PUBLISHED.write_text(json.dumps(records, indent=2, ensure_ascii=False))
    logger.info("published_signals.json updated for SIG-019")


def paperclip_mark_done(comment: str):
    if not PAPERCLIP_API_URL or not PAPERCLIP_API_KEY:
        logger.warning("Paperclip env vars not set — skipping done update")
        return
    url = f"{PAPERCLIP_API_URL}/api/issues/{PRO_237_ID}"
    headers = {
        "Authorization": f"Bearer {PAPERCLIP_API_KEY}",
        "Content-Type": "application/json",
        "X-Paperclip-Run-Id": PAPERCLIP_RUN_ID,
    }
    payload = {"status": "done", "comment": comment}
    with httpx.Client(timeout=20) as client:
        resp = client.patch(url, json=payload, headers=headers)
        if resp.status_code == 200:
            logger.info("PRO-237 marked done in Paperclip")
        else:
            logger.error("Paperclip PATCH failed: %s %s", resp.status_code, resp.text)


def push_dashboard():
    import subprocess
    result = subprocess.run(
        ["python3", str(BASE / "tools" / "git_push_dashboard.py")],
        capture_output=True,
        text=True,
        cwd=str(BASE),
    )
    if result.returncode == 0:
        logger.info("Dashboard pushed successfully")
    else:
        logger.warning("Dashboard push stderr: %s", result.stderr[:300])


def main():
    logger.info("=== SIG-019 Colorado Avalanche posting script starting (DRY_RUN=%s) ===", DRY_RUN)

    # Enforce 30-minute gap from last post
    records = json.loads(PUBLISHED.read_text())
    all_times = [p.get("actually_posted_at") for p in records if p.get("actually_posted_at")]
    if all_times:
        last_post_str = max(all_times)
        last_post = datetime.fromisoformat(last_post_str)
        now = datetime.now(timezone.utc)
        elapsed = (now - last_post).total_seconds()
        if elapsed < 1800 and not DRY_RUN:
            logger.error(
                "Rate limit: only %.0f seconds since last post (need 1800). Aborting.",
                elapsed,
            )
            sys.exit(1)
        logger.info("Gap since last post: %.0f seconds (minimum 1800)", elapsed)

    # Check daily Telegram limit (max 5)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    tg_today = [
        p for p in records
        if p.get("actually_posted_at", "").startswith(today)
        and "telegram" in p.get("platforms", [])
    ]
    skip_telegram = len(tg_today) >= 5
    if skip_telegram:
        logger.warning("Telegram daily limit reached (%d/5) — skipping Telegram, posting X only.", len(tg_today))
    else:
        logger.info("Telegram today: %d/5", len(tg_today))

    # Check daily X limit (max 40)
    x_today = [
        p for p in records
        if p.get("actually_posted_at", "").startswith(today)
        and "x" in p.get("platforms", [])
    ]
    if len(x_today) >= 40 and not DRY_RUN:
        logger.error("X daily limit reached (%d/40). Aborting.", len(x_today))
        sys.exit(1)
    logger.info("X today: %d/40", len(x_today))

    sig = SIGNAL
    tw = sig["x_thread_copy"]

    # Validate tweet lengths
    t1_len = len(tw["tweet_1"])
    t2_raw = len(tw["tweet_2"])
    # URL https://dub.sh/pb-x (20 chars raw) counts as 23 on Twitter (+3)
    t2_twitter = t2_raw + 3
    logger.info("Tweet 1 length: %d chars (limit 200 per agent spec)", t1_len)
    logger.info("Tweet 2 length: %d raw / %d Twitter-weighted (limit 280)", t2_raw, t2_twitter)
    if t1_len > 200:
        logger.error("Tweet 1 exceeds 200 chars — aborting")
        sys.exit(1)
    if t2_twitter > 280:
        logger.error("Tweet 2 exceeds 280 chars Twitter-weighted (%d) — aborting", t2_twitter)
        sys.exit(1)

    # Telegram
    tg_result = None
    if skip_telegram:
        logger.info("Telegram skipped (daily limit %d/5).", len(tg_today))
    elif DRY_RUN:
        logger.info("DRY RUN Telegram:\n%s", sig["telegram_copy"])
        tg_result = {"ok": True, "dry_run": True, "result": {"message_id": -1}}
    else:
        logger.info("Posting SIG-019 to Telegram...")
        tg_result = telegram_send(sig["telegram_copy"])
        logger.info("Telegram OK — message_id=%s", tg_result.get("result", {}).get("message_id"))
        time.sleep(3)

    # X thread
    logger.info("Posting SIG-019 X thread...")
    if DRY_RUN:
        logger.info(
            "DRY RUN X:\nTweet 1 (%d chars): %s\nTweet 2 (%d raw / %d Twitter chars): %s\nTweet 3: %s",
            t1_len, tw["tweet_1"], t2_raw, t2_twitter, tw["tweet_2"], tw["tweet_3"],
        )
        x_ids = ["dry-t1", "dry-t2", "dry-t3"]
    else:
        x_ids = x_post_thread(tw["tweet_1"], tw["tweet_2"], tw["tweet_3"])

    posted_at = datetime.now(timezone.utc).isoformat()

    tg_status = "skipped (daily limit 6/5)" if skip_telegram else "posted ✓"
    platforms = ["x"] if skip_telegram else ["telegram", "x"]

    if not DRY_RUN:
        update_published(sig, tg_result or {}, x_ids, posted_at, platforms)
        logger.info("SIG-019 posted at %s", posted_at)
        logger.info("Pushing dashboard...")
        push_dashboard()
        paperclip_mark_done(
            "SIG-019 (Colorado Avalanche NHL Stanley Cup) published.\n\n"
            f"**Telegram:** {tg_status}\n"
            "**X:** thread posted ✓\n\n"
            "Edits applied per [PRO-238](/PRO/issues/PRO-238) + [PRO-239](/PRO/issues/PRO-239) review:\n"
            "- Removed Kadri claim (not in Research Agent evidence)\n"
            "- Added NFA disclaimer to X thread\n"
            "- Added dashboard link to X tweet 3\n"
            "- Added affiliate link to X tweet 2\n"
            "- SportsBettingDime cited without @mention\n\n"
            f"Posted at: {posted_at}"
        )
    else:
        logger.info("DRY RUN — skipping published_signals.json update, dashboard push, and Paperclip update")

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
