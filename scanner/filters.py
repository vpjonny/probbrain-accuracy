from typing import List
from .models import Market


MIN_VOLUME_USD = 50_000  # $50k minimum volume


def apply_filters(markets: List[Market]) -> List[Market]:
    """
    Keep markets with ≥$50k volume OR top 20% in their category by volume.
    """
    # Pass 1: always keep high-volume markets
    high_volume = {m.id for m in markets if m.volume_usd >= MIN_VOLUME_USD}

    # Pass 2: top 20% per category
    by_category: dict[str, List[Market]] = {}
    for m in markets:
        by_category.setdefault(m.category, []).append(m)

    top20_ids: set[str] = set()
    for cat_markets in by_category.values():
        sorted_markets = sorted(cat_markets, key=lambda m: m.volume_usd, reverse=True)
        cutoff = max(1, int(len(sorted_markets) * 0.20))
        for m in sorted_markets[:cutoff]:
            top20_ids.add(m.id)

    keep = high_volume | top20_ids
    filtered = [m for m in markets if m.id in keep]

    # Sort by volume descending
    filtered.sort(key=lambda m: m.volume_usd, reverse=True)
    return filtered
