// scanner/passes/pass3-kalshi-monotonicity.js
//
// Within-Kalshi strike monotonicity. Group all open Kalshi markets by
// (underlying, direction, resolution_date, resolution_type). Within each
// group, sort by strike ascending. For "above" markets prices should drop
// as strike rises; for "below" prices should rise.
//
// Reuses canonical-key + tier assignment logic from Pass 2. The only
// platform-specific difference is the price source: Kalshi prices are in
// _dollars-suffixed string fields (yes_ask_dollars, yes_bid_dollars).

import { normalizeKalshi } from '../normalize/kalshi.js';
import { estimateFeesPct, assignTier } from '../lib/tiering.js';

const PAIR_VIOLATION_THRESHOLD = 0.02; // 2pp

function parseDollars(s) {
  if (s == null) return null;
  const n = parseFloat(s);
  return Number.isFinite(n) ? n : null;
}

// On Kalshi, yes_ask is what you pay to buy YES. For monotonicity we use
// the mid (avg of bid and ask) when both exist, else the most informative
// of the available fields. Last_price isn't useful when the orderbook is
// active because it can lag by hours.
function midYesPrice(market) {
  const bid = parseDollars(market.yes_bid_dollars);
  const ask = parseDollars(market.yes_ask_dollars);
  if (bid != null && ask != null && ask > 0 && bid >= 0 && ask >= bid) {
    return (bid + ask) / 2;
  }
  if (ask != null && ask > 0 && ask < 1) return ask;
  if (bid != null && bid > 0 && bid < 1) return bid;
  const last = parseDollars(market.last_price_dollars);
  if (last != null && last > 0 && last < 1) return last;
  return null;
}

function depthEstimate(market) {
  // liquidity_dollars is total resting liquidity; use 25% as at-price depth proxy.
  const liq = parseDollars(market.liquidity_dollars);
  if (liq == null || liq <= 0) {
    // Fall back to bid/ask sizes if liquidity_dollars is missing.
    const bidSize = Number(market.yes_bid_size_fp || 0);
    const askSize = Number(market.yes_ask_size_fp || 0);
    const sized = (bidSize + askSize) * (parseDollars(market.yes_ask_dollars) || 0.5);
    return Math.round(sized);
  }
  return Math.round(liq * 0.25);
}

function lastTradeAt(market) {
  // Kalshi exposes updated_time on each market record. If volume_24h_fp > 0
  // there were trades in the last 24h, so updated_time is a reasonable proxy.
  // No volume → return null and let the recency filter mark it stale.
  const v24 = Number(market.volume_24h_fp || 0);
  if (v24 > 0 && market.updated_time) return market.updated_time;
  return null;
}

function legUrl(market) {
  if (!market.ticker) return null;
  return `https://kalshi.com/markets/${market.event_ticker || ''}/${market.ticker}`;
}

function buildLeg({ market, side, yesPrice }) {
  const v24 = Number(market.volume_24h_fp || 0);
  return {
    platform: 'kalshi',
    market_id: market.ticker,
    market_url: legUrl(market),
    side,
    price: side === 'YES' ? +yesPrice.toFixed(4) : +(1 - yesPrice).toFixed(4),
    depth_usd_at_price: depthEstimate(market),
    last_trade_at: lastTradeAt(market),
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

function stableId({ canonical, lowTicker, highTicker }) {
  const [a, b] = [lowTicker, highTicker].sort();
  return `pass3-kalshi-mono-${canonical.underlying}-${canonical.direction}-${canonical.resolution_date}-${canonical.resolution_type}-${a}-${b}`;
}

function weakestLink({ resolutionType, minDepth, netEdgePct, daysToResolution }) {
  if (netEdgePct <= 0) {
    return `Net edge negative after Kalshi 0.07·C·P·(1−P) fees and spread on both legs.`;
  }
  if (minDepth < 200) {
    return `Kalshi depth on the thinner leg limits fill to ~$${Math.round(minDepth)} before slippage closes the violation.`;
  }
  if (resolutionType === 'monthly' || resolutionType === 'quarterly') {
    return `Long-horizon (${Math.round(daysToResolution)} days) — capital tie-up at 8% annualized eats part of the edge.`;
  }
  return `Both Kalshi legs must fill near simultaneously; same-platform inversions on liquid ladders close fast.`;
}

function summarize({ canonical, low, high }) {
  const u = canonical.underlying;
  const d = canonical.direction;
  return `Kalshi ${u} ${d}-${fmtStrike(low.strike, u)} priced ${low.yes.toFixed(3)} but ${d}-${fmtStrike(high.strike, u)} priced ${high.yes.toFixed(3)} — strike monotonicity violation (${canonical.resolution_date} · ${canonical.resolution_type})`;
}

export async function runPass3(kalshiMarkets, log) {
  const normalized = [];
  const kalshiMarketsScanned = kalshiMarkets.length;

  for (const m of kalshiMarkets) {
    if (m.status && m.status !== 'active' && m.status !== 'open') continue;
    const yes = midYesPrice(m);
    if (yes == null || yes <= 0 || yes >= 1) continue;

    const norm = normalizeKalshi(m);
    if (norm.skip) {
      log.skip(`pass3_${norm.reason}`, norm.context);
      continue;
    }
    normalized.push({ market: m, yes, canonical: norm });
  }

  const groupKey = (n) =>
    `${n.canonical.underlying}|${n.canonical.direction}|${n.canonical.resolution_date}|${n.canonical.resolution_type}`;
  const groups = new Map();
  for (const item of normalized) {
    const k = groupKey(item);
    if (!groups.has(k)) groups.set(k, []);
    groups.get(k).push({
      strike: item.canonical.strike,
      yes: item.yes,
      market: item.market,
      canonical: item.canonical,
    });
  }

  const opportunities = [];
  let candidatesPreFilter = 0;

  for (const [, items] of groups.entries()) {
    if (items.length < 2) continue;
    items.sort((a, b) => a.strike - b.strike);

    // Adjacent-strike pairs only — see pass2 comment for rationale.
    for (let i = 0; i < items.length - 1; i++) {
      {
        const low = items[i];
        const high = items[i + 1];
        if (low.strike === high.strike) continue;

        const direction = low.canonical.direction;
        const violation = direction === 'above'
          ? high.yes - low.yes
          : low.yes - high.yes;
        if (violation <= PAIR_VIOLATION_THRESHOLD) continue;

        candidatesPreFilter++;

        const lowV24 = Number(low.market.volume_24h_fp || 0);
        const highV24 = Number(high.market.volume_24h_fp || 0);
        if (lowV24 < 100 && highV24 < 100) {
          log.skip('pass3_pair_low_volume', { low: low.market.ticker, high: high.market.ticker });
          continue;
        }
        if (lowV24 === 0 || highV24 === 0) {
          log.skip('pass3_pair_dead_leg', { low: low.market.ticker, high: high.market.ticker });
          continue;
        }
        const ratio = Math.max(low.strike, high.strike) / Math.max(0.01, Math.min(low.strike, high.strike));
        if (ratio > 5 && low.canonical.underlying !== 'NFP') {
          log.skip('pass3_strike_ratio_too_wide', { low: low.strike, high: high.strike, ratio: +ratio.toFixed(1) });
          continue;
        }

        let cheapLeg, expensiveLeg, cheapSide, expensiveSide;
        if (direction === 'above') {
          cheapLeg = low; expensiveLeg = high;
          cheapSide = 'YES'; expensiveSide = 'NO';
        } else {
          cheapLeg = high; expensiveLeg = low;
          cheapSide = 'YES'; expensiveSide = 'NO';
        }

        const legs = [
          buildLeg({ market: cheapLeg.market, side: cheapSide, yesPrice: cheapLeg.yes }),
          buildLeg({ market: expensiveLeg.market, side: expensiveSide, yesPrice: expensiveLeg.yes }),
        ];

        const grossEdgePct = +(violation * 100).toFixed(2);
        const minDepth = Math.min(...legs.map(l => l.depth_usd_at_price || 0));
        const exp = high.market.expiration_time ? Date.parse(high.market.expiration_time) : NaN;
        const daysToResolution = Number.isFinite(exp)
          ? Math.max(0, (exp - Date.now()) / (24 * 3.6e6))
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
          id: stableId({ canonical: low.canonical, lowTicker: low.market.ticker, highTicker: high.market.ticker }),
          tier,
          type: 'kalshi_monotonicity',
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
            minDepth, netEdgePct, daysToResolution,
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
      kalshi_markets_scanned: kalshiMarketsScanned,
      kalshi_normalized: normalized.length,
    },
  };
}
