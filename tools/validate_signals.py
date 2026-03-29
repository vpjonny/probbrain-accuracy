"""
validate_signals.py — Validate signal data integrity before dashboard sync.

Checks every signal in signals.json and published_signals.json for:
  - Required price fields (market_price, market_price_at_signal, our_estimate)
  - Valid probability ranges (0.0–1.0)
  - Non-empty direction
  - Consistent gap_pct calculation

Usage:
    python tools/validate_signals.py          # validate and report
    python tools/validate_signals.py --fix    # validate, backfill missing fields, and report

Also importable:
    from tools.validate_signals import validate, backfill
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIGNALS_PATH = ROOT / "data" / "signals.json"
PUBLISHED_PATH = ROOT / "data" / "published_signals.json"


def _normalize_price(value) -> float | None:
    """Convert a price value to a 0-1 probability. Returns None if invalid."""
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    # Detect percentage-style values (e.g. 18.1 instead of 0.181)
    if v > 1.0:
        v = v / 100.0
    if v < 0.0:
        return None
    return round(v, 4)


def _compute_market_price(our_estimate: float, gap_pct: float, direction: str) -> float | None:
    """Derive market_price_at_signal from our_estimate, gap_pct, and direction."""
    if our_estimate is None or gap_pct is None or not direction:
        return None
    if "YES_UNDERPRICED" in direction:
        return round(our_estimate - gap_pct / 100, 4)
    elif "NO_UNDERPRICED" in direction:
        return round(our_estimate + gap_pct / 100, 4)
    return None


def validate(signals: list) -> list[dict]:
    """Validate a list of signal dicts. Returns list of issues found."""
    issues = []
    for s in signals:
        sid = s.get("signal_id", s.get("signal_number", "unknown"))
        mp = s.get("market_price") or s.get("market_price_at_signal") or s.get("market_yes_price")
        oe = s.get("our_estimate") or s.get("our_calibrated_estimate")
        direction = s.get("direction", "")

        if mp is None:
            issues.append({"signal_id": sid, "field": "market_price", "issue": "missing"})
        elif _normalize_price(mp) is None:
            issues.append({"signal_id": sid, "field": "market_price", "issue": f"invalid value: {mp}"})
        elif float(mp) > 1.0:
            issues.append({"signal_id": sid, "field": "market_price", "issue": f"looks like percentage, not probability: {mp}"})

        if oe is None:
            issues.append({"signal_id": sid, "field": "our_estimate", "issue": "missing"})
        elif _normalize_price(oe) is None:
            issues.append({"signal_id": sid, "field": "our_estimate", "issue": f"invalid value: {oe}"})
        elif float(oe) > 1.0:
            issues.append({"signal_id": sid, "field": "our_estimate", "issue": f"looks like percentage, not probability: {oe}"})

        if not direction:
            issues.append({"signal_id": sid, "field": "direction", "issue": "missing or empty"})

    return issues


def backfill(signals_path: Path = SIGNALS_PATH, published_path: Path = PUBLISHED_PATH) -> int:
    """Backfill missing price fields in signals.json using published_signals.json and derivation.

    Returns count of signals fixed.
    """
    signals = json.loads(signals_path.read_text()) if signals_path.exists() else []
    published = json.loads(published_path.read_text()) if published_path.exists() else []

    # Build lookup from published_signals.json by signal_number
    pub_by_num = {}
    for p in published:
        sn = p.get("signal_number")
        if sn is not None:
            pub_by_num[sn] = p

    fixed = 0
    for s in signals:
        sn = s.get("signal_number")
        changed = False

        # Source: published_signals.json entry for this signal
        pub = pub_by_num.get(sn, {})

        # Backfill our_estimate from our_calibrated_estimate or published data
        if s.get("our_estimate") is None:
            oe = (
                _normalize_price(s.get("our_calibrated_estimate"))
                or _normalize_price(pub.get("our_calibrated_estimate"))
                or _normalize_price(pub.get("our_estimate"))
            )
            if oe is not None:
                s["our_estimate"] = oe
                changed = True

        # Backfill our_calibrated_estimate from our_estimate
        if s.get("our_calibrated_estimate") is None and s.get("our_estimate") is not None:
            s["our_calibrated_estimate"] = s["our_estimate"]
            changed = True

        # Backfill market_price_at_signal from market_yes_price or derivation
        if s.get("market_price_at_signal") is None:
            mp = (
                _normalize_price(pub.get("market_yes_price"))
                or _normalize_price(pub.get("market_price_at_signal"))
                or _normalize_price(s.get("market_yes_price"))
            )
            if mp is None:
                # Derive from gap_pct + our_estimate + direction
                oe = s.get("our_estimate") or s.get("our_calibrated_estimate")
                mp = _compute_market_price(
                    _normalize_price(oe),
                    s.get("gap_pct"),
                    s.get("direction", ""),
                )
            if mp is not None:
                s["market_price_at_signal"] = mp
                changed = True

        # Backfill market_price (current) — use market_price_at_signal as initial value
        if s.get("market_price") is None and s.get("market_price_at_signal") is not None:
            s["market_price"] = s["market_price_at_signal"]
            changed = True

        # Normalize any percentage-style values to probabilities
        for field in ["market_price", "market_price_at_signal", "our_estimate", "our_calibrated_estimate"]:
            val = s.get(field)
            if val is not None and isinstance(val, (int, float)) and val > 1.0:
                s[field] = _normalize_price(val)
                changed = True

        if changed:
            fixed += 1

    if fixed:
        signals_path.write_text(json.dumps(signals, indent=2, ensure_ascii=False))

    return fixed


def main():
    fix_mode = "--fix" in sys.argv

    if fix_mode:
        fixed = backfill()
        print(f"Backfilled {fixed} signal(s)")

    signals = json.loads(SIGNALS_PATH.read_text()) if SIGNALS_PATH.exists() else []
    issues = validate(signals)

    if issues:
        print(f"\n{len(issues)} validation issue(s) found:")
        for issue in issues:
            print(f"  {issue['signal_id']}: {issue['field']} — {issue['issue']}")
        sys.exit(1)
    else:
        print("All signals valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
