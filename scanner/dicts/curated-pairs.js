// scanner/dicts/curated-pairs.js
//
// Hand-validated cross-platform pairs. Each entry asserts: "this Polymarket
// bucket and this Kalshi bucket ask the SAME question, even if the venues'
// canonical keys don't match exactly." This is how Pass 4 bridges the
// Poly↔Kalshi calendar mismatch that Pass 5 (strict canonical-key) misses.
//
// Adding a pair is a deliberate human decision. Read both venues' market
// pages, confirm the resolution rules describe the same observable event,
// then write the entry. No fuzzy matching is allowed beyond what the entry
// explicitly opts into via `match.strikeTolerancePct`.
//
// Schema:
//   id:                   stable string used in opportunity IDs and dedupe
//   underlying:           UNDERLYINGS key (BTC/ETH/...) — sanity check only
//   polyFilter(event,m):  predicate over (event, market) — return true if
//                         this Poly market belongs to the bucket
//   kalshiFilter(market): predicate over kalshi market
//   match:
//     strikeTolerancePct:    relative tolerance for strike equality (0.5 = 0.5%).
//                            Required because Kalshi uses $X,XXX.99 strikes
//                            while Poly uses round numbers.
//     requireSameDirection:  if true, only above↔above and below↔below match.
//                            Almost always true. Set false ONLY for buckets
//                            where Poly and Kalshi mirror direction (e.g.
//                            Poly "stays under $X" ↔ Kalshi "below $X").
//   sameResolutionWindow: if true, allow non-strict resolution_date matches
//                         to be Tier 1 — you've manually verified that the
//                         settlement windows resolve to the same observable.
//                         If false, non-strict matches still get capped at
//                         Tier 2 with resolution_mismatch (same as Pass 5).
//   notes:                free-form justification, kept for future-you.
//
// Seed entries below are conservative. Re-validate periodically — venue
// product lines drift and a curated pair can stop being valid silently.

export const CURATED_PAIRS = [
  {
    id: 'btc-year-end-2026',
    underlying: 'BTC',

    polyFilter: (event, market) => {
      const slug = String(event.slug || '').toLowerCase();
      const q = String(market.question || '').toLowerCase();
      const groupTitle = String(market.groupItemTitle || '').toLowerCase();
      const blob = `${slug} ${q} ${groupTitle}`;
      const isYearEnd2026 =
        /december[\s,-]*31[\s,-]*2026/.test(blob) ||
        /by-?the-?end-?of-?2026/.test(blob) ||
        /by-end-of-2026/.test(blob);
      const isAboveStrike = /(reach|hit|above)\s*\$?[\d,]+(?:k|m|bn)?/i.test(q) ||
                            /\$[\d,]+/.test(q);
      const isBitcoin = /\bbitcoin\b|\bbtc\b/i.test(blob);
      return isBitcoin && isYearEnd2026 && isAboveStrike;
    },

    kalshiFilter: (market) => {
      const series = String(market._series_ticker_hint || market.series_ticker || '').toUpperCase();
      const ticker = String(market.ticker || '').toUpperCase();
      // KXBTCMAXY = Kalshi's BTC year-end ladder. Restrict to 26DEC31 markets
      // so a 2027 ladder published later doesn't collide.
      if (series !== 'KXBTCMAXY') return false;
      return ticker.includes('26DEC31');
    },

    match: {
      strikeTolerancePct: 0.5,        // $150k vs $149,999.99 → ~0.0007% diff
      requireSameDirection: true,
    },

    sameResolutionWindow: true,
    notes:
      'Both venues resolve on BTC close on Dec 31 2026. Poly endDate sits at Jan 1 2027 ' +
      '(midnight ET on Dec 31). Kalshi expiration is Jan 31 2027 (settlement window) but ' +
      'the observable is identical — Dec 31 2026 daily close. Verified 2026-04-30.',
  },
];

// Apply a curated pair's match logic to a normalized (poly, kalshi) item pair.
// Returns { matches: bool, reason?: string } so the caller can log skips.
export function pairsMatch(curatedPair, polyCanonical, kalshiCanonical) {
  if (curatedPair.match.requireSameDirection &&
      polyCanonical.direction !== kalshiCanonical.direction) {
    return { matches: false, reason: 'direction_differs' };
  }
  const ps = polyCanonical.strike;
  const ks = kalshiCanonical.strike;
  if (!Number.isFinite(ps) || !Number.isFinite(ks)) {
    return { matches: false, reason: 'strike_not_finite' };
  }
  const tolPct = curatedPair.match.strikeTolerancePct ?? 0;
  // Use the larger strike as denominator so $150,000 vs $149,999.99 evaluates
  // symmetrically.
  const denom = Math.max(Math.abs(ps), Math.abs(ks), 1);
  const diffPct = Math.abs(ps - ks) / denom * 100;
  if (diffPct > tolPct) {
    return { matches: false, reason: `strike_diff_${diffPct.toFixed(3)}pct_exceeds_${tolPct}pct` };
  }
  return { matches: true };
}
