"""
sync_dashboard.py — single entry point to sync all signal data to the public dashboard.

Call this after any signal publication or resolution to ensure the dashboard stays in sync.
It does three things:
  1. Ensures every signal in published_signals.json is also in signals.json
  2. Recomputes dashboard/accuracy.json from resolved.json
  3. Pushes to both origin (probbrain) and accuracy (probbrain-accuracy) repos

Usage:
    python tools/sync_dashboard.py [--signal-id SIG-024]

Also importable:
    from tools.sync_dashboard import sync
    sync(signal_id="SIG-024")

AUTO-SYNC: This script automatically detects and syncs when resolved.json changes.
The monitor_resolved.py script can watch for changes and trigger auto-sync continuously.

Usage for auto-sync:
    python tools/monitor_resolved.py              # One-time check
    python tools/monitor_resolved.py --watch      # Continuous monitoring (background)
"""
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
SIGNALS_PATH = ROOT / "data" / "signals.json"
PUBLISHED_PATH = ROOT / "data" / "published_signals.json"
SLUGS_PATH = ROOT / "data" / "polymarket_slugs.json"


def _extract_signal_number(ps: dict) -> int | None:
    """Extract signal_number from a published signal entry, falling back to signal_id parsing."""
    sn = ps.get("signal_number")
    if sn is not None:
        return int(sn)
    sid = ps.get("signal_id", "")
    if sid.startswith("SIG-"):
        try:
            return int(sid.split("-", 1)[1])
        except (ValueError, IndexError):
            pass
    return None


def _sync_signals_json() -> int:
    """Ensure every published signal exists in signals.json. Returns count of added entries."""
    published = json.loads(PUBLISHED_PATH.read_text()) if PUBLISHED_PATH.exists() else []
    signals = json.loads(SIGNALS_PATH.read_text()) if SIGNALS_PATH.exists() else []

    existing_nums = {s["signal_number"] for s in signals if "signal_number" in s}
    existing_ids = {s.get("signal_id") for s in signals}
    added = 0

    for ps in published:
        # Skip non-signal entries (e.g. edge threads)
        if ps.get("type") in ("edge_thread",):
            continue
        sn = _extract_signal_number(ps)
        if sn is None:
            continue
        sid = ps.get("signal_id", f"SIG-{sn:03d}")
        if sn in existing_nums or sid in existing_ids:
            continue

        market_price = ps.get("market_yes_price") or ps.get("market_price_at_signal") or ps.get("market_price", 0)
        our_est = ps.get("our_calibrated_estimate") or ps.get("our_estimate") or ps.get("our_estimate_yes", 0)
        entry = {
            "signal_number": sn,
            "signal_id": sid,
            "market_id": ps.get("market_id", ""),
            "question": ps.get("question") or ps.get("market_question", ""),
            "category": ps.get("category", "general"),
            "direction": ps.get("direction", ""),
            "confidence": ps.get("confidence", ""),
            "market_price": market_price,
            "market_price_at_signal": market_price,
            "our_estimate": our_est,
            "our_calibrated_estimate": our_est,
            "market_yes_price": market_price,
            "gap_pct": ps.get("gap_pct") or ps.get("gap_pp", 0),
            "volume_usdc": ps.get("volume_usdc", 0),
            "close_date": ps.get("close_date") or ps.get("closes", ""),
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
    # Add parent dir to path for imports when running as script
    sys.path.insert(0, str(ROOT))
    from tools.compute_accuracy import main as recompute_accuracy
    from tools.git_push_dashboard import push as push_dashboard
    from tools.validate_signals import backfill, validate

    # Step 1: Sync signals.json
    added = _sync_signals_json()
    logger.info("sync_dashboard: %d new signals added to signals.json", added)

    # Step 1b: Validate and fix slugs via Gamma API
    try:
        from tools.validate_slugs import validate_and_fix
        slug_result = validate_and_fix(fix=True)
        if slug_result["fixed"]:
            logger.info("sync_dashboard: auto-fixed %d wrong Polymarket slugs", slug_result["fixed"])
    except Exception as e:
        logger.warning("sync_dashboard: slug validation skipped — %s", e)

    # Step 1c: Backfill any missing price fields
    fixed = backfill()
    if fixed:
        logger.info("sync_dashboard: backfilled %d signal(s) with missing price data", fixed)

    # Step 1d: Validate — warn but don't block
    signals = json.loads(SIGNALS_PATH.read_text()) if SIGNALS_PATH.exists() else []
    issues = validate(signals)
    if issues:
        for issue in issues:
            logger.warning("sync_dashboard: validation issue — %s: %s (%s)",
                           issue["signal_id"], issue["field"], issue["issue"])

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
