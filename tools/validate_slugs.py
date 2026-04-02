"""
validate_slugs.py — Validate and auto-fix Polymarket slugs in signal data.

Fetches the canonical slug from the Gamma Markets API for each signal's market_id,
then updates signals.json, published_signals.json, polymarket_slugs.json, and
dashboard/accuracy.json with the correct slug.

Usage:
    python tools/validate_slugs.py              # Dry run — show what would change
    python tools/validate_slugs.py --fix        # Apply fixes
    python tools/validate_slugs.py --check-urls # Also verify URLs resolve (slower)
"""
import json
import logging
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
SIGNALS_PATH = ROOT / "data" / "signals.json"
PUBLISHED_PATH = ROOT / "data" / "published_signals.json"
SLUGS_PATH = ROOT / "data" / "polymarket_slugs.json"
ACCURACY_PATH = ROOT / "dashboard" / "accuracy.json"

GAMMA_API = "https://gamma-api.polymarket.com/markets"


def fetch_slug(market_id: str) -> str | None:
    """Fetch the canonical slug from the Gamma Markets API for a numeric market_id."""
    if not market_id or not str(market_id).isdigit():
        return None
    url = f"{GAMMA_API}/{market_id}"
    try:
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "ProbBrain/1.0")
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        return data.get("slug", "")
    except Exception as e:
        logger.warning("Failed to fetch slug for market %s: %s", market_id, e)
        return None


def polymarket_url(slug: str) -> str:
    """Build the correct Polymarket URL for a slug."""
    if not slug:
        return ""
    path = "event" if "/" in slug else "market"
    return f"https://polymarket.com/{path}/{slug}"


def check_url(slug: str) -> bool:
    """Check if a Polymarket URL resolves (HTTP 200)."""
    url = polymarket_url(slug)
    if not url:
        return False
    try:
        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.getcode() == 200
    except Exception:
        return False


def validate_and_fix(fix: bool = False, check_urls: bool = False) -> dict:
    """Validate all signal slugs against Gamma API. Returns summary dict."""
    signals = json.loads(SIGNALS_PATH.read_text()) if SIGNALS_PATH.exists() else []
    published = json.loads(PUBLISHED_PATH.read_text()) if PUBLISHED_PATH.exists() else []
    slug_map = json.loads(SLUGS_PATH.read_text()) if SLUGS_PATH.exists() else {}
    accuracy = json.loads(ACCURACY_PATH.read_text()) if ACCURACY_PATH.exists() else {}

    # Build market_id -> correct_slug cache
    all_market_ids = set()
    for s in signals + published + accuracy.get("signals", []):
        mid = str(s.get("market_id", ""))
        if mid and mid.isdigit():
            all_market_ids.add(mid)

    slug_cache = {}
    for mid in sorted(all_market_ids):
        slug = fetch_slug(mid)
        if slug:
            slug_cache[mid] = slug
        time.sleep(0.2)

    wrong = []
    fixed = 0

    def fix_list(entries, source_name):
        nonlocal fixed
        for s in entries:
            mid = str(s.get("market_id", ""))
            if mid not in slug_cache:
                continue
            correct = slug_cache[mid]
            current = s.get("polymarket_slug", "")
            if current != correct:
                wrong.append({
                    "source": source_name,
                    "signal_id": s.get("signal_id", s.get("id", "?")),
                    "market_id": mid,
                    "current": current,
                    "correct": correct,
                })
                if fix:
                    s["polymarket_slug"] = correct
                    fixed += 1

    fix_list(signals, "signals.json")
    fix_list(published, "published_signals.json")
    fix_list(accuracy.get("signals", []), "accuracy.json")

    # Fix slug map
    for num, current_slug in list(slug_map.items()):
        # Find the signal with this number to get market_id
        for s in signals:
            sn = s.get("signal_number")
            if sn is not None and str(sn) == num:
                mid = str(s.get("market_id", ""))
                if mid in slug_cache and current_slug != slug_cache[mid]:
                    wrong.append({
                        "source": "polymarket_slugs.json",
                        "signal_id": f"SIG-{int(num):03d}",
                        "market_id": mid,
                        "current": current_slug,
                        "correct": slug_cache[mid],
                    })
                    if fix:
                        slug_map[num] = slug_cache[mid]
                        fixed += 1
                break

    url_broken = []
    if check_urls:
        for s in accuracy.get("signals", []):
            slug = s.get("polymarket_slug", "")
            if slug and not check_url(slug):
                url_broken.append({
                    "signal_id": s.get("signal_id", "?"),
                    "slug": slug,
                    "url": polymarket_url(slug),
                })
                time.sleep(0.3)

    if fix and wrong:
        SIGNALS_PATH.write_text(json.dumps(signals, indent=2, ensure_ascii=False))
        PUBLISHED_PATH.write_text(json.dumps(published, indent=2, ensure_ascii=False))
        SLUGS_PATH.write_text(json.dumps(slug_map, indent=2))
        ACCURACY_PATH.write_text(json.dumps(accuracy, indent=2, ensure_ascii=False))

    return {
        "total_markets": len(all_market_ids),
        "slugs_fetched": len(slug_cache),
        "wrong_slugs": wrong,
        "fixed": fixed,
        "url_broken": url_broken,
    }


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    do_fix = "--fix" in sys.argv
    do_check = "--check-urls" in sys.argv

    result = validate_and_fix(fix=do_fix, check_urls=do_check)

    print(f"\nMarkets checked: {result['total_markets']}")
    print(f"Slugs fetched: {result['slugs_fetched']}")
    print(f"Wrong slugs: {len(result['wrong_slugs'])}")

    if result["wrong_slugs"]:
        for w in result["wrong_slugs"]:
            print(f"  {w['signal_id']} ({w['source']}): '{w['current']}' -> '{w['correct']}'")

    if result["url_broken"]:
        print(f"\nBroken URLs: {len(result['url_broken'])}")
        for b in result["url_broken"]:
            print(f"  {b['signal_id']}: {b['url']}")

    if do_fix:
        print(f"\nFixed {result['fixed']} entries.")
    elif result["wrong_slugs"]:
        print("\nRun with --fix to apply corrections.")


if __name__ == "__main__":
    main()
