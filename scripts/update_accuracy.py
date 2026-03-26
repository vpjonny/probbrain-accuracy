#!/usr/bin/env python3
"""
update_accuracy.py — regenerate dashboard/accuracy.json from signals data.

Reads:
  data/resolved.json     — list of resolved signal dicts
  data/pending_signals.json  — list of pending (unresolved) signal dicts

Writes:
  dashboard/accuracy.json

Run manually or via GitHub Actions on each pipeline cycle.
"""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESOLVED_PATH = ROOT / "data" / "resolved.json"
PENDING_PATH = ROOT / "data" / "pending_signals.json"
SIGNALS_PATH = ROOT / "data" / "signals.json"
OUTPUT_PATH = ROOT / "dashboard" / "accuracy.json"


def load_json(path: Path) -> list:
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    return []


def brier_score(signals: list) -> float | None:
    """Average Brier score over resolved signals that have probability + outcome."""
    valid = [s for s in signals if s.get("outcome") is not None and s.get("probability") is not None]
    if not valid:
        return None
    total = sum((s["probability"] - s["outcome"]) ** 2 for s in valid)
    return round(total / len(valid), 4)


def streak(signals: list) -> tuple[int, str | None]:
    """Return (length, 'win'|'loss') of current streak from most-recent resolved signals."""
    resolved = [s for s in signals if s.get("correct") is not None]
    if not resolved:
        return 0, None
    last = resolved[-1]["correct"]
    streak_type = "win" if last else "loss"
    count = 0
    for s in reversed(resolved):
        if s.get("correct") == last:
            count += 1
        else:
            break
    return count, streak_type


def category_stats(resolved: list) -> dict:
    cats: dict = {}
    for s in resolved:
        cat = s.get("category", "unknown")
        if cat not in cats:
            cats[cat] = {"published": 0, "resolved": 0, "correct": 0, "accuracy_pct": None}
        cats[cat]["resolved"] += 1
        if s.get("correct"):
            cats[cat]["correct"] += 1
    for cat, stats in cats.items():
        if stats["resolved"] > 0:
            stats["accuracy_pct"] = round(100 * stats["correct"] / stats["resolved"], 1)
    return cats


def confidence_stats(resolved: list) -> dict:
    tiers: dict = {}
    for s in resolved:
        tier = s.get("confidence", "UNKNOWN")
        if tier not in tiers:
            tiers[tier] = {"published": 0, "resolved": 0, "correct": 0, "accuracy_pct": None}
        tiers[tier]["resolved"] += 1
        if s.get("correct"):
            tiers[tier]["correct"] += 1
    for tier, stats in tiers.items():
        if stats["resolved"] > 0:
            stats["accuracy_pct"] = round(100 * stats["correct"] / stats["resolved"], 1)
    return tiers


def kill_switch_check(resolved: list, accuracy_pct: float | None) -> list:
    active = []
    if accuracy_pct is not None and len(resolved) >= 20 and accuracy_pct < 52:
        active.append("ACCURACY_COLLAPSE")
    # Check 3 consecutive wrong in same category
    by_cat: dict = {}
    for s in resolved:
        cat = s.get("category", "unknown")
        by_cat.setdefault(cat, []).append(s.get("correct", True))
    for cat, results in by_cat.items():
        if len(results) >= 3 and not any(results[-3:]):
            active.append(f"3_CONSECUTIVE_WRONG:{cat}")
    return active


def build_signal_table(all_signals: list, resolved: list) -> list:
    """Build the signal table array for the dashboard, sorted by signal number."""
    resolved_map = {s.get("signal_id"): s for s in resolved}
    table = []
    for s in sorted(all_signals, key=lambda x: x.get("signal_number", 0)):
        sig_id = s.get("id") or s.get("signal_id")
        res = resolved_map.get(sig_id)
        if res and res.get("correct") is True:
            status = "WIN"
        elif res and res.get("correct") is False:
            status = "LOSS"
        else:
            status = "PENDING"
        table.append({
            "signal_number": s.get("signal_number"),
            "title": s.get("question") or s.get("market_question", ""),
            "category": s.get("category", ""),
            "direction": s.get("direction", ""),
            "market_price": s.get("market_price", 0),
            "our_estimate": s.get("our_estimate", 0),
            "gap_pct": s.get("gap_pct", 0),
            "confidence": s.get("confidence", ""),
            "status": status,
            "close_date": s.get("close_date", ""),
            "polymarket_slug": s.get("polymarket_slug", ""),
        })
    return table


def main():
    resolved = load_json(RESOLVED_PATH)
    pending = load_json(PENDING_PATH)
    all_signals = load_json(SIGNALS_PATH)

    total_published = len(all_signals) if all_signals else len(resolved) + len(pending)
    total_resolved = len(resolved)
    correct_count = sum(1 for s in resolved if s.get("correct"))

    accuracy_pct = None
    if total_resolved > 0:
        accuracy_pct = round(100 * correct_count / total_resolved, 1)

    streak_len, streak_type = streak(resolved)
    last_resolved = resolved[-1] if resolved else None

    output = {
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "signals_published": total_published,
        "signals_resolved": total_resolved,
        "correct": correct_count,
        "accuracy_pct": accuracy_pct,
        "brier_score": brier_score(resolved),
        "current_streak": streak_len,
        "streak_type": streak_type,
        "by_category": category_stats(resolved),
        "by_confidence": confidence_stats(resolved),
        "kill_switches_active": kill_switch_check(resolved, accuracy_pct),
        "last_resolved_signal": last_resolved,
        "signals": build_signal_table(all_signals, resolved),
    }

    # Merge into existing accuracy.json to preserve fields from other processes
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    existing = {}
    if OUTPUT_PATH.exists():
        with open(OUTPUT_PATH) as f:
            existing = json.load(f)
    existing.update(output)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(existing, f, indent=2, default=str)

    print(f"accuracy.json updated: {total_published} published, {total_resolved} resolved, accuracy={accuracy_pct}%")


if __name__ == "__main__":
    main()
