"""
sync_dashboard.py — single entry point to sync all signal data to the public dashboard.

Call this after any signal publication to ensure the dashboard stays in sync.
It does three things:
  1. Ensures every signal in published_signals.json is also in signals.json
  2. Recomputes dashboard/accuracy.json
  3. Pushes to both origin (probbrain) and accuracy (probbrain-accuracy) repos

Usage:
    python tools/sync_dashboard.py [--signal-id SIG-024]

Also importable:
    from tools.sync_dashboard import sync
    sync(signal_id="SIG-024")
"""
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
SIGNALS_PATH = ROOT / "data" / "signals.json"
PUBLISHED_PATH = ROOT / "data" / "published_signals.json"


def _sync_signals_json() -> int:
    """Ensure every published signal exists in signals.json. Returns count of added entries."""
    published = json.loads(PUBLISHED_PATH.read_text()) if PUBLISHED_PATH.exists() else []
    signals = json.loads(SIGNALS_PATH.read_text()) if SIGNALS_PATH.exists() else []

    existing_nums = {s["signal_number"] for s in signals}
    added = 0

    for ps in published:
        sn = ps.get("signal_number")
        if sn is None or sn in existing_nums:
            continue

        entry = {
            "signal_number": sn,
            "signal_id": ps.get("signal_id", f"SIG-{sn:03d}"),
            "market_id": ps.get("market_id", ""),
            "question": ps.get("question", ""),
            "category": ps.get("category", "general"),
            "direction": ps.get("direction", ""),
            "confidence": ps.get("confidence", ""),
            "market_yes_price": ps.get("market_yes_price", 0),
            "our_calibrated_estimate": ps.get("our_calibrated_estimate", 0),
            "gap_pct": ps.get("gap_pct", 0),
            "volume_usdc": ps.get("volume_usdc", 0),
            "close_date": ps.get("close_date", ""),
            "evidence": ps.get("evidence", []),
            "published_at": ps.get("actually_posted_at") or ps.get("telegram_posted_at") or ps.get("published_at", ""),
        }
        signals.append(entry)
        existing_nums.add(sn)
        added += 1
        logger.info("sync_dashboard: added SIG-%03d to signals.json", sn)

    if added:
        SIGNALS_PATH.write_text(json.dumps(signals, indent=2, ensure_ascii=False))

    return added


def sync(signal_id: str = "") -> bool:
    """Full sync: signals.json → compute accuracy → push to both repos."""
    from tools.compute_accuracy import main as recompute_accuracy
    from tools.git_push_dashboard import push as push_dashboard

    # Step 1: Sync signals.json
    added = _sync_signals_json()
    logger.info("sync_dashboard: %d new signals added to signals.json", added)

    # Step 2: Recompute accuracy
    result = recompute_accuracy()
    logger.info("sync_dashboard: accuracy recomputed — %d published, %d resolved",
                result["signals_published"], result["signals_resolved"])

    # Step 3: Push to both repos
    ok = push_dashboard(signal_id=signal_id)
    if ok:
        logger.info("sync_dashboard: pushed to both repos")
    else:
        logger.warning("sync_dashboard: push failed or nothing to push")

    return ok


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    signal_id = ""
    if "--signal-id" in sys.argv:
        idx = sys.argv.index("--signal-id")
        if idx + 1 < len(sys.argv):
            signal_id = sys.argv[idx + 1]
    sync(signal_id=signal_id)


if __name__ == "__main__":
    main()
