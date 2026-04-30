// scanner/passes/pass2-poly-monotonicity.js
//
// Within-Polymarket strike monotonicity. Group all open Polymarket markets by
// (underlying, direction, resolution_date, resolution_type) — i.e. canonical
// key sans strike. Within each group with ≥2 markets, sort by strike
// ascending. Check for inversions:
//
//   "above" markets: price(low_strike) should be ≥ price(high_strike).
//   "below" markets: price(low_strike) should be ≤ price(high_strike).
//
// Each violating pair gets one opportunity. Strategy:
//   above-violation:  buy YES on low_strike (underpriced), NO on high_strike
//                     (overpriced). Risk-free if the higher threshold
//                     resolves YES — the lower must too.
//   below-violation:  symmetric.

import { normalizePolymarket } from '../normalize/polymarket.js';
import { estimateFeesPct, assignTier } from '../lib/tiering.js';

// Pair-level violation threshold. Below this, we treat as noise (rounding,
// tick-size jitter). Real Poly monotonicity violations on illiquid ladders
// are usually 2pp+; tighter than that probably isn't tradeable after fees.
const PAIR_VIOLATION_THRESHOLD = 0.02; // 2pp

function parsePrices(raw) {
  if (Array.isArray(raw)) return raw.map(Number);
  if (typeof raw === 'string') {
    try { return JSON.parse(raw).map(Number); } catch { return null; }
  }
  return null;
}

function depthEstimate(market) {
  const liq = Number(market.liquidityNum ?? market.liquidity ?? 0);
  return Number.isFinite(liq) && liq > 0 ? Math.round(liq * 0.25) : 0;
}

function lastTradeAt(market) {
  if (market.lastTradeTime) return market.lastTradeTime;
  const v24 = Number(market.volume24hr || 0);
  return v24 > 0 && market.updatedAt ? market.updatedAt : null;
}

function legUrl(eventSlug, marketSlug) {
  if (!eventSlug) return null;
  return marketSlug && marketSlug !== eventSlug
    ? `https://polymarket.com/event/${eventSlug}/${marketSlug}`
    : `https://polymarket.com/event/${eventSlug}`;
}

function buildLeg({ event, market, side, yesPrice }) {
  const v24 = Number(market.volume24hr || 0);
  return {
    platform: 'polymarket',
    market_id: String(market.id),
    market_url: legUrl(event.slug, market.slug),
    side,
    price: side === 'YES' ? +yesPrice.toFixed(4) : +(1 - yesPrice).toFixed(4),
    depth_usd_at_price: depthEstimate(market),
    last_trade_at: lastTradeAt(market),
    volume_24h_usd: Number.isFinite(v24) ? Math.round(v24) : 0,
  };
}

function stableId({ canonical, lowMarketId, highMarketId }) {
  // Sort ids so reordering across scans doesn't change the id.
  const [a, b] = [lowMarketId, highMarketId].map(String).sort();
  return `pass2-poly-mono-${canonical.underlying}-${canonical.direction}-${canonical.resolution_date}-${canonical.resolution_type}-${a}-${b}`;
}

function fmtStrike(s, underlying) {
  if (['BTC', 'ETH', 'SOL'].includes(underlying)) return `$${Math.round(s).toLocaleString()}`;
  if (['CPI', 'FED_RATE'].includes(underlying)) {
    // Strikes parsed as "3.00%" become 0.03; strikes parsed as "3.00" (no %)
    // become 3.0. Display rule: <1 is decimal-rate, ≥1 is already-percentage.
    const pct = s < 1 ? s * 100 : s;
    return `${pct.toFixed(2)}%`;
  }
  if (underlying === 'NFP') return Math.round(s).toLocaleString();
  return String(s);
}

function weakestLink({ resolutionType, minDepth, netEdgePct, daysToResolution }) {
  if (netEdgePct <= 0) {
    return `Net edge negative after Polymarket taker fees and spread on both legs — gross inversion exists but execution erases it.`;
  }
  if (minDepth < 200) {
    return `Polymarket depth on the thinner leg limits fill to ~$${Math.round(minDepth)} before slippage closes the violation.`;
  }
  if (resolutionType === 'monthly' || resolutionType === 'quarterly') {
    return `Long-horizon (${Math.round(daysToResolution)} days) — capital tie-up at 8% annualized eats part of the edge before resolution.`;
  }
  return `Both legs must fill before either price moves; same-platform monotonicity violations close fast on liquid ladders.`;
}

function summarize({ canonical, low, high }) {
  const u = canonical.underlying;
  const d = canonical.direction;
  const lowS = fmtStrike(low.strike, u);
  const highS = fmtStrike(high.strike, u);
  const lowP = low.yes.toFixed(3);
  const highP = high.yes.toFixed(3);
  return `Polymarket ${u} ${d}-${lowS} priced ${lowP} but ${d}-${highS} priced ${highP} — strike monotonicity violation (${canonical.resolution_date} · ${canonical.resolution_type})`;
}

export async function runPass2(events, log) {
  // Flatten markets, normalize each, drop skips.
  const normalized = [];
  let polyMarketsScanned = 0;

  const nowMs = Date.now();
  for (const event of events) {
    const markets = Array.isArray(event.markets) ? event.markets : [];
    polyMarketsScanned += markets.length;
    for (const m of markets) {
      if (m.closed || m.active === false) continue;
      // Skip markets past their endDate — they're effectively resolved even
      // if Polymarket hasn't flagged them closed yet. Stale post-resolution
      // prices generate huge fake monotonicity violations.
      if (m.endDate && Date.parse(m.endDate) <= nowMs) continue;
      const prices = parsePrices(m.outcomePrices);
      if (!prices || prices.length < 1) continue;
      const yes = prices[0];
      if (!Number.isFinite(yes) || yes <= 0 || yes >= 1) continue;

      const norm = normalizePolymarket(m, event);
      if (norm.skip) {
        log.skip(`pass2_${norm.reason}`, norm.context);
        continue;
      }
      normalized.push({ event, market: m, yes, canonical: norm });
    }
  }

  // Group by event_id + canonical key (excluding strike). Cross-event grouping
  // was creating false pairs because Polymarket has unrelated events that
  // share underlyings/dates (e.g. "BTC reach 80k by Dec 31" vs "BTC 60k or
  // 80k first"). Within-event grouping matches the structure of real strike
  // ladders (negRisk and otherwise) without false cross-event matches.
  const groupKey = (n) =>
    `event:${n.event.id}|${n.canonical.underlying}|${n.canonical.direction}|${n.canonical.resolution_date}|${n.canonical.resolution_type}`;
  const groups = new Map();
  for (const item of normalized) {
    const k = groupKey(item);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push({
      strike: item.canonical.strike,
      yes: item.yes,
      market: item.market,
      event: item.event,
      canonical: item.canonical,
    });
  }

  // Detect violating pairs.
  const opportunities = [];
  let candidatesPreFilter = 0;

  for (const [, items] of groups.entries()) {
    if (items.length < 2) continue;
    items.sort((a, b) => a.strike - b.strike);

    // Adjacent-strike pairs only (i, i+1). Reasons:
    //   • avoids combinatorial blowup on long ladders (N markets → N pairs not N²)
    //   • adjacent inversions are the cleanest signal — non-adjacent
    //     "violations" usually compound multiple adjacent inversions
    //   • the spec says "any pair (low_strike, high_strike) where ..." but
    //     adjacent-only is a strict subset that catches the same MM bugs
    //     with one card per inverted strike instead of O(N) cards
    for (let i = 0; i < items.length - 1; i++) {
      {
        const low = items[i];
        const high = items[i + 1];
        if (low.strike === high.strike) continue;

        const direction = low.canonical.direction;
        // For "above": price should drop as strike rises → violation if low.yes < high.yes.
        // For "below": price should rise as strike rises → violation if low.yes > high.yes.
        const violation = direction === 'above'
          ? high.yes - low.yes
          : low.yes - high.yes;
        if (violation <= PAIR_VIOLATION_THRESHOLD) continue;

        candidatesPreFilter++;

        // Filter dead/sparse pairs — both legs must have real recent activity.
        // (was: only skipped when BOTH dead — too lax; was generating expired-
        // market false positives.)
        const lowV24 = Number(low.market.volume24hr || 0);
        const highV24 = Number(high.market.volume24hr || 0);
        if (lowV24 < 100 && highV24 < 100) {
          log.skip('pass2_pair_low_volume', { low_id: low.market.id, high_id: high.market.id });
          continue;
        }
        if (lowV24 === 0 || highV24 === 0) {
          log.skip('pass2_pair_dead_leg', { low_id: low.market.id, high_id: high.market.id });
          continue;
        }
        // Strike ratio sanity. A monotonicity ladder for a single asset shouldn't
        // span 5x in strike (real BTC ladders are $5k apart). Wider spans are
        // almost always expired-market artifacts spanning entire historic ranges.
        const ratio = Math.max(low.strike, high.strike) / Math.max(0.01, Math.min(low.strike, high.strike));
        if (ratio > 5 && low.canonical.underlying !== 'NFP') {
          log.skip('pass2_strike_ratio_too_wide', { low: low.strike, high: high.strike, ratio: +ratio.toFixed(1) });
          continue;
        }

        // Strategy: buy underpriced cheap leg YES, sell overpriced leg NO.
        // For "above" violation: low_strike YES is underpriced (lower-than-expected),
        //   buy YES on low; high_strike YES is overpriced, buy NO on high.
        // For "below" violation: symmetric — buy YES on high, NO on low.
        let cheapLeg, expensiveLeg, cheapSide, expensiveSide;
        if (direction === 'above') {
          cheapLeg = low; expensiveLeg = high;
          cheapSide = 'YES'; expensiveSide = 'NO';
        } else {
          cheapLeg = high; expensiveLeg = low;
          cheapSide = 'YES'; expensiveSide = 'NO';
        }

        const legs = [
          buildLeg({ event: cheapLeg.event, market: cheapLeg.market, side: cheapSide, yesPrice: cheapLeg.yes }),
          buildLeg({ event: expensiveLeg.event, market: expensiveLeg.market, side: expensiveSide, yesPrice: expensiveLeg.yes }),
        ];

        const grossEdgePct = +(violation * 100).toFixed(2);
        const minDepth = Math.min(...legs.map(l => l.depth_usd_at_price || 0));
        const endDate = high.market.endDate ? Date.parse(high.market.endDate) : NaN;
        const daysToResolution = Number.isFinite(endDate)
          ? Math.max(0, (endDate - Date.now()) / (24 * 3.6e6))
          : 30;
        const feesPct = estimateFeesPct({ legs, daysToResolution });
        const netEdgePct = +(grossEdgePct - feesPct).toFixed(2);
        const edgeNetPerDollar = +(netEdgePct / 100).toFixed(4);

        const depthSeverelyCapped = minDepth > 0 && minDepth < 200;
        let { tier, flags } = assignTier({
          grossEdgePct,
          legs,
          resolutionType: low.canonical.resolution_type,
          hasOffsetWarning: false,
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

        opportunities.push({
          id: stableId({
            canonical: low.canonical,
            lowMarketId: low.market.id,
            highMarketId: high.market.id,
          }),
          tier,
          type: 'poly_monotonicity',
          summary: summarize({ canonical: low.canonical, low, high }),
          underlying: low.canonical.underlying,
          resolution_date: low.canonical.resolution_date,
          resolution_type: low.canonical.resolution_type,
          legs,
          edge_gross_pct: grossEdgePct,
          edge_net_estimate_pct: netEdgePct,
          max_executable_size_per_leg_usd: Math.round(minDepth),
          edge_net_per_dollar: edgeNetPerDollar,
          weakest_link_summary: weakestLink({
            resolutionType: low.canonical.resolution_type,
            minDepth,
            netEdgePct,
            daysToResolution,
          }),
          confidence_flags: flags,
        });
      }
    }
  }

  return {
    opportunities,
    stats: {
      candidates_pre_filter: candidatesPreFilter,
      poly_markets_scanned: polyMarketsScanned,
      poly_normalized: normalized.length,
    },
  };
}
