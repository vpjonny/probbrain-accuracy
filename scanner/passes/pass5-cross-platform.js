// scanner/passes/pass5-cross-platform.js
//
// The high-leverage pass: same question priced differently on Polymarket and
// Kalshi. Strategy: buy YES on the underpriced venue, NO on the overpriced
// one. Risk-free if both legs settle the same way (which they should, by
// construction — that's what canonical-key matching guarantees).
//
// Architecture:
//   1. Normalize every Polymarket child market via normalizePolymarket.
//   2. Normalize every Kalshi market via normalizeKalshi.
//   3. Build per-platform Map<canonical_key, items[]>. Hard equality, no fuzzy.
//   4. For each canonical key present on both venues, cross-product the items
//      and emit one opportunity per (poly, kalshi) pair with spread > threshold.
//   5. Filter pipeline: recency → settlement-offset → depth → fee/edge → tier.

import { normalizePolymarket } from '../normalize/polymarket.js';
import { normalizeKalshi } from '../normalize/kalshi.js';
import { serializeCanonicalKey, logCollisions } from '../lib/canonical.js';
import {
  estimateFeesPct, assignTier, offsetTolerance,
} from '../lib/tiering.js';

const SPREAD_THRESHOLD = 0.02; // 2pp — below this, fees + spread always eat it

// ── Polymarket leg helpers ──────────────────────────────────────────────────
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

// ── Kalshi leg helpers ──────────────────────────────────────────────────────
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

// ── leg builders ────────────────────────────────────────────────────────────
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

// ── formatting ──────────────────────────────────────────────────────────────
function fmtStrike(s, underlying) {
  if (['BTC', 'ETH', 'SOL'].includes(underlying)) return `$${Math.round(s).toLocaleString()}`;
  if (['CPI', 'FED_RATE'].includes(underlying)) {
    const pct = s < 1 ? s * 100 : s;
    return `${pct.toFixed(2)}%`;
  }
  if (underlying === 'NFP') return Math.round(s).toLocaleString();
  return String(s);
}

function summarize({ canonical, polyYes, kalshiYes }) {
  const u = canonical.underlying;
  const d = canonical.direction;
  const dir = polyYes > kalshiYes ? 'Poly higher' : 'Kalshi higher';
  return `${u} ${d}-${fmtStrike(canonical.strike, u)} on ${canonical.resolution_date} — Polymarket YES ${polyYes.toFixed(3)} vs Kalshi YES ${kalshiYes.toFixed(3)} (${dir} by ${(Math.abs(polyYes - kalshiYes) * 100).toFixed(1)}pp)`;
}

function stableId({ canonical, polyId, kalshiId }) {
  return `pass5-cross-${canonical.underlying}-${canonical.direction}-${canonical.strike}-${canonical.resolution_date}-${canonical.resolution_type}-poly${polyId}-kalshi${kalshiId}`;
}

function weakestLink({ minDepth, netEdgePct, offsetMin, resolutionType, daysToResolution }) {
  if (netEdgePct <= 0) {
    return `Net edge negative after fees — Poly taker + Kalshi 0.07·C·P·(1−P) + spread + bridge consume the cross-platform spread.`;
  }
  if (minDepth < 200) {
    return `Thinner-leg depth limits fill to ~$${Math.round(minDepth)} before slippage closes the spread on that venue.`;
  }
  const tol = offsetTolerance(resolutionType);
  if (offsetMin > tol) {
    return `Settlement times differ by ${Math.round(offsetMin)}min on a ${resolutionType} market (tolerance ${tol}min) — underlying can move between settlements and break the arb.`;
  }
  if (resolutionType === 'monthly' || resolutionType === 'quarterly') {
    return `Long-horizon (${Math.round(daysToResolution)} days) — capital tie-up on both venues at 8% annualized eats part of the edge.`;
  }
  return `Both legs must fill near-simultaneously across two venues; cross-platform execution adds latency risk versus same-platform arbs.`;
}

// ── main ────────────────────────────────────────────────────────────────────
export async function runPass5(polyEvents, kalshiMarkets, log) {
  const nowMs = Date.now();

  // 1. Normalize Polymarket child markets.
  const polyItems = [];
  for (const event of polyEvents) {
    for (const m of (event.markets || [])) {
      if (m.closed || m.active === false) continue;
      if (m.endDate && Date.parse(m.endDate) <= nowMs) continue;
      const prices = parsePolyPrices(m.outcomePrices);
      if (!prices || prices.length < 1) continue;
      const yes = prices[0];
      if (!Number.isFinite(yes) || yes <= 0 || yes >= 1) continue;
      const norm = normalizePolymarket(m, event);
      if (norm.skip) {
        log.skip(`pass5_poly_${norm.reason}`, norm.context);
        continue;
      }
      polyItems.push({ event, market: m, yes, canonical: norm, rawDate: m.endDate, platform: 'polymarket' });
    }
  }

  // 2. Normalize Kalshi markets.
  const kalshiItems = [];
  for (const m of kalshiMarkets) {
    if (m.status && m.status !== 'active' && m.status !== 'open') continue;
    const yes = kalshiMidYes(m);
    if (yes == null || yes <= 0 || yes >= 1) continue;
    const norm = normalizeKalshi(m);
    if (norm.skip) {
      log.skip(`pass5_kalshi_${norm.reason}`, norm.context);
      continue;
    }
    kalshiItems.push({ market: m, yes, canonical: norm, rawDate: m.expiration_time || m.close_time, platform: 'kalshi' });
  }

  // 3. Per-platform canonical-key index.
  const polyByKey = new Map();
  const kalshiByKey = new Map();
  for (const item of polyItems) {
    const k = serializeCanonicalKey(item.canonical);
    if (!polyByKey.has(k)) polyByKey.set(k, []);
    polyByKey.get(k).push(item);
  }
  for (const item of kalshiItems) {
    const k = serializeCanonicalKey(item.canonical);
    if (!kalshiByKey.has(k)) kalshiByKey.set(k, []);
    kalshiByKey.get(k).push(item);
  }

  // Collision detection — same canonical key from two markets of the same
  // platform = normalization is producing identical keys for distinct markets.
  // Logs but doesn't crash.
  const allItems = [
    ...polyItems.map(i => ({ ...i, market: { ...i.market, platform: 'polymarket', id: i.market.id } })),
    ...kalshiItems.map(i => ({ ...i, market: { ...i.market, platform: 'kalshi', id: i.market.ticker } })),
  ];
  const allByKey = new Map();
  for (const it of allItems) {
    const k = serializeCanonicalKey(it.canonical);
    if (!allByKey.has(k)) allByKey.set(k, []);
    allByKey.get(k).push(it);
  }
  logCollisions(allByKey, 'polymarket', log);
  logCollisions(allByKey, 'kalshi', log);

  // 4. Find canonical-key matches (key present on both venues).
  const opportunities = [];
  let candidatesPreFilter = 0;

  for (const [key, polyArr] of polyByKey.entries()) {
    if (!kalshiByKey.has(key)) continue;
    const kalshiArr = kalshiByKey.get(key);

    for (const p of polyArr) {
      for (const k of kalshiArr) {
        const polyYes = p.yes;
        const kalshiYes = k.yes;
        const spread = Math.abs(polyYes - kalshiYes);
        if (spread <= SPREAD_THRESHOLD) continue;
        candidatesPreFilter++;

        // Settlement-time offset. Within tolerance: clean. Over tolerance:
        // downgrade one tier with offset_warning (per spec). Way over (4× the
        // tier-2 tolerance): skip — the cross-platform thesis breaks because
        // one venue settles on stale data the other already moved past.
        const polyT = Date.parse(p.rawDate);
        const kalshiT = Date.parse(k.rawDate);
        const offsetMin = (Number.isFinite(polyT) && Number.isFinite(kalshiT))
          ? Math.abs(polyT - kalshiT) / 60_000
          : 0;
        const tol = offsetTolerance(p.canonical.resolution_type);
        if (offsetMin > tol * 4) {
          log.skip('pass5_offset_too_large', {
            offset_min: Math.round(offsetMin), tolerance_min: tol, key,
          });
          continue;
        }

        // Sanity: both legs must have real recent activity. One dead venue
        // means we'd be pricing against a stale book on that side.
        const polyV24 = Number(p.market.volume24hr || 0);
        const kalshiV24 = Number(k.market.volume_24h_fp || 0);
        if (polyV24 === 0 || kalshiV24 === 0) {
          log.skip('pass5_pair_dead_leg', {
            key, poly_v24: polyV24, kalshi_v24: kalshiV24,
          });
          continue;
        }
        if (polyV24 < 100 && kalshiV24 < 100) {
          log.skip('pass5_pair_low_volume', {
            key, poly_v24: polyV24, kalshi_v24: kalshiV24,
          });
          continue;
        }

        // Determine which side is underpriced. Buy YES on the cheaper venue,
        // NO on the more expensive one. Risk-free if both resolve identically.
        let cheapItem, expItem, cheapPlatform, expPlatform;
        if (polyYes < kalshiYes) {
          cheapItem = p; expItem = k;
          cheapPlatform = 'polymarket'; expPlatform = 'kalshi';
        } else {
          cheapItem = k; expItem = p;
          cheapPlatform = 'kalshi'; expPlatform = 'polymarket';
        }
        const buildCheap = cheapPlatform === 'polymarket' ? polyLeg : kalshiLeg;
        const buildExp = expPlatform === 'polymarket' ? polyLeg : kalshiLeg;
        const cheapLeg = cheapPlatform === 'polymarket'
          ? buildCheap({ event: cheapItem.event, market: cheapItem.market, side: 'YES', yesPrice: cheapItem.yes })
          : buildCheap({ market: cheapItem.market, side: 'YES', yesPrice: cheapItem.yes });
        const expLeg = expPlatform === 'polymarket'
          ? buildExp({ event: expItem.event, market: expItem.market, side: 'NO', yesPrice: expItem.yes })
          : buildExp({ market: expItem.market, side: 'NO', yesPrice: expItem.yes });
        const legs = [cheapLeg, expLeg];

        const grossEdgePct = +(spread * 100).toFixed(2);
        const minDepth = Math.min(...legs.map(l => l.depth_usd_at_price || 0));
        const endMs = Math.max(polyT || 0, kalshiT || 0);
        const daysToResolution = endMs > 0
          ? Math.max(0, (endMs - nowMs) / (24 * 3.6e6))
          : 30;
        const feesPct = estimateFeesPct({ legs, daysToResolution });
        const netEdgePct = +(grossEdgePct - feesPct).toFixed(2);
        const edgeNetPerDollar = +(netEdgePct / 100).toFixed(4);

        const depthSeverelyCapped = minDepth > 0 && minDepth < 200;
        const hasOffsetWarning = offsetMin > tol;

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

        opportunities.push({
          id: stableId({
            canonical: p.canonical,
            polyId: p.market.id,
            kalshiId: k.market.ticker,
          }),
          tier,
          type: 'cross_platform',
          summary: summarize({
            canonical: p.canonical,
            polyYes,
            kalshiYes,
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
            minDepth, netEdgePct, offsetMin,
            resolutionType: p.canonical.resolution_type, daysToResolution,
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
      poly_normalized_for_match: polyItems.length,
      kalshi_normalized_for_match: kalshiItems.length,
      shared_canonical_keys: [...polyByKey.keys()].filter(k => kalshiByKey.has(k)).length,
    },
  };
}
