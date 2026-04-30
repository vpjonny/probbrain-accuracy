// Hand-crafted unit tests for Pass 1.
// Run: node scanner/test-pass1.js
//
// Per spec sanity tests #1, #2, #5, #6.

import { runPass1 } from './passes/pass1-poly-sum.js';
import { createLogger } from './lib/log.js';

let pass = 0;
let fail = 0;
function assert(cond, msg) {
  if (cond) { pass++; console.log(`  ✓ ${msg}`); }
  else { fail++; console.log(`  ✗ ${msg}`); }
}

const log = createLogger({ verbose: false });

// ── Test 1: empty input → empty output ───────────────────────────────────────
console.log('Test 1: empty events');
{
  const r = await runPass1([], log);
  assert(r.opportunities.length === 0, 'no opportunities emitted');
  assert(r.stats.poly_markets_scanned === 0, 'zero markets scanned');
}

// ── Test 2: hand-crafted sum=1.05, two negRisk markets → emits opportunity ──
console.log('\nTest 2: sum=1.05 sum-violation candidate');
{
  const event = {
    id: 'test-1',
    slug: 'test-event-105',
    title: 'Test event sum=1.05',
    negRisk: true,
    endDate: new Date(Date.now() + 30 * 86400_000).toISOString(),
    markets: [
      { id: 'm1', slug: 'a', outcomePrices: '["0.65","0.35"]', liquidityNum: 5000,
        volume24hr: 12000, lastTradeTime: new Date().toISOString(),
        active: true, closed: false },
      { id: 'm2', slug: 'b', outcomePrices: '["0.40","0.60"]', liquidityNum: 4000,
        volume24hr: 9000, lastTradeTime: new Date().toISOString(),
        active: true, closed: false },
    ],
  };
  const r = await runPass1([event], log);
  assert(r.opportunities.length === 1, 'one opportunity emitted');
  const o = r.opportunities[0];
  assert(o.type === 'poly_sum_violation', 'type is poly_sum_violation');
  assert(Math.abs(o.edge_gross_pct - 5.0) < 0.01, `edge_gross_pct ≈ 5.0 (got ${o.edge_gross_pct})`);
  assert(o.summary.includes('buy-all-NO'), 'summary names buy-all-NO strategy (sum > 1)');
  assert(o.legs.length === 2, 'two legs');
  assert(o.legs.every(l => l.platform === 'polymarket'), 'both legs polymarket');
  assert(o.legs.every(l => l.side === 'YES'), 'both legs YES side');
}

// ── Test 3: hand-crafted sum=0.93 → buy-all-YES ──────────────────────────────
console.log('\nTest 3: sum=0.93 buy-all-YES');
{
  const event = {
    id: 'test-2',
    slug: 'test-event-093',
    title: 'Test event sum=0.93',
    negRisk: true,
    endDate: new Date(Date.now() + 7 * 86400_000).toISOString(),
    markets: [
      { id: 'm1', outcomePrices: '["0.55","0.45"]', liquidityNum: 5000, volume24hr: 12000,
        lastTradeTime: new Date().toISOString(), active: true, closed: false },
      { id: 'm2', outcomePrices: '["0.38","0.62"]', liquidityNum: 4000, volume24hr: 9000,
        lastTradeTime: new Date().toISOString(), active: true, closed: false },
    ],
  };
  const r = await runPass1([event], log);
  assert(r.opportunities.length === 1, 'one opportunity emitted');
  const o = r.opportunities[0];
  assert(Math.abs(o.edge_gross_pct - 7.0) < 0.01, `edge_gross_pct ≈ 7.0 (got ${o.edge_gross_pct})`);
  assert(o.summary.includes('buy-all-YES'), 'summary names buy-all-YES strategy (sum < 1)');
}

// ── Test 4: violation within threshold → no emit ─────────────────────────────
console.log('\nTest 4: |sum - 1| ≤ 0.015 → suppressed');
{
  const event = {
    id: 'test-3', negRisk: true, slug: 'tight',
    endDate: new Date(Date.now() + 30 * 86400_000).toISOString(),
    markets: [
      { id: 'm1', outcomePrices: '["0.50","0.50"]', liquidityNum: 5000, volume24hr: 1000,
        lastTradeTime: new Date().toISOString(), active: true, closed: false },
      { id: 'm2', outcomePrices: '["0.51","0.49"]', liquidityNum: 4000, volume24hr: 1000,
        lastTradeTime: new Date().toISOString(), active: true, closed: false },
    ],
  };
  const r = await runPass1([event], log);
  assert(r.opportunities.length === 0, 'tight sum not emitted (violation 1.0pp under 1.5pp threshold)');
}

// ── Test 5: stale leg (>4h on a daily market) → Tier 3 with stale_price ─────
console.log('\nTest 5: stale leg → Tier 3');
{
  const sixHoursAgo = new Date(Date.now() - 6 * 3600_000).toISOString();
  const fresh = new Date().toISOString();
  const event = {
    id: 'test-4', negRisk: true, slug: 'stale-leg', title: 'daily market',
    endDate: new Date(Date.now() + 1 * 86400_000).toISOString(), // tomorrow → daily
    markets: [
      { id: 'm1', outcomePrices: '["0.65","0.35"]', liquidityNum: 5000, volume24hr: 5000,
        lastTradeTime: sixHoursAgo, active: true, closed: false },
      { id: 'm2', outcomePrices: '["0.42","0.58"]', liquidityNum: 4000, volume24hr: 5000,
        lastTradeTime: fresh, active: true, closed: false },
    ],
  };
  const r = await runPass1([event], log);
  assert(r.opportunities.length === 1, 'opportunity emitted');
  const o = r.opportunities[0];
  assert(o.tier === 3, `tier === 3 (got ${o.tier})`);
  assert(o.confidence_flags.includes('stale_price'), 'has stale_price flag');
}

// ── Test 6: all-dead event (no v24, no last trade) → skipped ────────────────
console.log('\nTest 6: dead market filter');
{
  const event = {
    id: 'test-5', negRisk: true, slug: 'dead',
    endDate: new Date(Date.now() + 30 * 86400_000).toISOString(),
    markets: [
      { id: 'm1', outcomePrices: '["0.65","0.35"]', liquidityNum: 0, volume24hr: 0,
        lastTradeTime: null, active: true, closed: false },
      { id: 'm2', outcomePrices: '["0.42","0.58"]', liquidityNum: 0, volume24hr: 0,
        lastTradeTime: null, active: true, closed: false },
    ],
  };
  const r = await runPass1([event], log);
  assert(r.opportunities.length === 0, 'dead event skipped');
}

// ── Test 7: violation > 10pp → suppressed (likely structural artifact) ──────
console.log('\nTest 7: huge violation > 10pp suppressed');
{
  const event = {
    id: 'test-6', negRisk: true, slug: 'open-universe', title: 'next bond actor',
    endDate: new Date(Date.now() + 30 * 86400_000).toISOString(),
    markets: Array.from({ length: 5 }, (_, i) => ({
      id: `m${i}`, outcomePrices: '["0.10","0.90"]', liquidityNum: 1000, volume24hr: 100,
      lastTradeTime: new Date().toISOString(), active: true, closed: false,
    })),
  };
  // sum = 0.50 — well outside MAX_REPORTABLE_VIOLATION
  const r = await runPass1([event], log);
  assert(r.opportunities.length === 0, 'huge violation suppressed (likely open-universe artifact)');
}

console.log(`\n${pass}/${pass + fail} tests passed`);
process.exit(fail > 0 ? 1 : 0);
