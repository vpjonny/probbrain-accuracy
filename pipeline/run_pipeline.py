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
  7. post_x_threads()      — build and post threads for published signals
"""
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional

from scanner.polymarket import fetch_markets, save_snapshot
from scanner.models import Market
from pipeline.signals import detect_signals
from pipeline.publisher import publish_signals
from pipeline import x_publisher
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


def _lookup_signal_by_market_id(market_id: str) -> Optional[dict]:
    """Look up a signal by market_id from signals.json."""
    if not SIGNALS_PATH.exists():
        return None
    try:
        signals = json.loads(SIGNALS_PATH.read_text())
        for s in signals:
            if str(s.get("market_id", "")) == str(market_id):
                return s
    except (json.JSONDecodeError, KeyError):
        logger.warning("Could not parse %s for signal lookup", SIGNALS_PATH)
    return None


def _post_x_thread_for_signal(signal_data: dict, market: Market, dry_run: bool = False) -> Optional[list[str]]:
    """Build and post an X thread for a signal. Returns list of tweet IDs or None on failure."""
    try:
        thread = x_publisher.build_thread(
            question=signal_data.get("question") or market.question,
            market_yes_pct=signal_data.get("market_price", market.yes_price) * 100,
            our_estimate_pct=signal_data.get("our_calibrated_estimate", 0) * 100,
            gap_pct=signal_data.get("gap_pct", 0),
            direction=signal_data.get("direction", ""),
            confidence=signal_data.get("confidence", "MEDIUM"),
            evidence=signal_data.get("evidence", []),
            close_date=signal_data.get("close_date", market.close_date.isoformat() if market.close_date else ""),
            volume_usdc=market.volume_usd,
        )
        tweet_ids = x_publisher.post_thread(thread, dry_run=dry_run)
        if tweet_ids:
            logger.info("Posted X thread for signal SIG-%s (3 tweets, ids=%s)",
                        signal_data.get("signal_number"), tweet_ids)
        return tweet_ids
    except Exception as exc:
        logger.error("Failed to post X thread for market %s: %s", market.id, exc)
        return None


def _update_published_signals_with_x_threads(published_market_ids: List[str], markets_by_id: dict) -> None:
    """
    Update published_signals.json to include X tweet IDs for newly published signals.
    Looks up each published market in signals.json and posts X thread.
    """
    if not published_market_ids:
        return

    if not PUBLISHED_SIGNALS_PATH.exists():
        logger.warning("published_signals.json not found; skipping X thread posting")
        return

    published_signals = json.loads(PUBLISHED_SIGNALS_PATH.read_text())

    for entry in published_signals:
        market_id = str(entry.get("market_id", ""))
        if market_id not in published_market_ids:
            continue
        # Skip if already has X tweet IDs
        if entry.get("x_tweet_ids"):
            logger.info("Market %s already has X tweets posted; skipping", market_id)
            continue

        signal_data = _lookup_signal_by_market_id(market_id)
        market = markets_by_id.get(market_id)
        if not signal_data or not market:
            logger.warning("Could not find signal or market data for market_id %s; skipping X thread", market_id)
            continue

        tweet_ids = _post_x_thread_for_signal(signal_data, market)
        if tweet_ids:
            entry["x_tweet_ids"] = {
                "tweet_1": tweet_ids[0],
                "tweet_2": tweet_ids[1],
                "tweet_3": tweet_ids[2],
            }

    # Write updated published_signals.json
    PUBLISHED_SIGNALS_PATH.write_text(json.dumps(published_signals, indent=2))
    logger.info("Updated published_signals.json with X thread IDs")


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

    # 4b. Dedup — remove signals already in published_signals.json
    if signals and not dry_run:
        already_published = set()
        if PUBLISHED_SIGNALS_PATH.exists():
            try:
                pub = json.loads(PUBLISHED_SIGNALS_PATH.read_text())
                already_published = {str(s.get("market_id", "")) for s in pub if s.get("market_id")}
            except (json.JSONDecodeError, KeyError):
                pass
        before = len(signals)
        signals = [s for s in signals if str(s.id) not in already_published]
        skipped = before - len(signals)
        if skipped:
            logger.info("DEDUP: filtered out %d already-published signal(s)", skipped)

    # 5. Publish (or dry-run log)
    published = 0
    published_market_ids = []
    if signals:
        if dry_run:
            for s in signals:
                logger.info("[DRY RUN] Would publish: %s — %.1f%%", s.question[:60], s.implied_probability)
        else:
            published = publish_signals(signals)
            if published > 0:
                # Track which markets were published for X thread posting
                published_market_ids = [str(s.id) for s in signals]
                recompute_accuracy()
                push_dashboard()

    # 6. Post X threads for published signals (after Telegram)
    if published_market_ids and not dry_run:
        markets_by_id = {str(m.id): m for m in markets}
        _update_published_signals_with_x_threads(published_market_ids, markets_by_id)

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
