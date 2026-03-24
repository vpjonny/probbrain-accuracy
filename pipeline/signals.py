"""
Signal detection: identify notable prediction market opportunities from scanner output.
A signal is any market that passes a notability threshold.
"""
from typing import List

from scanner.models import Market


# Signals fire when a market sits in these probability ranges (interesting uncertainty)
INTERESTING_RANGES = [
    (0.20, 0.35),  # Underdog approaching 1-in-4
    (0.65, 0.80),  # Strong favourite but not certain
]

# Minimum volume for a market to be signal-worthy
SIGNAL_MIN_VOLUME = 100_000  # $100k


def is_notable(market: Market) -> bool:
    """Return True if the market is signal-worthy."""
    if market.volume_usd < SIGNAL_MIN_VOLUME:
        return False
    p = market.yes_price
    return any(lo <= p <= hi for lo, hi in INTERESTING_RANGES)


def detect_signals(markets: List[Market]) -> List[Market]:
    """
    Filter markets down to notable signals.
    Returns them sorted by volume descending.
    """
    signals = [m for m in markets if is_notable(m)]
    signals.sort(key=lambda m: m.volume_usd, reverse=True)
    return signals
