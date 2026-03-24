#!/usr/bin/env python3
"""
End-to-end signal pipeline test using a synthetic market.
Verifies: signal detection → formatting → Dub link appended → disclaimer included.
No credentials required — run at any time.

Usage: python test_e2e_signal.py
"""
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from scanner.models import Market
from pipeline.signals import is_notable, detect_signals
from bot.templates import format_signal, format_signal_list, DISCLAIMER

DUB_LINK = "https://dub.sh/pb-tg"


def make_market(
    question: str,
    yes_price: float,
    volume_usd: float,
    category: str = "politics",
) -> Market:
    return Market(
        id="test-001",
        slug="test-market",
        question=question,
        category=category,
        yes_price=yes_price,
        no_price=round(1.0 - yes_price, 4),
        volume_usd=volume_usd,
        liquidity_usd=volume_usd * 0.1,
        close_date=datetime(2026, 6, 30, tzinfo=timezone.utc),
        image_url=None,
        url="https://polymarket.com/event/test-market",
    )


def run_tests() -> None:
    passed = 0
    failed = 0

    def ok(label: str) -> None:
        nonlocal passed
        print(f"  PASS  {label}")
        passed += 1

    def fail(label: str, detail: str = "") -> None:
        nonlocal failed
        print(f"  FAIL  {label}" + (f": {detail}" if detail else ""))
        failed += 1

    # ── 1. Signal detection ───────────────────────────────────────────────────
    print("\n[1] Signal detection")

    notable = make_market("Will X happen?", yes_price=0.25, volume_usd=200_000)
    if is_notable(notable):
        ok("market at 25% / $200k is notable")
    else:
        fail("market at 25% / $200k is notable")

    boring_low_vol = make_market("Low volume?", yes_price=0.25, volume_usd=50_000)
    if not is_notable(boring_low_vol):
        ok("market at $50k volume is NOT notable (below threshold)")
    else:
        fail("market at $50k volume is NOT notable (below threshold)")

    boring_50pct = make_market("Coin flip?", yes_price=0.50, volume_usd=500_000)
    if not is_notable(boring_50pct):
        ok("market at 50% is NOT notable (outside interesting range)")
    else:
        fail("market at 50% is NOT notable (outside interesting range)")

    signals = detect_signals([notable, boring_low_vol, boring_50pct])
    if len(signals) == 1 and signals[0].question == "Will X happen?":
        ok(f"detect_signals returns exactly 1 signal")
    else:
        fail("detect_signals returns exactly 1 signal", f"got {len(signals)}")

    # ── 2. Free-tier format_signal ────────────────────────────────────────────
    print("\n[2] Free-tier format_signal")

    free_msg = format_signal(
        question=notable.question,
        yes_pct=notable.implied_probability,
        volume_usd=notable.volume_usd,
        close_date=notable.close_date,
        category=notable.category,
        market_url=notable.url,
        dub_link=DUB_LINK,
        is_pro=False,
    )

    if f"[Trade on Polymarket]({DUB_LINK})" in free_msg:
        ok("Dub affiliate link present")
    else:
        fail("Dub affiliate link present", f"not found in:\n{free_msg}")

    if DISCLAIMER in free_msg:
        ok("Disclaimer present")
    else:
        fail("Disclaimer present")

    if "polymarket.com/event/test-market" not in free_msg:
        ok("Free tier does NOT expose direct market URL")
    else:
        fail("Free tier does NOT expose direct market URL")

    if "25\\.0%" in free_msg:
        ok("Probability formatted correctly (25.0%)")
    else:
        fail("Probability formatted correctly", f"missing in:\n{free_msg}")

    # ── 3. Pro-tier format_signal ─────────────────────────────────────────────
    print("\n[3] Pro-tier format_signal")

    pro_msg = format_signal(
        question=notable.question,
        yes_pct=notable.implied_probability,
        volume_usd=notable.volume_usd,
        close_date=notable.close_date,
        category=notable.category,
        market_url=notable.url,
        dub_link=DUB_LINK,
        is_pro=True,
    )

    if "polymarket.com/event/test-market" in pro_msg:
        ok("Pro tier includes direct market URL")
    else:
        fail("Pro tier includes direct market URL", f"not in:\n{pro_msg}")

    if "$200,000" in pro_msg:
        ok("Volume formatted correctly ($200,000)")
    else:
        fail("Volume formatted correctly", f"missing in:\n{pro_msg}")

    if "Jun 30, 2026" in pro_msg:
        ok("Close date formatted correctly (Jun 30, 2026)")
    else:
        fail("Close date formatted correctly", f"missing in:\n{pro_msg}")

    if f"[Trade on Polymarket]({DUB_LINK})" in pro_msg and DISCLAIMER in pro_msg:
        ok("Dub link and disclaimer present in Pro tier too")
    else:
        fail("Dub link and disclaimer present in Pro tier too")

    # ── 4. format_signal_list ─────────────────────────────────────────────────
    print("\n[4] format_signal_list (free tier)")

    list_msg = format_signal_list([notable.to_dict()], dub_link=DUB_LINK, is_pro=False)

    if f"[Trade on Polymarket]({DUB_LINK})" in list_msg:
        ok("Dub link in signal list")
    else:
        fail("Dub link in signal list")

    if DISCLAIMER in list_msg:
        ok("Disclaimer in signal list")
    else:
        fail("Disclaimer in signal list")

    # ── 5. Data flow summary ──────────────────────────────────────────────────
    print("\n[5] Data flow")
    print("    Polymarket Gamma API")
    print("    → scanner.polymarket.fetch_markets()  [paginated, ~36k markets]")
    print("    → scanner.filters.apply_filters()     [volume >= $50k OR top-20% per category]")
    print("    → scanner.polymarket.save_snapshot()  [timestamped JSON in data/]")
    print("    → pipeline.signals.detect_signals()   [20-35% or 65-80% range, vol >= $100k]")
    print("    → bot.templates.format_signal()       [MarkdownV2, free/pro tiers]")
    print("    → pipeline.publisher.publish_signals() [sendMessage via Bot API]")
    print("    → Telegram channel / bot users")

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*50}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        print("\nSample free-tier message output:")
        print("---")
        print(free_msg)
        sys.exit(1)
    else:
        print("\nSample free-tier message output:")
        print("---")
        print(free_msg)
        print("---")
        print("\nSample pro-tier message output:")
        print("---")
        print(pro_msg)


if __name__ == "__main__":
    run_tests()
