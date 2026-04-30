// Hand-crafted unit tests for track-record.js.
// Run: node scanner/test-track-record.js

import {
  computeTrackRecord,
  classifySpreadEvolution,
  classifyLeftFeedReason,
  AMONG_ACTIVE_STATES,
  LEFT_FEED_REASONS,
} from './lib/track-record.js';

let pass = 0, fail = 0;
function assert(cond, msg) {
  if (cond) { pass++; console.log(`  ✓ ${msg}`); }
  else { fail++; console.log(`  ✗ ${msg}`); }
}

// ── classifySpreadEvolution ─────────────────────────────────────────────────
console.log('Test 1: classifySpreadEvolution — closed_substantially (>50% drop)');
{
  assert(classifySpreadEvolution(5, 2.4) === 'closed_substantially', '5 → 2.4 (ratio 0.48)');
  assert(classifySpreadEvolution(10, 4) === 'closed_substantially', '10 → 4 (ratio 0.4)');
  assert(classifySpreadEvolution(10, 0) === 'closed_substantially', '10 → 0 (ratio 0)');
}

console.log('\nTest 2: classifySpreadEvolution — tightened (20-50% drop)');
{
  assert(classifySpreadEvolution(5, 3) === 'tightened', '5 → 3 (ratio 0.6)');
  assert(classifySpreadEvolution(10, 7.9) === 'tightened', '10 → 7.9 (ratio 0.79)');
}

console.log('\nTest 3: classifySpreadEvolution — stable (±20%)');
{
  assert(classifySpreadEvolution(5, 5) === 'stable', '5 → 5');
  assert(classifySpreadEvolution(5, 4.1) === 'stable', '5 → 4.1 (ratio 0.82)');
  assert(classifySpreadEvolution(5, 5.9) === 'stable', '5 → 5.9 (ratio 1.18)');
}

console.log('\nTest 4: classifySpreadEvolution — widened (>20% rise)');
{
  assert(classifySpreadEvolution(5, 6.5) === 'widened', '5 → 6.5 (ratio 1.3)');
  assert(classifySpreadEvolution(5, 10) === 'widened', '5 → 10 (ratio 2)');
}

console.log('\nTest 5: classifySpreadEvolution — defensive on bad input');
{
  assert(classifySpreadEvolution(0, 2) === 'stable', 'first=0 → stable (avoids div-by-zero)');
  assert(classifySpreadEvolution(NaN, 2) === 'stable', 'first=NaN → stable');
  assert(classifySpreadEvolution(5, NaN) === 'stable', 'last=NaN → stable');
  assert(classifySpreadEvolution(-1, 2) === 'stable', 'negative first → stable');
}

// ── computeTrackRecord ──────────────────────────────────────────────────────
console.log('\nTest 6: computeTrackRecord — empty history → zeros');
{
  const r = computeTrackRecord(new Map(), new Set());
  assert(r.total_observed === 0, 'total_observed 0');
  assert(r.active === 0 && r.left_feed === 0, 'active + left_feed both 0');
  assert(r.median_lifetime_hours === null, 'median is null on empty');
  for (const k of AMONG_ACTIVE_STATES) {
    assert(r.among_active[k] === 0, `${k} count 0`);
    assert(r.among_active_pct[k] === 0, `${k} pct 0`);
  }
}

console.log('\nTest 7: computeTrackRecord — one live opp, single sample → stable');
{
  const h = new Map();
  h.set('a', [{ ts: '2026-04-30T12:00:00Z', tier: 1, edge_gross_pct: 5 }]);
  const r = computeTrackRecord(h, new Set(['a']));
  assert(r.total_observed === 1, 'total_observed 1');
  assert(r.active === 1, 'active 1');
  assert(r.left_feed === 0, 'left_feed 0');
  assert(r.among_active.stable === 1, 'classified stable (single sample)');
  assert(r.among_active_pct.stable === 100, 'pct stable 100');
}

console.log('\nTest 8: computeTrackRecord — distinct evolutions across opps');
{
  const h = new Map();
  // closed_substantially
  h.set('closed', [
    { ts: '2026-04-30T08:00:00Z', tier: 2, edge_gross_pct: 10 },
    { ts: '2026-04-30T12:00:00Z', tier: 2, edge_gross_pct: 4 },
  ]);
  // tightened
  h.set('tight', [
    { ts: '2026-04-30T08:00:00Z', tier: 2, edge_gross_pct: 10 },
    { ts: '2026-04-30T12:00:00Z', tier: 2, edge_gross_pct: 7 },
  ]);
  // stable
  h.set('stable', [
    { ts: '2026-04-30T08:00:00Z', tier: 3, edge_gross_pct: 5 },
    { ts: '2026-04-30T12:00:00Z', tier: 3, edge_gross_pct: 5.2 },
  ]);
  // widened
  h.set('wide', [
    { ts: '2026-04-30T08:00:00Z', tier: 2, edge_gross_pct: 5 },
    { ts: '2026-04-30T12:00:00Z', tier: 1, edge_gross_pct: 8 },
  ]);
  // left_feed
  h.set('gone', [
    { ts: '2026-04-29T08:00:00Z', tier: 3, edge_gross_pct: 5 },
    { ts: '2026-04-29T20:00:00Z', tier: 3, edge_gross_pct: 4.8 },
  ]);
  const live = new Set(['closed', 'tight', 'stable', 'wide']);
  const r = computeTrackRecord(h, live);
  assert(r.total_observed === 5, 'total_observed 5');
  assert(r.active === 4, 'active 4');
  assert(r.left_feed === 1, 'left_feed 1');
  assert(r.among_active.closed_substantially === 1, '1 closed_substantially');
  assert(r.among_active.tightened === 1, '1 tightened');
  assert(r.among_active.stable === 1, '1 stable');
  assert(r.among_active.widened === 1, '1 widened');
  assert(r.among_active_pct.closed_substantially === 25, '25% closed (1/4)');
  assert(r.among_active_pct.widened === 25, '25% widened (1/4)');
}

console.log('\nTest 9: computeTrackRecord — median lifetime');
{
  const h = new Map();
  h.set('a', [
    { ts: '2026-04-30T08:00:00Z', tier: 1, edge_gross_pct: 5 },
    { ts: '2026-04-30T09:00:00Z', tier: 1, edge_gross_pct: 5 },
  ]);
  h.set('b', [
    { ts: '2026-04-30T08:00:00Z', tier: 1, edge_gross_pct: 5 },
    { ts: '2026-04-30T12:00:00Z', tier: 1, edge_gross_pct: 5 },
  ]);
  h.set('c', [
    { ts: '2026-04-30T08:00:00Z', tier: 1, edge_gross_pct: 5 },
    { ts: '2026-04-30T16:00:00Z', tier: 1, edge_gross_pct: 5 },
  ]);
  const r = computeTrackRecord(h, new Set(['a', 'b', 'c']));
  assert(r.median_lifetime_hours === 4, `median 4h (got ${r.median_lifetime_hours})`);
}

console.log('\nTest 10: computeTrackRecord — even-count median (avg of middle two)');
{
  const h = new Map();
  h.set('a', [
    { ts: '2026-04-30T08:00:00Z', edge_gross_pct: 5 },
    { ts: '2026-04-30T10:00:00Z', edge_gross_pct: 5 },
  ]);
  h.set('b', [
    { ts: '2026-04-30T08:00:00Z', edge_gross_pct: 5 },
    { ts: '2026-04-30T12:00:00Z', edge_gross_pct: 5 },
  ]);
  h.set('c', [
    { ts: '2026-04-30T08:00:00Z', edge_gross_pct: 5 },
    { ts: '2026-04-30T14:00:00Z', edge_gross_pct: 5 },
  ]);
  h.set('d', [
    { ts: '2026-04-30T08:00:00Z', edge_gross_pct: 5 },
    { ts: '2026-04-30T16:00:00Z', edge_gross_pct: 5 },
  ]);
  const r = computeTrackRecord(h, new Set());
  // lifetimes: 2, 4, 6, 8 → median = (4+6)/2 = 5
  assert(r.median_lifetime_hours === 5, `median 5h (got ${r.median_lifetime_hours})`);
}

console.log('\nTest 11: computeTrackRecord — by_tier rollup uses latest tier');
{
  const h = new Map();
  h.set('promoted', [
    { ts: '2026-04-30T08:00:00Z', tier: 3, edge_gross_pct: 5 },
    { ts: '2026-04-30T12:00:00Z', tier: 1, edge_gross_pct: 12 }, // promoted
  ]);
  h.set('always-t2', [
    { ts: '2026-04-30T08:00:00Z', tier: 2, edge_gross_pct: 5 },
    { ts: '2026-04-30T12:00:00Z', tier: 2, edge_gross_pct: 5 },
  ]);
  const r = computeTrackRecord(h, new Set(['promoted', 'always-t2']));
  assert(r.by_tier[1].total_observed === 1, 'tier 1 has the promoted opp');
  assert(r.by_tier[2].total_observed === 1, 'tier 2 has the steady opp');
  assert(r.by_tier[3].total_observed === 0, 'tier 3 not credited (latest tier wins)');
  assert(r.by_tier[1].among_active.widened === 1, 'tier 1 promoted opp classified widened');
}

console.log('\nTest 12: computeTrackRecord — opp in history but no live samples → left_feed');
{
  const h = new Map();
  h.set('orphan', [
    { ts: '2026-04-29T08:00:00Z', tier: 2, edge_gross_pct: 5 },
  ]);
  const r = computeTrackRecord(h, new Set());
  assert(r.active === 0, 'active 0');
  assert(r.left_feed === 1, 'left_feed 1');
  assert(r.among_active.stable === 0, 'no among_active classification for left_feed opps');
}

console.log('\nTest 13: computeTrackRecord — pct sums to ~100 across active states');
{
  const h = new Map();
  for (let i = 0; i < 7; i++) {
    h.set(`a${i}`, [{ ts: '2026-04-30T08:00:00Z', tier: 2, edge_gross_pct: 5 }]);
  }
  const r = computeTrackRecord(h, new Set(['a0','a1','a2','a3','a4','a5','a6']));
  // All single-sample stable → 100% stable
  const sum = AMONG_ACTIVE_STATES.reduce((s, k) => s + r.among_active_pct[k], 0);
  assert(Math.abs(sum - 100) < 0.5, `pct sum ≈ 100 (got ${sum})`);
}

console.log('\nTest 14: computeTrackRecord — lookback_days passes through');
{
  const r = computeTrackRecord(new Map(), new Set(), { lookbackDays: 7 });
  assert(r.lookback_days === 7, 'lookback_days reflected from caller');
}

// ── classifyLeftFeedReason ──────────────────────────────────────────────────
const NOW = Date.parse('2026-04-30T15:00:00Z');

console.log('\nTest 15: classifyLeftFeedReason — null sample → unknown');
{
  assert(classifyLeftFeedReason(null, null, NOW) === 'unknown', 'null sample');
}

console.log('\nTest 16: classifyLeftFeedReason — past resolution_date → leg_expired');
{
  const sample = {
    resolution_date: '2026-04-29',
    leg_ids: [{ platform: 'polymarket', market_id: 'p1' }],
  };
  // legs alive in fetch but date is past
  const cur = { poly: new Set(['p1']), kalshi: new Set() };
  assert(classifyLeftFeedReason(sample, cur, NOW) === 'leg_expired', 'date past — leg_expired wins');
}

console.log('\nTest 17: classifyLeftFeedReason — leg missing → leg_delisted');
{
  const sample = {
    resolution_date: '2027-01-01',
    leg_ids: [
      { platform: 'polymarket', market_id: 'p1' },
      { platform: 'kalshi', market_id: 'KX-T1' },
    ],
  };
  const cur = { poly: new Set(['p1']), kalshi: new Set() };
  assert(classifyLeftFeedReason(sample, cur, NOW) === 'leg_delisted', 'kalshi leg gone');
}

console.log('\nTest 18: classifyLeftFeedReason — all legs alive → spread_closed');
{
  const sample = {
    resolution_date: '2027-01-01',
    leg_ids: [
      { platform: 'polymarket', market_id: 'p1' },
      { platform: 'kalshi', market_id: 'KX-T1' },
    ],
  };
  const cur = { poly: new Set(['p1']), kalshi: new Set(['KX-T1']) };
  assert(classifyLeftFeedReason(sample, cur, NOW) === 'spread_closed', 'both alive → closed');
}

console.log('\nTest 19: classifyLeftFeedReason — backwards compat (no leg_ids) → unknown');
{
  const sample = {
    resolution_date: '2027-01-01',
    // legacy: no leg_ids field
  };
  const cur = { poly: new Set(), kalshi: new Set() };
  assert(classifyLeftFeedReason(sample, cur, NOW) === 'unknown', 'old sample → unknown');
}

console.log('\nTest 20: classifyLeftFeedReason — no fetch context → unknown');
{
  const sample = {
    resolution_date: '2027-01-01',
    leg_ids: [{ platform: 'polymarket', market_id: 'p1' }],
  };
  // No currentMarketIds passed
  assert(classifyLeftFeedReason(sample, null, NOW) === 'unknown', 'no fetch ctx → unknown');
}

console.log('\nTest 21: classifyLeftFeedReason — poly_sum (all-poly legs) variant');
{
  const sample = {
    resolution_date: '2027-01-01',
    leg_ids: [
      { platform: 'polymarket', market_id: 'p1' },
      { platform: 'polymarket', market_id: 'p2' },
      { platform: 'polymarket', market_id: 'p3' },
    ],
  };
  const cur = { poly: new Set(['p1', 'p3']), kalshi: new Set() };
  assert(classifyLeftFeedReason(sample, cur, NOW) === 'leg_delisted', 'p2 missing → delisted');
}

// ── computeTrackRecord with left_feed_reasons ───────────────────────────────
console.log('\nTest 22: computeTrackRecord — left_feed_reasons populated');
{
  const h = new Map();
  // 1. spread_closed: legs alive
  h.set('closed', [{
    ts: '2026-04-29T08:00:00Z', tier: 2, edge_gross_pct: 5,
    leg_ids: [{ platform: 'polymarket', market_id: 'pA' }, { platform: 'kalshi', market_id: 'kA' }],
    resolution_date: '2027-01-01',
  }]);
  // 2. leg_delisted: kalshi leg gone
  h.set('delist', [{
    ts: '2026-04-29T08:00:00Z', tier: 2, edge_gross_pct: 5,
    leg_ids: [{ platform: 'polymarket', market_id: 'pB' }, { platform: 'kalshi', market_id: 'kGONE' }],
    resolution_date: '2027-01-01',
  }]);
  // 3. leg_expired: date past
  h.set('expire', [{
    ts: '2026-04-29T08:00:00Z', tier: 2, edge_gross_pct: 5,
    leg_ids: [{ platform: 'polymarket', market_id: 'pC' }],
    resolution_date: '2026-04-29',
  }]);
  // 4. unknown: legacy sample
  h.set('legacy', [{
    ts: '2026-04-29T08:00:00Z', tier: 2, edge_gross_pct: 5,
  }]);
  const cur = {
    poly: new Set(['pA', 'pB', 'pC']),
    kalshi: new Set(['kA']),
  };
  const r = computeTrackRecord(h, new Set(), {
    currentMarketIds: cur, nowMs: NOW,
  });
  assert(r.left_feed === 4, 'all 4 left feed');
  assert(r.left_feed_reasons.spread_closed === 1, '1 spread_closed');
  assert(r.left_feed_reasons.leg_delisted === 1, '1 leg_delisted');
  assert(r.left_feed_reasons.leg_expired === 1, '1 leg_expired');
  assert(r.left_feed_reasons.unknown === 1, '1 unknown');
}

console.log('\nTest 23: computeTrackRecord — without currentMarketIds, all left_feed are unknown (with leg_ids) or expired (date)');
{
  const h = new Map();
  h.set('a', [{
    ts: '2026-04-29T08:00:00Z', tier: 2, edge_gross_pct: 5,
    leg_ids: [{ platform: 'polymarket', market_id: 'p1' }],
    resolution_date: '2027-01-01',
  }]);
  h.set('b', [{
    ts: '2026-04-29T08:00:00Z', tier: 2, edge_gross_pct: 5,
    resolution_date: '2026-04-29', // past
  }]);
  const r = computeTrackRecord(h, new Set(), { nowMs: NOW });
  assert(r.left_feed_reasons.unknown === 1, '1 unknown (no fetch ctx)');
  assert(r.left_feed_reasons.leg_expired === 1, '1 expired (date past)');
}

console.log('\nTest 24: computeTrackRecord — by_tier carries left_feed_reasons');
{
  const h = new Map();
  h.set('t2-closed', [{
    ts: '2026-04-29T08:00:00Z', tier: 2, edge_gross_pct: 5,
    leg_ids: [{ platform: 'polymarket', market_id: 'pA' }],
    resolution_date: '2027-01-01',
  }]);
  h.set('t3-expired', [{
    ts: '2026-04-29T08:00:00Z', tier: 3, edge_gross_pct: 5,
    leg_ids: [{ platform: 'polymarket', market_id: 'pB' }],
    resolution_date: '2026-04-29',
  }]);
  const cur = { poly: new Set(['pA', 'pB']), kalshi: new Set() };
  const r = computeTrackRecord(h, new Set(), { currentMarketIds: cur, nowMs: NOW });
  assert(r.by_tier[2].left_feed_reasons.spread_closed === 1, 'tier 2 spread_closed');
  assert(r.by_tier[3].left_feed_reasons.leg_expired === 1, 'tier 3 leg_expired');
}

console.log(`\n${pass}/${pass + fail} tests passed`);
process.exit(fail > 0 ? 1 : 0);
