// scanner/passes/pass1-poly-sum.js — Polymarket negRisk sum violations.
//
// For every open Polymarket event with negRisk=true (mutually exclusive
// markets), sum the YES prices across child markets. If |sum - 1.0| > 0.015,
// we have a candidate.
//
//   sum < 1 → buy_all_YES, profit per share-set = 1 - sum
//   sum > 1 → buy_all_NO,  profit per share-set = sum - 1
//
// This is the cheapest pass — no matching, no normalization. Catches
// Polymarket's own internal pricing inconsistencies.

import { estimateFeesPct, assignTier } from '../lib/tiering.js';

const VIOLATION_THRESHOLD = 0.015;
// Above ~5pp the "violation" is more likely a structural artifact (open
// universe — e.g. "next X" markets with a NULL/unlisted-winner category, or
// sports brackets that include implicit "tie/other" outcomes) than a
// tradeable mispricing. Real Polymarket sum violations on tight negRisk
// baskets typically sit in the 1.5–5pp range. Above the threshold we still
// surface but cap at Tier 2 with a resolution_mismatch flag — buying all
// listed YES doesn't pay $1 if an unlisted outcome wins.
const STRUCTURAL_VIOLATION_THRESHOLD = 0.05;
// Hard sanity cap. >10pp on negRisk almost always means the basket doesn't
// span the universe — drop entirely rather than report.
const MAX_REPORTABLE_VIOLATION = 0.10;

function parseOutcomePrices(raw) {
  if (Array.isArray(raw)) return raw.map(Number);
  if (typeof raw === 'string') {
    try { return JSON.parse(raw).map(Number); } catch { return null; }
  }
  return null;
}

function detectResolutionType(event) {
  const text = `${event.slug || ''} ${event.title || ''}`.toLowerCase();
  if (/\bhourly\b|hour-by/.test(text)) return 'hourly';
  if (/\bdaily\b|today|tomorrow/.test(text)) return 'daily';
  if (/\bweekly\b|week-of/.test(text)) return 'weekly';
  if (/\bquarterly\b/.test(text)) return 'quarterly';
  if (/\bmonthly\b/.test(text)) return 'monthly';
  // Infer from time-to-end
  const end = event.endDate ? Date.parse(event.endDate) : NaN;
  if (Number.isFinite(end)) {
    const hoursToEnd = (end - Date.now()) / 3.6e6;
    if (hoursToEnd <= 0)        return 'hourly';
    if (hoursToEnd < 24)        return 'hourly';
    if (hoursToEnd < 24 * 7)    return 'daily';
    if (hoursToEnd < 24 * 30)   return 'weekly';
    if (hoursToEnd < 24 * 100)  return 'monthly';
    return 'quarterly';
  }
  return 'monthly';
}

function detectUnderlying(event) {
  const text = `${event.slug || ''} ${event.title || ''}`.toLowerCase();
  if (/\bbtc\b|bitcoin/.test(text)) return 'BTC';
  if (/\beth\b|ethereum/.test(text)) return 'ETH';
  if (/\bsol\b|solana/.test(text)) return 'SOL';
  if (/\bfed\b|fomc|federal funds|interest rate/.test(text)) return 'FED_RATE';
  if (/\bcpi\b|inflation|consumer price/.test(text)) return 'CPI';
  if (/\bnfp\b|nonfarm|jobs report/.test(text)) return 'NFP';
  return 'OTHER';
}

// Liquidity is total resting orders, not depth at the displayed price.
// Without a CLOB orderbook call we use a conservative fraction as the
// at-price depth estimate (kept honest — flagged depth_limited if thin).
function depthEstimate(market) {
  const liq = Number(market.liquidityNum ?? market.liquidity ?? 0);
  if (!Number.isFinite(liq) || liq <= 0) return 0;
  return Math.round(liq * 0.25);
}

// Trade-time heuristic. lastTradeTime is the truth but is null in many Gamma
// event payloads. updatedAt by itself is unreliable (it bumps on any metadata
// change, not real trades) — but combined with non-zero 24h volume it's a
// reasonable proxy for "the orderbook was active in the last 24h".
function lastTradeAt(market) {
  if (market.lastTradeTime) return market.lastTradeTime;
  const v24 = Number(market.volume24hr || 0);
  if (v24 > 0 && market.updatedAt) return market.updatedAt;
  return null;
}

function legUrl(event, market) {
  if (!event.slug) return null;
  if (market.slug && market.slug !== event.slug) {
    return `https://polymarket.com/event/${event.slug}/${market.slug}`;
  }
  return `https://polymarket.com/event/${event.slug}`;
}

// Stable id — same opportunity keeps its id across scans so the frontend
// can dedupe and persist UI state.
function stableId(event, sumLow) {
  const slug = event.slug || `event-${event.id}`;
  return `pass1-poly-sum-${slug}-${sumLow ? 'underpriced' : 'overpriced'}`;
}

function weakestLinkSummary({ legs, netEdgePct, minDepth, resolutionType, nLegs }) {
  if (netEdgePct <= 0) {
    return `Net edge negative after fees at any size — sum violation exists but Polymarket fees + spread on ${nLegs} legs consume it.`;
  }
  if (minDepth < 200) {
    return `Polymarket depth on the thinnest leg limits fill to ~$${Math.round(minDepth)} before slippage exceeds the edge.`;
  }
  if (resolutionType === 'monthly' || resolutionType === 'quarterly') {
    return `Long-horizon resolution — capital tie-up at 8% annualized eats part of the edge before settlement.`;
  }
  return `Multi-leg basket — all ${nLegs} legs must fill before any individual price moves, otherwise the violation closes mid-execution.`;
}

export async function runPass1(events, log) {
  const opportunities = [];
  let candidatesPreFilter = 0;
  let polyMarketsScanned = 0;

  for (const event of events) {
    const markets = Array.isArray(event.markets) ? event.markets : [];
    polyMarketsScanned += markets.length;

    if (!event.negRisk) continue;
    if (markets.length < 2) {
      log.skip('negrisk_event_too_few_markets', { event_id: event.id, n_markets: markets.length });
      continue;
    }

    let sumYes = 0;
    let validLegs = 0;
    let minDepth = Infinity;
    let totalVolume24h = 0;
    const legs = [];

    for (const m of markets) {
      // Skip closed/inactive child markets — they shouldn't contribute to sum.
      if (m.closed || m.active === false) {
        log.skip('child_market_closed_or_inactive', { event_id: event.id, market_id: m.id });
        continue;
      }
      const prices = parseOutcomePrices(m.outcomePrices);
      if (!prices || prices.length < 1) {
        log.skip('child_market_missing_prices', { event_id: event.id, market_id: m.id });
        continue;
      }
      const yes = prices[0];
      if (!Number.isFinite(yes) || yes <= 0 || yes >= 1) {
        log.skip('child_market_invalid_yes', { event_id: event.id, market_id: m.id, yes });
        continue;
      }

      sumYes += yes;
      validLegs++;
      const depth = depthEstimate(m);
      if (depth > 0 && depth < minDepth) minDepth = depth;
      const v24 = Number(m.volume24hr ?? 0);
      if (Number.isFinite(v24)) totalVolume24h += v24;

      legs.push({
        platform: 'polymarket',
        market_id: String(m.id),
        market_url: legUrl(event, m),
        side: 'YES',
        price: +yes.toFixed(4),
        depth_usd_at_price: depth,
        last_trade_at: lastTradeAt(m),
        volume_24h_usd: Number.isFinite(v24) ? Math.round(v24) : 0,
      });
    }

    if (validLegs < 2) {
      log.skip('not_enough_valid_child_markets', { event_id: event.id, valid_legs: validLegs });
      continue;
    }
    // Filter out dead markets — every leg with $0 24h volume AND no last trade.
    // These are frozen orderbooks with stale prices; surfacing them as Tier-3
    // signals would bury real opportunities under thousands of zombies.
    const allDead = legs.every(l =>
      (l.volume_24h_usd ?? 0) === 0 && !l.last_trade_at
    );
    if (allDead) {
      log.skip('event_all_legs_dead_or_zero_volume', {
        event_id: event.id, slug: event.slug, n_legs: validLegs,
      });
      continue;
    }
    const violationMagnitude = Math.abs(sumYes - 1.0);
    if (violationMagnitude <= VIOLATION_THRESHOLD) continue;
    if (violationMagnitude > MAX_REPORTABLE_VIOLATION) {
      log.skip('violation_too_large_likely_open_universe', {
        event_id: event.id, slug: event.slug, sum: +sumYes.toFixed(3), n_legs: validLegs,
      });
      continue;
    }

    candidatesPreFilter++;

    const sumLow = sumYes < 1.0;
    const grossEdgePct = +(violationMagnitude * 100).toFixed(2);
    if (!Number.isFinite(minDepth)) minDepth = 0;

    const endDate = event.endDate ? Date.parse(event.endDate) : NaN;
    const daysToResolution = Number.isFinite(endDate)
      ? Math.max(0, (endDate - Date.now()) / (24 * 3.6e6))
      : 30;

    const feesPct = estimateFeesPct({ legs, daysToResolution });
    const netEdgePct = +(grossEdgePct - feesPct).toFixed(2);
    const edgeNetPerDollar = +(netEdgePct / 100).toFixed(4);

    const resolutionType = detectResolutionType(event);
    const underlying = detectUnderlying(event);
    const resolutionDate = event.endDate ? event.endDate.slice(0, 10) : null;

    const depthSeverelyCapped = minDepth > 0 && minDepth < 200;
    let { tier, flags } = assignTier({
      grossEdgePct,
      legs,
      resolutionType,
      hasOffsetWarning: false, // single-platform — no cross-venue settlement offset
      depthSeverelyCapped,
      netEdgePct,
    });

    // ── Pass-1 specific gates that cap Tier 1 ───────────────────────────────
    // A negRisk basket only pays $1 if exactly one outcome resolves YES — for
    // long-tail "next X" events with an open universe, that's not guaranteed.
    if (violationMagnitude > STRUCTURAL_VIOLATION_THRESHOLD) {
      tier = Math.max(tier, 2);
      if (!flags.includes('resolution_mismatch')) flags.push('resolution_mismatch');
    }
    // Any leg with no real recent trade → can't trust the displayed price.
    if (legs.some(l => !l.last_trade_at)) {
      tier = Math.max(tier, 3);
      if (!flags.includes('stale_price')) flags.push('stale_price');
    }
    // Any leg with $0 24h volume → not actionable.
    if (legs.some(l => (l.volume_24h_usd ?? 0) === 0)) {
      tier = Math.max(tier, 3);
      if (!flags.includes('low_volume')) flags.push('low_volume');
    } else if (legs.some(l => (l.volume_24h_usd ?? 0) < 1000)) {
      // <$1k 24h on any leg → still flag but don't auto-Tier-3
      tier = Math.max(tier, 2);
      if (!flags.includes('low_volume')) flags.push('low_volume');
    }
    if (depthSeverelyCapped && !flags.includes('depth_limited')) flags.push('depth_limited');
    // Net edge negative after fees → not actionable, max Tier 2 (signal only).
    if (netEdgePct <= 0) {
      tier = Math.max(tier, 2);
    }

    const strategy = sumLow ? 'buy-all-YES' : 'buy-all-NO';
    const summary = `Polymarket negRisk: ${event.title || event.slug || event.id} — ${validLegs} legs sum to ${sumYes.toFixed(3)} (${grossEdgePct.toFixed(1)}pp ${sumLow ? 'underpriced' : 'overpriced'}; ${strategy})`;

    opportunities.push({
      id: stableId(event, sumLow),
      tier,
      type: 'poly_sum_violation',
      summary,
      underlying,
      resolution_date: resolutionDate,
      resolution_type: resolutionType,
      legs,
      edge_gross_pct: grossEdgePct,
      edge_net_estimate_pct: netEdgePct,
      max_executable_size_per_leg_usd: Math.round(minDepth),
      edge_net_per_dollar: edgeNetPerDollar,
      weakest_link_summary: weakestLinkSummary({
        legs, netEdgePct, minDepth, resolutionType, nLegs: validLegs,
      }),
      confidence_flags: flags,
    });
  }

  return {
    opportunities,
    stats: {
      candidates_pre_filter: candidatesPreFilter,
      poly_markets_scanned: polyMarketsScanned,
    },
  };
}
