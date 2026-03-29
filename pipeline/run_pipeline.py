"""
End-to-end pipeline: scan → detect signals → stage for approval → publish.
Can be run once (cron) or via the scheduler module.

Flow:
  1. fetch_markets()       — Polymarket Gamma API → filtered Market list
  2. save_snapshot()       — timestamped JSON snapshot in data/
  3. detect_signals()      — filter to notable markets
  4. global approval gate  — if count threshold not met (publisher.json),
                             stage all to pending_signals.json and stop
  5. per-signal gate       — signals with approval_required: true in signals.json
                             are staged to pending_signals.json; rest proceed
  6. publish_signals()     — send approved signals to Telegram channel
"""
import json
import logging
import sys
from pathlib import Path
from typing import List

from scanner.polymarket import fetch_markets, save_snapshot
from scanner.models import Market
from pipeline.signals import detect_signals
from pipeline.publisher import publish_signals
from tools.compute_accuracy import main as recompute_accuracy
from tools.git_push_dashboard import push as push_dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

PUBLISHER_CONFIG_PATH = Path("config/publisher.json")
PENDING_SIGNALS_PATH = Path("data/pending_signals.json")
PUBLISHED_SIGNALS_PATH = Path("data/published_signals.json")
SIGNALS_PATH = Path("data/signals.json")


def _load_publisher_config() -> dict:
    if PUBLISHER_CONFIG_PATH.exists():
        return json.loads(PUBLISHER_CONFIG_PATH.read_text())
    return {}


def _approval_required() -> bool:
    """Return True if we haven't yet crossed the approval threshold."""
    config = _load_publisher_config()
    threshold = config.get("approval_required_until_signal_count", 0)
    if threshold == 0:
        return False
    if PUBLISHED_SIGNALS_PATH.exists():
        published = json.loads(PUBLISHED_SIGNALS_PATH.read_text())
    else:
        published = []
    return len(published) < threshold


def _signals_requiring_approval() -> set:
    """Return set of market IDs that have approval_required: true in signals.json."""
    if not SIGNALS_PATH.exists():
        return set()
    signals = json.loads(SIGNALS_PATH.read_text())
    return {s.get("market_id") for s in signals if s.get("approval_required")}


def _stage_signals(signals: List[Market]) -> None:
    """Append detected signals to pending_signals.json awaiting approval."""
    if PENDING_SIGNALS_PATH.exists():
        existing = json.loads(PENDING_SIGNALS_PATH.read_text())
    else:
        existing = []
    existing_ids = {s.get("id") or s.get("market_id") for s in existing}
    for m in signals:
        if m.id not in existing_ids:
            existing.append(m.to_dict())
    PENDING_SIGNALS_PATH.write_text(json.dumps(existing, indent=2))
    logger.info("Staged %d signal(s) → %s", len(signals), PENDING_SIGNALS_PATH)


def run(dry_run: bool = False, max_signals: int = 5, force_publish: bool = False) -> dict:
    """
    Full pipeline run.

    Args:
        dry_run:       If True, skip publishing (just log what would be sent).
        max_signals:   Cap on signals to publish per run.
        force_publish: Bypass approval gate (use for manual approval flows).

    Returns:
        Summary dict with counts.
    """
    logger.info("Pipeline start (dry_run=%s, force_publish=%s)", dry_run, force_publish)

    # 1. Scan
    markets = fetch_markets(filtered=True)
    snapshot_path = save_snapshot(markets)
    logger.info("Snapshot saved: %s (%d markets)", snapshot_path, len(markets))

    # 2. Detect signals
    signals = detect_signals(markets)[:max_signals]
    logger.info("Signals detected: %d", len(signals))

    # 3. Approval gate — stage if threshold not yet met
    if signals and not force_publish and not dry_run and _approval_required():
        _stage_signals(signals)
        summary = {
            "markets_scanned": len(markets),
            "signals_detected": len(signals),
            "signals_staged": len(signals),
            "signals_published": 0,
            "snapshot": str(snapshot_path),
            "dry_run": dry_run,
            "approval_required": True,
            "pending_signals_path": str(PENDING_SIGNALS_PATH),
        }
        logger.info("Pipeline staged (approval required): %s", summary)
        return summary

    # 4. Per-signal approval gate — split out signals with approval_required: true
    if signals and not force_publish and not dry_run:
        blocked_ids = _signals_requiring_approval()
        if blocked_ids:
            needs_approval = [s for s in signals if s.id in blocked_ids]
            signals = [s for s in signals if s.id not in blocked_ids]
            if needs_approval:
                _stage_signals(needs_approval)
                logger.info(
                    "Held %d signal(s) for per-signal approval: %s",
                    len(needs_approval),
                    [s.id for s in needs_approval],
                )

    # 5. Publish (or dry-run log)
    published = 0
    if signals:
        if dry_run:
            for s in signals:
                logger.info("[DRY RUN] Would publish: %s — %.1f%%", s.question[:60], s.implied_probability)
        else:
            published = publish_signals(signals)
            if published > 0:
                recompute_accuracy()
                push_dashboard()

    summary = {
        "markets_scanned": len(markets),
        "signals_detected": len(signals),
        "signals_published": published,
        "snapshot": str(snapshot_path),
        "dry_run": dry_run,
    }
    logger.info("Pipeline complete: %s", summary)
    return summary


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    force = "--force-publish" in sys.argv
    result = run(dry_run=dry, force_publish=force)
    print(result)
