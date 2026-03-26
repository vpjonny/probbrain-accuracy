"""
Post SIG-012: Will the Iranian regime fall before 2027? (NO_UNDERPRICED)
Sourced from PRO-191 signal description.
Content reviewed by Content Creator (PRO-193) and Twitter Engager (PRO-192).

Signal Confidence Rule applied: gap 15.5pp < 18% on a >6-month horizon (closes 2026-12-31)
→ badge downgraded from HIGH to MEDIUM per AGENTS.md rules.

This script:
1. Posts SIG-012 to Telegram then X
2. Updates data/published_signals.json
3. Pushes dashboard
4. PATCHes PRO-191 to done via Paperclip API

Usage: python tools/post_sig012_iran_regime_fall_2026_03_26.py [--dry-run]
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
PRO_191_ID = "37fe0411-fa4c-41cf-8c0e-0f69c90f7fef"

DRY_RUN = "--dry-run" in sys.argv

# Final copy — incorporates Content Creator (PRO-193) and Twitter Engager (PRO-192) feedback.
# Badge downgraded from HIGH → MEDIUM: gap 15.5pp < 18% on >6-month horizon (closes 2026-12-31).
# Tweet 2 trimmed from ~368 chars to ~247 chars by Twitter Engager.
SIGNAL = {
    "signal_number": 12,
    "signal_id": "SIG-012",
    "market_id": "iran-regime-fall-before-2027",
    "question": "Will the Iranian regime fall before 2027?",
    "category": "geopolitics",
    "direction": "NO_UNDERPRICED",
    "confidence": "MEDIUM",
    "our_estimate": 0.18,
    "market_price_at_signal": 0.335,
    "gap_pct": 15.5,
    "volume_usdc": 11750000,
    "close_date": "2026-12-31",
    "paperclip_issue": "PRO-191",
    "evidence": [
        "Khamenei survived the Feb 28 assassination attempt — hardliners consolidated power, succession not disrupted",
        "Mojtaba Khamenei installed as succession heir March 9, IRGC fully intact and loyal — institutional continuity secured",
        "Washington Times, Al Jazeera, WaPo: no credible collapse indicators as of March 26",
        "Manifold Markets independently prices ~26% — cross-platform crowd below Polymarket",
        "Shorter June 30 horizon only 22.5% — even conflict-accelerated markets don't see regime fall as likely near-term",
    ],
    "telegram_copy": (
        "\U0001f7e1 MEDIUM \u2014 Lean NO | MARKET SIGNAL\n\n"
        "\U0001f4ca Will the Iranian regime fall before 2027?\n\n"
        "Market: 33.5% YES | Our estimate: 18% YES\n"
        "Gap: 15.5pp (market overpricing YES)\n"
        "Volume: $11.75M\n"
        "Closes: 2026-12-31\n\n"
        "Evidence:\n"
        "\u2022 Khamenei survived the Feb 28 assassination attempt \u2014 hardliners consolidated power, succession not disrupted\n"
        "\u2022 Mojtaba Khamenei installed as succession heir March 9, IRGC fully intact and loyal \u2014 institutional continuity secured\n"
        "\u2022 Washington Times, Al Jazeera, WaPo: no credible collapse indicators as of March 26\n"
        "\u2022 Manifold Markets independently prices ~26% \u2014 cross-platform crowd below Polymarket\n"
        "\u2022 Shorter June 30 horizon only 22.5% \u2014 even conflict-accelerated markets don\u2019t see regime fall as likely near-term\n\n"
        "Counter-evidence: A prolonged US/Israeli air campaign targeting infrastructure could accelerate economic crisis "
        "and public unrest. The regime has survived 40+ years of pressure, but a sustained high-intensity conflict is "
        "a genuine stress test.\n\n"
        "\U0001f517 Trade on Polymarket: https://dub.sh/pb-tg\n\n"
        "\u26a0\ufe0f Not financial advice. Trade at your own risk.\n"
        "\U0001f4c8 Accuracy track record: https://vpjonny.github.io/probbrain-accuracy/"
    ),
    "x_thread_copy": {
        "tweet_1": (
            "Polymarket prices the Iranian regime falling before 2027 at 33.5%. "
            "Khamenei survived assassination in Feb. Mojtaba installed March 9 \u2014 IRGC intact. "
            "Our estimate: 18%. Gap: 15.5pp. [thread]"
        ),
        "tweet_2": (
            "Survived Khamenei\u2019s assassination (Feb 28). Mojtaba installed Mar 9, IRGC intact. "
            "WaTimes/AJ/WaPo: no collapse. Manifold ~26%. June 30 market: 22.5%.\n\n"
            "Market: 33.5% | Our: 18% | Gap: 15.5pp\n\n"
            "Trade NO: https://dub.sh/pb-x Not financial advice."
        ),
        "tweet_3": "We track every call publicly \u2192 https://vpjonny.github.io/probbrain-accuracy/",
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


def update_published(sig: dict, tg_result: dict, x_ids: list, posted_at: str):
    records = json.loads(PUBLISHED.read_text())
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
        "approved_by": "auto-PRO-191",
        "platforms": ["telegram", "x"],
        "telegram_link": "https://dub.sh/pb-tg",
        "x_link": "https://dub.sh/pb-x",
        "x_account": "@ProbBrain",
        "telegram_channel": "@ProbBrain",
        "evidence": sig["evidence"],
        "telegram_copy": sig["telegram_copy"],
        "x_thread_copy": sig["x_thread_copy"],
        "telegram_message_id": tg_result.get("result", {}).get("message_id") if not DRY_RUN else None,
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
    logger.info("published_signals.json updated for SIG-012")


def paperclip_mark_done(comment: str):
    if not PAPERCLIP_API_URL or not PAPERCLIP_API_KEY:
        logger.warning("Paperclip env vars not set — skipping done update")
        return
    url = f"{PAPERCLIP_API_URL}/api/issues/{PRO_191_ID}"
    headers = {
        "Authorization": f"Bearer {PAPERCLIP_API_KEY}",
        "Content-Type": "application/json",
        "X-Paperclip-Run-Id": PAPERCLIP_RUN_ID,
    }
    payload = {"status": "done", "comment": comment}
    with httpx.Client(timeout=20) as client:
        resp = client.patch(url, json=payload, headers=headers)
        if resp.status_code == 200:
            logger.info("PRO-191 marked done in Paperclip")
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
    logger.info("=== SIG-012 Iranian Regime Fall posting script starting (DRY_RUN=%s) ===", DRY_RUN)

    sig = SIGNAL
    tw = sig["x_thread_copy"]

    # Validate tweet lengths
    t1_len = len(tw["tweet_1"])
    t2_len = len(tw["tweet_2"])
    logger.info("Tweet 1 length: %d chars (limit 200 per agent spec)", t1_len)
    logger.info("Tweet 2 length: %d chars (limit 280)", t2_len)
    if t1_len > 200:
        logger.error("Tweet 1 exceeds 200 chars (%d) — aborting", t1_len)
        sys.exit(1)
    if t2_len > 280:
        logger.error("Tweet 2 exceeds 280 chars (%d) — aborting", t2_len)
        sys.exit(1)

    # Telegram
    logger.info("Posting SIG-012 to Telegram...")
    if DRY_RUN:
        logger.info("DRY RUN Telegram:\n%s", sig["telegram_copy"])
        tg_result = {"ok": True, "dry_run": True, "result": {"message_id": -1}}
    else:
        tg_result = telegram_send(sig["telegram_copy"])
        logger.info("Telegram OK — message_id=%s", tg_result.get("result", {}).get("message_id"))

    time.sleep(3)

    # X thread
    logger.info("Posting SIG-012 X thread...")
    if DRY_RUN:
        logger.info(
            "DRY RUN X:\nTweet 1: %s\nTweet 2: %s\nTweet 3: %s",
            tw["tweet_1"], tw["tweet_2"], tw["tweet_3"],
        )
        x_ids = ["dry-t1", "dry-t2", "dry-t3"]
    else:
        x_ids = x_post_thread(tw["tweet_1"], tw["tweet_2"], tw["tweet_3"])

    posted_at = datetime.now(timezone.utc).isoformat()
    update_published(sig, tg_result, x_ids, posted_at)
    logger.info("SIG-012 posted at %s", posted_at)

    logger.info("Pushing dashboard...")
    if not DRY_RUN:
        push_dashboard()

    summary = (
        "SIG-012 posted to Telegram (@ProbBrain) and X (@ProbBrain).\n\n"
        "**Signal:** Will the Iranian regime fall before 2027?\n"
        "**Direction:** NO_UNDERPRICED | **Confidence:** MEDIUM\n"
        "(Downgraded from HIGH: gap 15.5pp < 18% on >6-month horizon per agent rules.)\n"
        "**Market:** 33.5% YES | **Our estimate:** 18% YES | **Gap:** 15.5pp\n"
        "**Volume:** $11.75M | **Closes:** 2026-12-31\n\n"
        "Copy reviewed by Content Creator ([PRO-193](/PRO/issues/PRO-193)) "
        "and Twitter Engager ([PRO-192](/PRO/issues/PRO-192)).\n"
        "Auto-published (gap < 20pp, approval_required: false).\n\n"
        "Dashboard pushed. Not financial advice."
    )
    if not DRY_RUN:
        paperclip_mark_done(summary)
    else:
        logger.info("DRY RUN — would mark PRO-191 done with:\n%s", summary)

    logger.info("=== Script complete ===")


if __name__ == "__main__":
    main()
