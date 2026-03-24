"""
Recompute dashboard/accuracy.json from data/published_signals.json + data/resolved.json.

Run after every signal publication:
    python tools/compute_accuracy.py

The pipeline calls this automatically if --update-accuracy flag is set.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLISHED_PATH = ROOT / "data" / "published_signals.json"
RESOLVED_PATH = ROOT / "data" / "resolved.json"
OUTPUT_PATH = ROOT / "dashboard" / "accuracy.json"


def _load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text())
    return default


def compute() -> dict:
    published: list = _load_json(PUBLISHED_PATH, [])
    resolved_outcomes: list = _load_json(RESOLVED_PATH, [])

    # Build a lookup of resolved outcomes keyed by market_id
    # resolved.json entries should have: market_id, outcome (YES/NO), resolved_at
    outcome_by_market = {r["market_id"]: r for r in resolved_outcomes if "market_id" in r}

    signals_published = len(published)
    signals_resolved = 0
    correct = 0
    brier_sum = 0.0
    streak = 0
    streak_type = None
    by_category: dict[str, dict] = {}
    by_confidence: dict[str, dict] = {}
    last_resolved = None

    resolved_signals = []  # ordered list for streak calculation

    for sig in published:
        market_id = str(sig.get("market_id", ""))
        category = sig.get("category", "general")
        confidence = sig.get("confidence", "UNKNOWN")
        direction = sig.get("direction", "")
        our_estimate = sig.get("our_calibrated_estimate", None)

        # Init category bucket
        if category not in by_category:
            by_category[category] = {"published": 0, "resolved": 0, "correct": 0, "accuracy_pct": None}
        by_category[category]["published"] += 1

        # Init confidence bucket
        if confidence not in by_confidence:
            by_confidence[confidence] = {"published": 0, "resolved": 0, "correct": 0, "accuracy_pct": None}
        by_confidence[confidence]["published"] += 1

        outcome_data = outcome_by_market.get(market_id)
        if not outcome_data:
            continue  # not yet resolved

        # Resolved
        signals_resolved += 1
        by_category[category]["resolved"] += 1
        by_confidence[confidence]["resolved"] += 1

        market_outcome = outcome_data.get("outcome", "").upper()  # "YES" or "NO"
        resolved_at = outcome_data.get("resolved_at")

        # Determine if our call was correct
        # direction is e.g. "NO_UNDERPRICED" → we are betting NO → correct if outcome == NO
        # direction is e.g. "YES_UNDERPRICED" → we are betting YES → correct if outcome == YES
        if "NO_UNDERPRICED" in direction:
            call_correct = (market_outcome == "NO")
        elif "YES_UNDERPRICED" in direction:
            call_correct = (market_outcome == "YES")
        else:
            call_correct = False  # unknown direction

        if call_correct:
            correct += 1
            by_category[category]["correct"] += 1
            by_confidence[confidence]["correct"] += 1

        # Brier score: (forecast - outcome)^2 where outcome is 1=YES, 0=NO
        if our_estimate is not None:
            actual = 1.0 if market_outcome == "YES" else 0.0
            brier_sum += (our_estimate - actual) ** 2

        resolved_signals.append({
            "resolved_at": resolved_at,
            "correct": call_correct,
        })

        if resolved_at and (last_resolved is None or resolved_at > last_resolved):
            last_resolved = resolved_at

    # Sort resolved signals by resolved_at for streak calculation
    resolved_signals.sort(key=lambda x: x.get("resolved_at") or "")
    for entry in reversed(resolved_signals):
        if streak == 0:
            streak = 1
            streak_type = "win" if entry["correct"] else "loss"
        elif (streak_type == "win") == entry["correct"]:
            streak += 1
        else:
            break

    # Accuracy pct overall
    accuracy_pct = (correct / signals_resolved * 100) if signals_resolved > 0 else None

    # Brier score
    brier_score = (brier_sum / signals_resolved) if signals_resolved > 0 else None

    # Per-category accuracy
    for cat_data in by_category.values():
        if cat_data["resolved"] > 0:
            cat_data["accuracy_pct"] = round(cat_data["correct"] / cat_data["resolved"] * 100, 1)

    # Per-confidence accuracy
    for conf_data in by_confidence.values():
        if conf_data["resolved"] > 0:
            conf_data["accuracy_pct"] = round(conf_data["correct"] / conf_data["resolved"] * 100, 1)

    return {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "signals_published": signals_published,
        "signals_resolved": signals_resolved,
        "correct": correct,
        "accuracy_pct": round(accuracy_pct, 1) if accuracy_pct is not None else None,
        "brier_score": round(brier_score, 4) if brier_score is not None else None,
        "current_streak": streak,
        "streak_type": streak_type,
        "by_category": by_category,
        "by_confidence": by_confidence,
        "kill_switches_active": [],
        "last_resolved_signal": last_resolved,
    }


def main():
    result = compute()
    OUTPUT_PATH.write_text(json.dumps(result, indent=2))
    print(f"accuracy.json updated — {result['signals_published']} published, "
          f"{result['signals_resolved']} resolved, "
          f"accuracy: {result['accuracy_pct']}%")
    return result


if __name__ == "__main__":
    main()
    sys.exit(0)
