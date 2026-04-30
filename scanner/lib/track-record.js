// scanner/lib/track-record.js
//
// Aggregate "did the spreads we flagged actually behave like inefficiencies?"
// Built on the same history JSONL files persistence reads — no new data
// source. For each opp we've ever observed in the lookback window:
//   • If still in the latest scan → classify the spread evolution
//     (closed_substantially / tightened / stable / widened)
//   • If gone → left_feed (could be: resolved, leg delisted, or spread fell
//     below our 2pp emit threshold — we don't disambiguate here. Settlement
//     P&L is a separate v1.5 layer that cross-references resolved markets.)
//
// The output is rolled into the top level of opportunities.json so the
// frontend can render a small honesty panel above the tier sections.
//
// Honesty caveats baked in:
//   • States are observational, not financial — "closed_substantially" means
//     "the spread we flagged shrank a lot," NOT "we made money." A spread
//     can close without the trade clearing (depth, fees, latency).
//   • left_feed is intentionally NOT called "resolved" or "closed" —
//     conflating those would lie about what we know.

// Spread-evolution classifier. Operates on (firstGrossPct, lastGrossPct).
// Returns one of the AMONG_ACTIVE_STATES strings.
export const AMONG_ACTIVE_STATES = ['closed_substantially', 'tightened', 'stable', 'widened'];

// Why-did-this-leave-the-feed classifier. Order is significant — we check the
// most-decisive signals first.
export const LEFT_FEED_REASONS = ['leg_expired', 'leg_delisted', 'spread_closed', 'unknown'];

// Given the LAST sample we have for an opp + the current scan's market-ID
// sets + nowMs, return one of LEFT_FEED_REASONS.
//
//   leg_expired:    sample.resolution_date is in the past — the underlying
//                   market settled, opp can't physically still exist.
//   leg_delisted:   any leg's market_id is missing from the current fetch.
//                   That's almost always "the venue removed/expired the
//                   market" rather than a network blip.
//   spread_closed:  all legs still alive in fetch, but no opp emitted in the
//                   latest scan — means the spread fell below our 2pp emit
//                   threshold (or one leg now has dead volume).
//   unknown:        no leg_ids on the sample (history written before this
//                   field existed) and resolution_date didn't disqualify.
export function classifyLeftFeedReason(lastSample, currentMarketIds, nowMs = Date.now()) {
  if (!lastSample) return 'unknown';

  // resolution_date can disqualify even without leg info.
  if (lastSample.resolution_date) {
    const t = Date.parse(lastSample.resolution_date);
    if (Number.isFinite(t) && t < nowMs) return 'leg_expired';
  }

  const legs = Array.isArray(lastSample.leg_ids) ? lastSample.leg_ids : [];
  if (legs.length === 0) return 'unknown';

  if (currentMarketIds && (currentMarketIds.poly || currentMarketIds.kalshi)) {
    for (const leg of legs) {
      const set = leg.platform === 'polymarket'
        ? currentMarketIds.poly
        : leg.platform === 'kalshi'
          ? currentMarketIds.kalshi
          : null;
      if (!set) continue; // no fetch context for this platform — give up gracefully
      if (!set.has(String(leg.market_id))) return 'leg_delisted';
    }
    // All legs still in fetch — opp gone but its markets are alive.
    return 'spread_closed';
  }

  // No fetch context provided (caller didn't pass currentMarketIds).
  return 'unknown';
}

export function classifySpreadEvolution(firstGrossPct, lastGrossPct) {
  if (!Number.isFinite(firstGrossPct) || firstGrossPct <= 0) return 'stable';
  if (!Number.isFinite(lastGrossPct)) return 'stable';
  const ratio = lastGrossPct / firstGrossPct;
  if (ratio < 0.5) return 'closed_substantially';
  if (ratio < 0.8) return 'tightened';
  if (ratio > 1.2) return 'widened';
  return 'stable';
}

function median(values) {
  if (!values.length) return null;
  const sorted = values.slice().sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[mid];
  return (sorted[mid - 1] + sorted[mid]) / 2;
}

// Build the aggregate. `historyById` is the Map<id, samples[]> returned by
// loadHistory(). `currentLiveIds` is a Set<string> of opportunity IDs in the
// latest scan. `currentMarketIds` (optional) is { poly: Set, kalshi: Set } of
// market IDs present in the latest fetch — used to classify why each
// left_feed opp is gone. `nowMs` is overridable for tests.
export function computeTrackRecord(historyById, currentLiveIds, opts = {}) {
  const {
    lookbackDays = 14,
    currentMarketIds = null,
    nowMs = Date.now(),
  } = opts;
  const liveSet = currentLiveIds instanceof Set ? currentLiveIds : new Set(currentLiveIds || []);
  const totalSeen = historyById.size;

  if (totalSeen === 0) {
    return {
      lookback_days: lookbackDays,
      total_observed: 0,
      active: 0,
      left_feed: 0,
      among_active: { closed_substantially: 0, tightened: 0, stable: 0, widened: 0 },
      among_active_pct: { closed_substantially: 0, tightened: 0, stable: 0, widened: 0 },
      left_feed_reasons: { leg_expired: 0, leg_delisted: 0, spread_closed: 0, unknown: 0 },
      median_lifetime_hours: null,
      by_tier: { 1: emptyTierStats(), 2: emptyTierStats(), 3: emptyTierStats() },
    };
  }

  // Per-opportunity rollup.
  let active = 0, leftFeed = 0;
  const amongActive = { closed_substantially: 0, tightened: 0, stable: 0, widened: 0 };
  const leftFeedReasons = { leg_expired: 0, leg_delisted: 0, spread_closed: 0, unknown: 0 };
  const lifetimesHours = [];
  const byTier = { 1: emptyTierStats(), 2: emptyTierStats(), 3: emptyTierStats() };

  for (const [id, samples] of historyById.entries()) {
    if (!Array.isArray(samples) || samples.length === 0) continue;
    const ordered = samples.slice().sort((a, b) => Date.parse(a.ts) - Date.parse(b.ts));
    const first = ordered[0];
    const last = ordered[ordered.length - 1];

    const firstMs = Date.parse(first.ts);
    const lastMs = Date.parse(last.ts);
    if (Number.isFinite(firstMs) && Number.isFinite(lastMs) && lastMs >= firstMs) {
      lifetimesHours.push((lastMs - firstMs) / 3600_000);
    }

    // Tier bucket — use the LATEST tier for the by_tier rollup. An opp's tier
    // can drift (e.g. depth shrinks, recency expires) but the recent tier
    // best describes "what is this card showing today?"
    const tierKey = [1, 2, 3].includes(last.tier) ? last.tier : null;

    if (liveSet.has(id)) {
      active++;
      const state = classifySpreadEvolution(first.edge_gross_pct, last.edge_gross_pct);
      amongActive[state]++;
      if (tierKey) {
        byTier[tierKey].active++;
        byTier[tierKey].among_active[state]++;
      }
    } else {
      leftFeed++;
      const reason = classifyLeftFeedReason(last, currentMarketIds, nowMs);
      leftFeedReasons[reason] = (leftFeedReasons[reason] || 0) + 1;
      if (tierKey) {
        byTier[tierKey].left_feed++;
        byTier[tierKey].left_feed_reasons[reason] = (byTier[tierKey].left_feed_reasons[reason] || 0) + 1;
      }
    }

    if (tierKey) byTier[tierKey].total_observed++;
  }

  const amongActivePct = {};
  for (const k of AMONG_ACTIVE_STATES) {
    amongActivePct[k] = active > 0 ? +(amongActive[k] / active * 100).toFixed(1) : 0;
  }

  return {
    lookback_days: lookbackDays,
    total_observed: totalSeen,
    active,
    left_feed: leftFeed,
    among_active: amongActive,
    among_active_pct: amongActivePct,
    left_feed_reasons: leftFeedReasons,
    median_lifetime_hours: lifetimesHours.length ? +median(lifetimesHours).toFixed(2) : null,
    by_tier: byTier,
  };
}

function emptyTierStats() {
  return {
    total_observed: 0,
    active: 0,
    left_feed: 0,
    among_active: { closed_substantially: 0, tightened: 0, stable: 0, widened: 0 },
    left_feed_reasons: { leg_expired: 0, leg_delisted: 0, spread_closed: 0, unknown: 0 },
  };
}
