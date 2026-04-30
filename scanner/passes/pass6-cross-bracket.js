// scanner/passes/pass6-cross-bracket.js
//
// Bracket arbitrage across venues with mismatched strike granularities.
//
// Math: for two threshold markets on the same underlying / direction / same
// resolution observable, the "above" probability is non-increasing in strike
// and the "below" probability is non-decreasing in strike. So given two
// markets m1, m2 with same direction, define
//
//   looseness = direction === 'above' ? -strike : strike
//
// Then expected: m1.looseness < m2.looseness ⇒ P(m1) ≤ P(m2). When the
// reality is m1.looseness < m2.looseness AND P(m1) > P(m2), that's an arb:
// the looser side is mispriced LOW relative to the stricter side. Build the
// position by buying YES on the cheaper side (the truly-loose one) and NO
// on the more expensive side (the truly-strict one). Min payout is $1 in
// every settlement scenario; cost is `P_cheap_YES + (1 - P_expensive_YES)
// = 1 - (P_expensive - P_cheap)`. Profit = P_expensive - P_cheap.
//
// What this pass adds over Pass 4: Pass 4 matches strikes within a small
// tolerance (penny-equivalent strikes asking the same question). Pass 6
// matches DIFFERENT strikes (Poly's $150k bucket vs Kalshi's $130k bucket)
// and finds violations of the cross-venue monotonicity expected from a
// shared resolution observable.
//
// Honesty constraint: this is risk-free ONLY when the curated pair has
// `sameResolutionWindow: true` — that's the operator's assertion that both
// venues resolve to the same observable. With sameResolutionWindow=false,
// non-strict-date matches still cap at Tier 2 with `resolution_mismatch`.

import { normalizePolymarket } from '../normalize/polymarket.js';
import { normalizeKalshi } from '../normalize/kalshi.js';
import { CURATED_PAIRS } from '../dicts/curated-pairs.js';
import {
  estimateFeesPct, assignTier, offsetTolerance,
} from '../lib/tiering.js';

const SPREAD_THRESHOLD = 0.02; // 2pp gap minimum, same as other passes

// ── price + leg helpers (parallel to Pass 4/5) ──────────────────────────────
function parsePolyPrices(raw) {
  if (Array.isArray(raw)) return raw.map(Number);
  if (typeof raw === 'string') {
    try { return JSON.parse(raw).map(Number); } catch { return null; }
  }
  return null;
}
function polyDepthEstimate(market) {
  const liq = Number(market.liquidityNum ?? market.liquidity ?? 0);
  return Number.isFinite(liq) && liq > 0 ? Math.round(liq * 0.25) : 0;
}
function polyLastTradeAt(market) {
  if (market.lastTradeTime) return market.lastTradeTime;
  const v24 = Number(market.volume24hr || 0);
  return v24 > 0 && market.updatedAt ? market.updatedAt : null;
}
function polyMarketUrl(event, market) {
  if (!event.slug) return null;
  return market.slug && market.slug !== event.slug
    ? `https://polymarket.com/event/${event.slug}/${market.slug}`
    : `https://polymarket.com/event/${event.slug}`;
}
function parseDollars(s) {
  if (s == null) return null;
  const n = parseFloat(s);
  return Number.isFinite(n) ? n : null;
}
function kalshiMidYes(market) {
  const bid = parseDollars(market.yes_bid_dollars);
  const ask = parseDollars(market.yes_ask_dollars);
  if (bid != null && ask != null && ask > 0 && bid >= 0 && ask >= bid) return (bid + ask) / 2;
  if (ask != null && ask > 0 && ask < 1) return ask;
  if (bid != null && bid > 0 && bid < 1) return bid;
  const last = parseDollars(market.last_price_dollars);
  if (last != null && last > 0 && last < 1) return last;
  return null;
}
function kalshiDepthEstimate(market) {
  const liq = parseDollars(market.liquidity_dollars);
  if (liq && liq > 0) return Math.round(liq * 0.25);
  const bidSize = Number(market.yes_bid_size_fp || 0);
  const askSize = Number(market.yes_ask_size_fp || 0);
  const ask = parseDollars(market.yes_ask_dollars) || 0.5;
  return Math.round((bidSize + askSize) * ask);
}
function kalshiLastTradeAt(market) {
  const v24 = Number(market.volume_24h_fp || 0);
  return v24 > 0 && market.updated_time ? market.updated_time : null;
}
function kalshiMarketUrl(market) {
  if (!market.ticker) return null;
  return `https://kalshi.com/markets/${market.event_ticker || ''}/${market.ticker}`;
}

function polyLeg({ event, market, side, yesPrice }) {
  const v24 = Number(market.volume24hr || 0);
  return {
    platform: 'polymarket',
    market_id: String(market.id),
    market_url: polyMarketUrl(event, market),
    side,
    price: side === 'YES' ? +yesPrice.toFixed(4) : +(1 - yesPrice).toFixed(4),
    depth_usd_at_price: polyDepthEstimate(market),
    last_trade_at: polyLastTradeAt(market),
    volume_24h_usd: Number.isFinite(v24) ? Math.round(v24) : 0,
  };
}
function kalshiLeg({ market, side, yesPrice }) {
  const v24 = Number(market.volume_24h_fp || 0);
  return {
    platform: 'kalshi',
    market_id: market.ticker,
    market_url: kalshiMarketUrl(market),
    side,
    price: side === 'YES' ? +yesPrice.toFixed(4) : +(1 - yesPrice).toFixed(4),
    depth_usd_at_price: kalshiDepthEstimate(market),
    last_trade_at: kalshiLastTradeAt(market),
    volume_24h_usd: Number.isFinite(v24) ? Math.round(v24) : 0,
  };
}

function fmtStrike(s, underlying) {
  if (['BTC', 'ETH', 'SOL'].includes(underlying)) return `$${Math.round(s).toLocaleString()}`;
  if (['CPI', 'FED_RATE'].includes(underlying)) {
    const pct = s < 1 ? s * 100 : s;
    return `${pct.toFixed(2)}%`;
  }
  if (underlying === 'NFP') return Math.round(s).toLocaleString();
  return String(s);
}

// looseness in [-strike, +∞) — higher means "easier to be true" → expected to
// have higher probability. For 'above', looser = lower strike. For 'below',
// looser = higher strike.
function looseness(direction, strike) {
  return direction === 'above' ? -strike : +strike;
}

// Given two same-direction markets, return the one that's looser (expected
// to have higher P) and the one that's stricter.
function looseStrict(p, k) {
  const lp = looseness(p.canonical.direction, p.canonical.strike);
  const lk = looseness(k.canonical.direction, k.canonical.strike);
  if (lp === lk) return null; // identical strike — Pass 4 territory
  if (lp > lk) return { loose: p, strict: k };
  return { loose: k, strict: p };
}

function summarize({ pair, loose, strict, looseSide, strictSide }) {
  const u = loose.canonical.underlying;
  const d = loose.canonical.direction;
  const sLoose = fmtStrike(loose.canonical.strike, u);
  const sStrict = fmtStrike(strict.canonical.strike, u);
  const ploose = loose.platform || (loose.market.event_ticker ? 'kalshi' : 'polymarket');
  const pstrict = strict.platform || (strict.market.event_ticker ? 'kalshi' : 'polymarket');
  return `[bracket:${pair.id}] ${u} ${d}-${sLoose} (${ploose} YES ${loose.yes.toFixed(3)}) vs ${d}-${sStrict} (${pstrict} YES ${strict.yes.toFixed(3)}) — strict-side priced ${(strict.yes - loose.yes >= 0 ? 'higher' : 'lower')} than looser by ${(Math.abs(strict.yes - loose.yes) * 100).toFixed(1)}pp (monotonicity violation)`;
}

function stableId({ pair, loose, strict }) {
  const u = loose.canonical.underlying;
  const d = loose.canonical.direction;
  return `pass6-bracket-${pair.id}-${u}-${d}-loose${loose.canonical.strike}-strict${strict.canonical.strike}-poly${loose.platform === 'polymarket' ? loose.market.id : strict.market.id}-kalshi${loose.platform === 'kalshi' ? loose.market.ticker : strict.market.ticker}`;
}

function weakestLink({ pair, minDepth, netEdgePct, grossEdgePct, offsetMin, resolutionType, daysToResolution, strikeGapPct }) {
  if (netEdgePct <= 0) {
    return `Net edge negative after fees — bracket gap (${grossEdgePct.toFixed(2)}pp gross) shrinks below the fee + capital-cost floor over ${Math.round(daysToResolution)}d horizon.`;
  }
  if (minDepth < 200) {
    return `Thinner-leg depth limits fill to ~$${Math.round(minDepth)} before slippage closes the bracket spread on that venue.`;
  }
  const tol = offsetTolerance(resolutionType);
  if (offsetMin > tol && !pair.sameResolutionWindow) {
    return `Settlement times differ by ${Math.round(offsetMin)}min on a ${resolutionType} market (tolerance ${tol}min) — underlying can move between settlements and break the bracket.`;
  }
  return `Bracket arb: strikes differ by ${strikeGapPct.toFixed(1)}% so payouts diverge in the middle range — guaranteed $1 minimum, $2 maximum payout regardless of settle. Curated pair "${pair.id}" asserts both venues resolve identically.`;
}

// ── main ────────────────────────────────────────────────────────────────────
// Same opts shape as Pass 4: `curatedPairs` overrides the dict for tests.
// Returns { opportunities, coveredPairs, stats } — coveredPairs lets Pass 5
// dedupe.
export async function runPass6(polyEvents, kalshiMarkets, log, opts = {}) {
  const nowMs = Date.now();
  const pairs = Array.isArray(opts.curatedPairs) ? opts.curatedPairs : CURATED_PAIRS;
  const opportunities = [];
  const coveredPairs = new Set();
  let candidatesPreFilter = 0;

  // Pre-normalize once, reused across pairs.
  const polyAll = [];
  for (const event of polyEvents) {
    for (const m of (event.markets || [])) {
      if (m.closed || m.active === false) continue;
      if (m.endDate && Date.parse(m.endDate) <= nowMs) continue;
      const prices = parsePolyPrices(m.outcomePrices);
      if (!prices || prices.length < 1) continue;
      const yes = prices[0];
      if (!Number.isFinite(yes) || yes <= 0 || yes >= 1) continue;
      const norm = normalizePolymarket(m, event);
      if (norm.skip) continue;
      polyAll.push({ event, market: m, yes, canonical: norm, rawDate: m.endDate, platform: 'polymarket' });
    }
  }
  const kalshiAll = [];
  for (const m of kalshiMarkets) {
    if (m.status && m.status !== 'active' && m.status !== 'open') continue;
    const yes = kalshiMidYes(m);
    if (yes == null || yes <= 0 || yes >= 1) continue;
    const norm = normalizeKalshi(m);
    if (norm.skip) continue;
    kalshiAll.push({ market: m, yes, canonical: norm, rawDate: m.expiration_time || m.close_time, platform: 'kalshi' });
  }

  for (const pair of pairs) {
    const polyItems = polyAll.filter(it => {
      if (it.canonical.underlying !== pair.underlying) return false;
      try { return pair.polyFilter(it.event, it.market); }
      catch (e) { log.warn(`pass6: polyFilter error for ${pair.id}: ${e.message}`); return false; }
    });
    const kalshiItems = kalshiAll.filter(it => {
      if (it.canonical.underlying !== pair.underlying) return false;
      try { return pair.kalshiFilter(it.market); }
      catch (e) { log.warn(`pass6: kalshiFilter error for ${pair.id}: ${e.message}`); return false; }
    });

    log.info(`pass6: pair "${pair.id}" — poly_candidates=${polyItems.length} kalshi_candidates=${kalshiItems.length}`);
    if (polyItems.length === 0 || kalshiItems.length === 0) continue;

    const tolPct = pair.match?.strikeTolerancePct ?? 0;

    for (const p of polyItems) {
      for (const k of kalshiItems) {
        // Direction must match — the math only works when both are above/above
        // or both below/below.
        if (p.canonical.direction !== k.canonical.direction) {
          continue;
        }

        // Skip strikes within Pass 4's tolerance (Pass 4 covers those).
        const denom = Math.max(Math.abs(p.canonical.strike), Math.abs(k.canonical.strike), 1);
        const strikeGapPct = Math.abs(p.canonical.strike - k.canonical.strike) / denom * 100;
        if (strikeGapPct <= tolPct) continue;

        // Identify looser vs stricter side.
        const ls = looseStrict(p, k);
        if (!ls) continue;
        const { loose, strict } = ls;

        // Cross-venue monotonicity: looser should have higher (or equal) P
        // than stricter. Violation iff loose.yes < strict.yes.
        if (loose.yes >= strict.yes) continue;

        const arbGap = strict.yes - loose.yes;
        if (arbGap <= SPREAD_THRESHOLD) continue;
        candidatesPreFilter++;

        // Settlement-time offset.
        const polyT = Date.parse(p.rawDate);
        const kalshiT = Date.parse(k.rawDate);
        const offsetMin = (Number.isFinite(polyT) && Number.isFinite(kalshiT))
          ? Math.abs(polyT - kalshiT) / 60_000
          : 0;
        const tol = offsetTolerance(p.canonical.resolution_type);
        if (!pair.sameResolutionWindow && offsetMin > tol * 4) {
          log.skip(`pass6_${pair.id}_offset_too_large`, {
            offset_min: Math.round(offsetMin), tolerance_min: tol,
          });
          continue;
        }

        // Volume sanity — same gates as Pass 4/5. Both legs must have real
        // recent activity on their respective venues.
        const polyV24 = Number(p.market.volume24hr || 0);
        const kalshiV24 = Number(k.market.volume_24h_fp || 0);
        if (polyV24 === 0 || kalshiV24 === 0) {
          log.skip(`pass6_${pair.id}_dead_leg`, {
            poly_v24: polyV24, kalshi_v24: kalshiV24,
          });
          continue;
        }
        if (polyV24 < 100 && kalshiV24 < 100) {
          log.skip(`pass6_${pair.id}_low_volume`, {
            poly_v24: polyV24, kalshi_v24: kalshiV24,
          });
          continue;
        }

        // Build legs: looser-side YES (cheap), stricter-side NO (cheap).
        const buildLooseLeg = loose.platform === 'polymarket'
          ? polyLeg({ event: loose.event, market: loose.market, side: 'YES', yesPrice: loose.yes })
          : kalshiLeg({ market: loose.market, side: 'YES', yesPrice: loose.yes });
        const buildStrictLeg = strict.platform === 'polymarket'
          ? polyLeg({ event: strict.event, market: strict.market, side: 'NO', yesPrice: strict.yes })
          : kalshiLeg({ market: strict.market, side: 'NO', yesPrice: strict.yes });
        const legs = [buildLooseLeg, buildStrictLeg];

        const grossEdgePct = +(arbGap * 100).toFixed(2);
        const minDepth = Math.min(...legs.map(l => l.depth_usd_at_price || 0));
        const endMs = Math.max(polyT || 0, kalshiT || 0);
        const daysToResolution = endMs > 0
          ? Math.max(0, (endMs - nowMs) / (24 * 3.6e6))
          : 30;
        const feesPct = estimateFeesPct({ legs, daysToResolution });
        const netEdgePct = +(grossEdgePct - feesPct).toFixed(2);
        const edgeNetPerDollar = +(netEdgePct / 100).toFixed(4);

        const depthSeverelyCapped = minDepth > 0 && minDepth < 200;
        const hasOffsetWarning = !pair.sameResolutionWindow && offsetMin > tol;

        let { tier, flags } = assignTier({
          grossEdgePct,
          legs,
          resolutionType: p.canonical.resolution_type,
          hasOffsetWarning,
          depthSeverelyCapped,
          netEdgePct,
        });

        if (legs.some(l => !l.last_trade_at)) {
          tier = Math.max(tier, 3);
          if (!flags.includes('stale_price')) flags.push('stale_price');
        }
        if (legs.some(l => (l.volume_24h_usd ?? 0) === 0)) {
          tier = Math.max(tier, 3);
          if (!flags.includes('low_volume')) flags.push('low_volume');
        } else if (legs.some(l => (l.volume_24h_usd ?? 0) < 1000)) {
          if (!flags.includes('low_volume')) flags.push('low_volume');
        }
        if (depthSeverelyCapped && !flags.includes('depth_limited')) flags.push('depth_limited');
        if (netEdgePct <= 0) tier = Math.max(tier, 2);

        if (!flags.includes('curated_pair')) flags.push('curated_pair');
        if (!flags.includes('bracket_arb')) flags.push('bracket_arb');

        if (!pair.sameResolutionWindow) {
          tier = Math.max(tier, 2);
          if (!flags.includes('resolution_mismatch')) flags.push('resolution_mismatch');
        }

        opportunities.push({
          id: stableId({ pair, loose, strict }),
          tier,
          type: 'cross_platform_bracket',
          summary: summarize({
            pair, loose, strict,
            looseSide: 'YES',
            strictSide: 'NO',
          }),
          underlying: p.canonical.underlying,
          resolution_date: p.canonical.resolution_date,
          resolution_type: p.canonical.resolution_type,
          legs,
          edge_gross_pct: grossEdgePct,
          edge_net_estimate_pct: netEdgePct,
          max_executable_size_per_leg_usd: Math.round(minDepth),
          edge_net_per_dollar: edgeNetPerDollar,
          weakest_link_summary: weakestLink({
            pair, minDepth, netEdgePct, grossEdgePct, offsetMin,
            resolutionType: p.canonical.resolution_type, daysToResolution, strikeGapPct,
          }),
          confidence_flags: flags,
          curated_pair_id: pair.id,
        });
        coveredPairs.add(`${p.market.id}|${k.market.ticker}`);
      }
    }
  }

  return {
    opportunities,
    coveredPairs,
    stats: {
      candidates_pre_filter: candidatesPreFilter,
      curated_pairs_evaluated: pairs.length,
      poly_normalized_for_match: polyAll.length,
      kalshi_normalized_for_match: kalshiAll.length,
    },
  };
}
