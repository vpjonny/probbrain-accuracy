// scanner/passes/pass4-curated-cross.js
//
// Curated cross-platform pairs. Pass 5 matches by strict canonical key (with
// a strike-only fallback capped at Tier 2). Pass 4 is the human-validated
// path: a hand-maintained dict of (Poly bucket, Kalshi bucket) entries that
// the operator has confirmed describe the SAME observable event, even when
// the venues' canonical keys don't match — different end-date timestamps,
// different strike rounding, etc.
//
// Why this exists: in practice Poly and Kalshi sell different products on
// the same underlying — Poly ladders by year-end, Kalshi by daily/weekly.
// The few genuine overlaps (year-end strike ladders, scheduled release
// events) need a curator's judgment to bridge.
//
// Structure mirrors Pass 5: normalize, match, build legs, fee/tier. The
// difference is the matching step uses the curated dict instead of canonical
// equality, and `sameResolutionWindow: true` entries are allowed Tier 1 even
// when resolution_date timestamps don't strictly match.
//
// Returns { opportunities, stats, coveredPairs } where coveredPairs is a
// Set<"poly_id|kalshi_ticker"> so Pass 5 can dedupe — when both passes would
// surface the same physical pair, Pass 4's curated context wins.

import { normalizePolymarket } from '../normalize/polymarket.js';
import { normalizeKalshi } from '../normalize/kalshi.js';
import { CURATED_PAIRS, pairsMatch } from '../dicts/curated-pairs.js';
import {
  estimateFeesPct, assignTier, offsetTolerance,
} from '../lib/tiering.js';

const SPREAD_THRESHOLD = 0.02;

// ── price + leg helpers (parallel to Pass 5) ────────────────────────────────
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

function summarize({ pair, polyCanonical, kalshiCanonical, polyYes, kalshiYes }) {
  const u = polyCanonical.underlying;
  const d = polyCanonical.direction;
  const sP = fmtStrike(polyCanonical.strike, u);
  const sK = fmtStrike(kalshiCanonical.strike, u);
  const strikeBlob = sP === sK ? sP : `${sP}↔${sK}`;
  const dir = polyYes > kalshiYes ? 'Poly higher' : 'Kalshi higher';
  return `[curated:${pair.id}] ${u} ${d}-${strikeBlob} — Polymarket YES ${polyYes.toFixed(3)} vs Kalshi YES ${kalshiYes.toFixed(3)} (${dir} by ${(Math.abs(polyYes - kalshiYes) * 100).toFixed(1)}pp)`;
}

function stableId({ pair, polyCanonical, polyId, kalshiId }) {
  return `pass4-curated-${pair.id}-${polyCanonical.underlying}-${polyCanonical.direction}-${polyCanonical.strike}-poly${polyId}-kalshi${kalshiId}`;
}

function weakestLink({ pair, minDepth, netEdgePct, offsetMin, resolutionType, daysToResolution }) {
  if (netEdgePct <= 0) {
    return `Net edge negative after fees — Poly taker + Kalshi 0.07·C·P·(1−P) + spread + bridge consume the spread.`;
  }
  if (minDepth < 200) {
    return `Thinner-leg depth limits fill to ~$${Math.round(minDepth)} before slippage closes the spread on that venue.`;
  }
  const tol = offsetTolerance(resolutionType);
  if (offsetMin > tol && !pair.sameResolutionWindow) {
    return `Settlement times differ by ${Math.round(offsetMin)}min on a ${resolutionType} market (tolerance ${tol}min) — underlying can move between settlements and break the arb.`;
  }
  if (resolutionType === 'monthly' || resolutionType === 'quarterly') {
    return `Long-horizon (${Math.round(daysToResolution)} days) — capital tie-up on both venues at 8% annualized eats part of the edge.`;
  }
  return `Curated pair "${pair.id}" — operator-validated cross-platform match. Both legs must fill near-simultaneously across two venues; cross-platform execution adds latency risk.`;
}

// ── main ────────────────────────────────────────────────────────────────────
// opts.curatedPairs: override the curated dict (used by tests). Defaults to
//   the module-level CURATED_PAIRS.
export async function runPass4(polyEvents, kalshiMarkets, log, opts = {}) {
  const nowMs = Date.now();
  const pairs = Array.isArray(opts.curatedPairs) ? opts.curatedPairs : CURATED_PAIRS;
  const opportunities = [];
  const coveredPairs = new Set();
  let candidatesPreFilter = 0;

  // Pre-normalize all candidate items so we can run multiple curated entries
  // without re-normalizing every market each time. Keep the raw market on the
  // item so filters can consult event/market shape directly.
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
      polyAll.push({ event, market: m, yes, canonical: norm, rawDate: m.endDate });
    }
  }
  const kalshiAll = [];
  for (const m of kalshiMarkets) {
    if (m.status && m.status !== 'active' && m.status !== 'open') continue;
    const yes = kalshiMidYes(m);
    if (yes == null || yes <= 0 || yes >= 1) continue;
    const norm = normalizeKalshi(m);
    if (norm.skip) continue;
    kalshiAll.push({ market: m, yes, canonical: norm, rawDate: m.expiration_time || m.close_time });
  }

  for (const pair of pairs) {
    const polyItems = polyAll.filter(it => {
      if (it.canonical.underlying !== pair.underlying) return false;
      try { return pair.polyFilter(it.event, it.market); }
      catch (e) { log.warn(`pass4: polyFilter error for ${pair.id}: ${e.message}`); return false; }
    });
    const kalshiItems = kalshiAll.filter(it => {
      if (it.canonical.underlying !== pair.underlying) return false;
      try { return pair.kalshiFilter(it.market); }
      catch (e) { log.warn(`pass4: kalshiFilter error for ${pair.id}: ${e.message}`); return false; }
    });

    log.info(`pass4: pair "${pair.id}" — poly_candidates=${polyItems.length} kalshi_candidates=${kalshiItems.length}`);
    if (polyItems.length === 0 || kalshiItems.length === 0) continue;

    for (const p of polyItems) {
      for (const k of kalshiItems) {
        const m = pairsMatch(pair, p.canonical, k.canonical);
        if (!m.matches) {
          log.skip(`pass4_${pair.id}_${m.reason}`, {
            poly_id: p.market.id, kalshi: k.market.ticker,
            poly_strike: p.canonical.strike, kalshi_strike: k.canonical.strike,
          });
          continue;
        }

        const polyYes = p.yes;
        const kalshiYes = k.yes;
        const spread = Math.abs(polyYes - kalshiYes);
        if (spread <= SPREAD_THRESHOLD) continue;
        candidatesPreFilter++;

        // Settlement-time offset. For curated pairs with sameResolutionWindow
        // we're explicitly asserting the windows are equivalent — skip the
        // offset filter. Otherwise apply same 4× tolerance hard cap as Pass 5.
        const polyT = Date.parse(p.rawDate);
        const kalshiT = Date.parse(k.rawDate);
        const offsetMin = (Number.isFinite(polyT) && Number.isFinite(kalshiT))
          ? Math.abs(polyT - kalshiT) / 60_000
          : 0;
        const tol = offsetTolerance(p.canonical.resolution_type);
        if (!pair.sameResolutionWindow && offsetMin > tol * 4) {
          log.skip(`pass4_${pair.id}_offset_too_large`, {
            offset_min: Math.round(offsetMin), tolerance_min: tol,
          });
          continue;
        }

        const polyV24 = Number(p.market.volume24hr || 0);
        const kalshiV24 = Number(k.market.volume_24h_fp || 0);
        if (polyV24 === 0 || kalshiV24 === 0) {
          log.skip(`pass4_${pair.id}_dead_leg`, {
            poly_v24: polyV24, kalshi_v24: kalshiV24,
          });
          continue;
        }
        if (polyV24 < 100 && kalshiV24 < 100) {
          log.skip(`pass4_${pair.id}_low_volume`, {
            poly_v24: polyV24, kalshi_v24: kalshiV24,
          });
          continue;
        }

        let cheapItem, expItem, cheapPlatform, expPlatform;
        if (polyYes < kalshiYes) {
          cheapItem = p; expItem = k;
          cheapPlatform = 'polymarket'; expPlatform = 'kalshi';
        } else {
          cheapItem = k; expItem = p;
          cheapPlatform = 'kalshi'; expPlatform = 'polymarket';
        }
        const cheapLeg = cheapPlatform === 'polymarket'
          ? polyLeg({ event: cheapItem.event, market: cheapItem.market, side: 'YES', yesPrice: cheapItem.yes })
          : kalshiLeg({ market: cheapItem.market, side: 'YES', yesPrice: cheapItem.yes });
        const expLeg = expPlatform === 'polymarket'
          ? polyLeg({ event: expItem.event, market: expItem.market, side: 'NO', yesPrice: expItem.yes })
          : kalshiLeg({ market: expItem.market, side: 'NO', yesPrice: expItem.yes });
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
        // sameResolutionWindow asserts settlement equivalence — don't flag
        // offset_warning at all. Otherwise flag (and downgrade) if offset
        // exceeds soft tolerance, identical to Pass 5.
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

        // Curated tag — distinguishes from Pass 5 emissions in the dashboard
        // and surfaces the operator-validated context.
        if (!flags.includes('curated_pair')) flags.push('curated_pair');

        // If we're NOT asserting same resolution window, behave like Pass 5
        // for non-strict matches — cap at Tier 2.
        if (!pair.sameResolutionWindow) {
          tier = Math.max(tier, 2);
          if (!flags.includes('resolution_mismatch')) flags.push('resolution_mismatch');
        }

        const opp = {
          id: stableId({
            pair,
            polyCanonical: p.canonical,
            polyId: p.market.id,
            kalshiId: k.market.ticker,
          }),
          tier,
          type: 'cross_platform',
          summary: summarize({
            pair,
            polyCanonical: p.canonical,
            kalshiCanonical: k.canonical,
            polyYes,
            kalshiYes,
          }),
          underlying: p.canonical.underlying,
          // Use Poly's resolution_date as the canonical date; both venues are
          // asserted to resolve to the same observable, so either is fine.
          resolution_date: p.canonical.resolution_date,
          resolution_type: p.canonical.resolution_type,
          legs,
          edge_gross_pct: grossEdgePct,
          edge_net_estimate_pct: netEdgePct,
          max_executable_size_per_leg_usd: Math.round(minDepth),
          edge_net_per_dollar: edgeNetPerDollar,
          weakest_link_summary: weakestLink({
            pair, minDepth, netEdgePct, offsetMin,
            resolutionType: p.canonical.resolution_type, daysToResolution,
          }),
          confidence_flags: flags,
          curated_pair_id: pair.id,
        };

        opportunities.push(opp);
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
