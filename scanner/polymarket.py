"""
Polymarket market scanner using the Gamma Markets API.
Docs: https://gamma-api.polymarket.com/docs
"""
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import httpx

from .filters import apply_filters, filter_duplicates
from .models import Market

logger = logging.getLogger(__name__)

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
POLYMARKET_BASE = "https://polymarket.com/event"

# Builder attribution key — attributes scanned traffic to ProbBrain for weekly USDC rewards.
# Header name per Polymarket CLOB API builder attribution spec.
BUILDERS_API_KEY = os.getenv("POLYMARKET_BUILDERS_API_KEY", "")

# Categories Polymarket uses in their tag system
DEFAULT_CATEGORIES = [
    "politics", "sports", "crypto", "economics", "pop culture",
    "science", "weather", "world", "entertainment", "technology",
]


def _parse_price(raw: str | float | None, fallback: float = 0.5) -> float:
    if raw is None:
        return fallback
    try:
        val = float(raw)
        return max(0.0, min(1.0, val))
    except (ValueError, TypeError):
        return fallback


def _parse_date(raw: str | None) -> Optional[datetime]:
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _extract_category(market_data: dict) -> str:
    tags = market_data.get("tags") or []
    if isinstance(tags, list) and tags:
        first = tags[0]
        if isinstance(first, dict):
            return first.get("label", "general").lower()
        return str(first).lower()
    # Fall back to groupItemTitle or a generic bucket
    group = market_data.get("groupItemTitle") or market_data.get("category") or "general"
    return str(group).lower()


def _market_url(market_data: dict) -> str:
    slug = market_data.get("slug") or market_data.get("id", "")
    return f"{POLYMARKET_BASE}/{slug}"


def _parse_market(raw: dict) -> Optional[Market]:
    """Convert a raw Gamma API market dict into a Market object."""
    try:
        market_id = str(raw.get("id", ""))
        if not market_id:
            return None

        # YES price comes from outcomePrices[0] or bestBid/bestAsk
        outcome_prices = raw.get("outcomePrices") or []
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except (json.JSONDecodeError, TypeError):
                outcome_prices = []

        yes_price = _parse_price(outcome_prices[0] if outcome_prices else None)
        no_price = _parse_price(outcome_prices[1] if len(outcome_prices) > 1 else None, 1.0 - yes_price)

        volume = float(raw.get("volume", 0) or raw.get("volumeNum", 0) or 0)
        liquidity = float(raw.get("liquidity", 0) or raw.get("liquidityNum", 0) or 0)

        return Market(
            id=market_id,
            slug=raw.get("slug", market_id),
            question=raw.get("question", ""),
            category=_extract_category(raw),
            yes_price=yes_price,
            no_price=no_price,
            volume_usd=volume,
            liquidity_usd=liquidity,
            close_date=_parse_date(raw.get("endDate") or raw.get("endDateIso")),
            image_url=raw.get("image"),
            url=_market_url(raw),
        )
    except Exception as exc:
        logger.warning("Failed to parse market %s: %s", raw.get("id"), exc)
        return None


def fetch_markets(limit: int = 500, filtered: bool = True) -> List[Market]:
    """
    Fetch open Polymarket markets via the Gamma API.

    Args:
        limit:    Max markets per request page (API max ~500)
        filtered: Apply volume/top-20% filters before returning

    Returns:
        List of Market objects, sorted by volume descending.
    """
    markets: List[Market] = []
    offset = 0

    headers = {}
    if BUILDERS_API_KEY:
        headers["POLY_BUILDER_API_KEY"] = BUILDERS_API_KEY

    with httpx.Client(timeout=30, headers=headers) as client:
        while True:
            params = {
                "active": "true",
                "closed": "false",
                "limit": limit,
                "offset": offset,
                "order": "volume",
                "ascending": "false",
            }
            try:
                resp = client.get(f"{GAMMA_API_BASE}/markets", params=params)
                resp.raise_for_status()
                page = resp.json()
            except httpx.HTTPError as exc:
                logger.error("Gamma API request failed (offset=%d): %s", offset, exc)
                break

            if not page:
                break

            for raw in page:
                market = _parse_market(raw)
                if market:
                    markets.append(market)

            logger.info("Fetched %d markets (offset=%d)", len(page), offset)

            if len(page) < limit:
                break
            offset += limit

    logger.info("Total markets fetched: %d", len(markets))

    if filtered:
        markets = apply_filters(markets)
        logger.info("Markets after liquidity filtering: %d", len(markets))

        markets = filter_duplicates(markets)
        logger.info("Markets after dedup filtering: %d", len(markets))

    return markets


def save_snapshot(markets: List[Market], output_dir: str = "data/scans") -> Path:
    """Save markets to a daily JSON snapshot file (data/scans/YYYY-MM-DD.json)."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    path = out / f"{date_str}.json"

    payload = {
        "fetched_at": datetime.utcnow().isoformat() + "Z",
        "count": len(markets),
        "markets": [m.to_dict() for m in markets],
    }
    path.write_text(json.dumps(payload, indent=2))
    logger.info("Saved snapshot: %s (%d markets)", path, len(markets))
    return path


def load_latest_snapshot(output_dir: str = "data/scans") -> Optional[dict]:
    """Load the most recent daily JSON snapshot, or None if none exist."""
    snapshots = sorted(Path(output_dir).glob("????-??-??.json"))
    if not snapshots:
        return None
    return json.loads(snapshots[-1].read_text())
