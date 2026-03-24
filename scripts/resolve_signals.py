#!/usr/bin/env python3
"""
resolve_signals.py — check Polymarket for resolved markets and update our tracking files.

Reads:  data/pending_signals.json
Writes: data/pending_signals.json (removes resolved signals)
        data/resolved.json        (appends resolved signals with outcome + scoring)

Hard rule: never manufacture outcomes. Only mark resolved if Polymarket API confirms.
Disputed resolutions (ambiguous winner): flagged with disputed=true, not scored.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
PENDING_PATH = ROOT / "data" / "pending_signals.json"
RESOLVED_PATH = ROOT / "data" / "resolved.json"

GAMMA_API_BASE = "https://gamma-api.polymarket.com"


def load_json(path: Path) -> list:
    if path.exists():
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    return []


def save_json(path: Path, data: list) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def fetch_market(client: httpx.Client, market_id: str) -> dict | None:
    """Fetch a single market by numeric ID or slug from the Gamma API."""
    if market_id.isdigit():
        try:
            resp = client.get(f"{GAMMA_API_BASE}/markets/{market_id}")
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                return data[0] if data else None
            return data
        except httpx.HTTPError as exc:
            print(f"  API error for market id={market_id}: {exc}", file=sys.stderr)
            return None
    else:
        try:
            resp = client.get(f"{GAMMA_API_BASE}/markets", params={"slug": market_id})
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return data[0]
            return None
        except httpx.HTTPError as exc:
            print(f"  API error for slug={market_id}: {exc}", file=sys.stderr)
            return None


def is_resolved(market: dict) -> bool:
    """Return True only if the market is closed AND has a confirmed winner."""
    return bool(market.get("closed") and market.get("winner"))


def get_outcome(market: dict) -> int | None:
    """
    Return 1 (YES resolved), 0 (NO resolved), or None (ambiguous — do not score).
    """
    winner = str(market.get("winner", "")).strip().lower()
    if winner in ("yes", "1", "true"):
        return 1
    if winner in ("no", "0", "false"):
        return 0
    return None


def is_correct(direction: str, outcome: int) -> bool:
    if direction == "YES_UNDERPRICED":
        return outcome == 1
    if direction == "NO_UNDERPRICED":
        return outcome == 0
    return False


def main() -> None:
    pending = load_json(PENDING_PATH)
    resolved = load_json(RESOLVED_PATH)

    if not pending:
        print("No pending signals to check.")
        return

    still_pending: list = []
    newly_resolved: list = []

    with httpx.Client(timeout=30) as client:
        for signal in pending:
            market_id = str(signal.get("market_id", ""))
            signal_id = signal.get("signal_id", market_id)
            print(f"Checking {signal_id} (market: {market_id}) ...")

            market = fetch_market(client, market_id)
            if market is None:
                print(f"  Could not fetch — keeping as pending.")
                still_pending.append(signal)
                continue

            if not is_resolved(market):
                print(f"  Not yet resolved.")
                still_pending.append(signal)
                continue

            outcome = get_outcome(market)
            if outcome is None:
                winner_raw = market.get("winner", "<none>")
                print(f"  Ambiguous winner '{winner_raw}' — flagging as disputed, not scoring.")
                still_pending.append({**signal, "disputed": True, "dispute_reason": f"ambiguous_winner:{winner_raw}"})
                continue

            direction = signal.get("direction", "")
            our_estimate = float(signal.get("our_estimate", 0.5))
            correct = is_correct(direction, outcome)
            brier = round((our_estimate - outcome) ** 2, 4)

            resolved_at = (
                market.get("resolutionTime")
                or market.get("endDate")
                or datetime.now(timezone.utc).isoformat()
            )

            resolved_entry = {
                "signal_id": signal_id,
                "market_id": market_id,
                "question": signal.get("question", ""),
                "category": signal.get("category", "unknown"),
                "confidence": signal.get("confidence", "UNKNOWN"),
                "direction": direction,
                "probability": our_estimate,
                "outcome": outcome,
                "correct": correct,
                "brier_contribution": brier,
                "resolved_at": resolved_at,
                "published_at": signal.get("published_at"),
                "paperclip_issue": signal.get("paperclip_issue"),
            }
            resolved.append(resolved_entry)
            newly_resolved.append(signal_id)
            print(f"  RESOLVED: outcome={'YES' if outcome == 1 else 'NO'}, correct={correct}, brier={brier}")

    save_json(PENDING_PATH, still_pending)
    save_json(RESOLVED_PATH, resolved)

    if newly_resolved:
        print(f"\nResolved {len(newly_resolved)} signal(s): {', '.join(newly_resolved)}")
        print(f"{len(still_pending)} signal(s) still pending.")
    else:
        print(f"\nNo new resolutions. {len(still_pending)} signal(s) still pending.")


if __name__ == "__main__":
    main()
