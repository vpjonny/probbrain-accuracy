// Hand-crafted unit tests for Passes 2 + 3 (within-platform monotonicity).
// Run: node scanner/test-pass2-pass3.js

import { runPass2 } from './passes/pass2-poly-monotonicity.js';
import { runPass3 } from './passes/pass3-kalshi-monotonicity.js';
import { normalizePolymarket } from './normalize/polymarket.js';
import { normalizeKalshi } from './normalize/kalshi.js';
import { createLogger } from './lib/log.js';

let pass = 0, fail = 0;
function assert(cond, msg) {
  if (cond) { pass++; console.log(`  ✓ ${msg}`); }
  else { fail++; console.log(`  ✗ ${msg}`); }
}
const log = createLogger({ verbose: false });

// ── normalize unit tests ─────────────────────────────────────────────────────
console.log('Test 1: normalizePolymarket — BTC above $100k');
{
  const event = {
    slug: 'btc-100k-may-31', title: 'Will Bitcoin reach $100k by May 31?',
    category: 'crypto', tags: [], endDate: '2026-05-31T12:00:00Z',
  };
  const market = { id: 'm1', slug: 'btc-100k', question: 'Will BTC be above $100,000 on May 31?', groupItemTitle: '$100,000', endDate: '2026-05-31T12:00:00Z' };
  const r = normalizePolymarket(market, event);
  assert(!r.skip, 'normalized (no skip)');
  assert(r.underlying === 'BTC', `underlying === BTC (got ${r.underlying})`);
  assert(r.direction === 'above', `direction === above (got ${r.direction})`);
  assert(r.strike === 100000, `strike === 100000 (got ${r.strike})`);
  assert(r.resolution_date === '2026-05-31', `resolution_date === 2026-05-31 (got ${r.resolution_date})`);
  assert(r.resolution_type === 'monthly', `resolution_type === monthly (got ${r.resolution_type})`);
}

console.log('\nTest 2: normalizePolymarket — non-tracked underlying skipped');
{
  const event = { slug: 'arsenal-vs-chelsea', title: 'Arsenal vs Chelsea winner?', endDate: '2026-05-15T12:00:00Z' };
  const market = { id: 'm1', question: 'Will Arsenal win above 2 goals?' };
  const r = normalizePolymarket(market, event);
  assert(r.skip === true, 'skipped');
  assert(r.reason === 'underlying_not_in_dict', 'reason === underlying_not_in_dict');
}

console.log('\nTest 3: normalizeKalshi — KXBTC threshold');
{
  const market = {
    ticker: 'KXBTC-26MAY31-T100000', event_ticker: 'KXBTC-26MAY31',
    _series_ticker_hint: 'KXBTC',
    yes_sub_title: '$100,000 or above', strike_type: 'greater',
    expiration_time: '2026-05-31T20:00:00Z', close_time: '2026-05-31T20:00:00Z',
    open_time: '2026-05-30T00:00:00Z',
  };
  const r = normalizeKalshi(market);
  assert(!r.skip, 'normalized');
  assert(r.underlying === 'BTC', `underlying === BTC (got ${r.underlying})`);
  assert(r.direction === 'above', `direction === above`);
  assert(r.strike === 100000, `strike === 100000 (got ${r.strike})`);
  assert(r.resolution_date === '2026-05-31', `resolution_date === 2026-05-31`);
}

console.log('\nTest 4: normalizeKalshi — between-strike-type skipped');
{
  const market = {
    ticker: 'KXBTC-26MAY31-B100000', _series_ticker_hint: 'KXBTC',
    yes_sub_title: '$100,000 to 100,999', strike_type: 'between',
    expiration_time: '2026-05-31T20:00:00Z',
  };
  const r = normalizeKalshi(market);
  assert(r.skip === true, 'skipped');
  assert(r.reason === 'kalshi_strike_type_between_not_threshold', 'reason matches');
}

// ── Pass 2 (Poly monotonicity) ───────────────────────────────────────────────
console.log('\nTest 5: Pass 2 — BTC above-$100k @ 0.30 vs above-$120k @ 0.35 → emit');
{
  const event = {
    slug: 'btc-by-may-31', title: 'BTC price by May 31?',
    category: 'crypto', tags: [],
  };
  const fresh = new Date().toISOString();
  const mk = (id, strike, yes) => ({
    id, slug: `s-${id}`, question: `Will BTC be above $${strike.toLocaleString()} on May 31?`,
    groupItemTitle: `$${strike.toLocaleString()}`,
    endDate: '2026-05-31T12:00:00Z', outcomePrices: JSON.stringify([yes, 1 - yes]),
    liquidityNum: 8000, volume24hr: 4000, lastTradeTime: fresh,
    active: true, closed: false,
  });
  const ev = { ...event, markets: [mk('a', 100000, 0.30), mk('b', 120000, 0.35)] };
  const r = await runPass2([ev], log);
  assert(r.opportunities.length === 1, `1 opportunity emitted (got ${r.opportunities.length})`);
  if (r.opportunities[0]) {
    const o = r.opportunities[0];
    assert(o.type === 'poly_monotonicity', 'type === poly_monotonicity');
    assert(Math.abs(o.edge_gross_pct - 5.0) < 0.01, `edge_gross_pct ≈ 5.0 (got ${o.edge_gross_pct})`);
    assert(o.legs.length === 2, '2 legs');
    const yesLeg = o.legs.find(l => l.side === 'YES');
    const noLeg = o.legs.find(l => l.side === 'NO');
    assert(yesLeg && yesLeg.market_id === 'a', `YES leg on cheap-low-strike market`);
    assert(noLeg && noLeg.market_id === 'b', `NO leg on expensive-high-strike market`);
  }
}

console.log('\nTest 6: Pass 2 — monotonic prices (no inversion) → no emit');
{
  const event = { slug: 'btc-may-31-mono', title: 'BTC by May 31', category: 'crypto', tags: [] };
  const fresh = new Date().toISOString();
  const mk = (id, strike, yes) => ({
    id, question: `Will BTC be above $${strike.toLocaleString()}?`,
    groupItemTitle: `$${strike.toLocaleString()}`, endDate: '2026-05-31T12:00:00Z',
    outcomePrices: JSON.stringify([yes, 1 - yes]),
    liquidityNum: 8000, volume24hr: 4000, lastTradeTime: fresh, active: true, closed: false,
  });
  // Correct: lower strike = higher yes
  const ev = { ...event, markets: [mk('a', 100000, 0.50), mk('b', 120000, 0.30), mk('c', 150000, 0.10)] };
  const r = await runPass2([ev], log);
  assert(r.opportunities.length === 0, 'no opportunity emitted on monotonic ladder');
}

console.log('\nTest 7: Pass 2 — below-direction inversion');
{
  const event = { slug: 'btc-may-31-below', title: 'BTC by May 31', category: 'crypto', tags: [] };
  const fresh = new Date().toISOString();
  const mk = (id, strike, yes) => ({
    id, question: `Will BTC be below $${strike.toLocaleString()}?`,
    groupItemTitle: `$${strike.toLocaleString()}`, endDate: '2026-05-31T12:00:00Z',
    outcomePrices: JSON.stringify([yes, 1 - yes]),
    liquidityNum: 8000, volume24hr: 4000, lastTradeTime: fresh, active: true, closed: false,
  });
  // For "below" direction, low_strike yes should be < high_strike yes (price rises with strike).
  // Inversion: low_strike yes > high_strike yes.
  const ev = { ...event, markets: [mk('a', 80000, 0.50), mk('b', 100000, 0.40)] };
  const r = await runPass2([ev], log);
  assert(r.opportunities.length === 1, `1 opportunity (got ${r.opportunities.length})`);
  if (r.opportunities[0]) {
    assert(Math.abs(r.opportunities[0].edge_gross_pct - 10.0) < 0.01, `edge ≈ 10pp`);
  }
}

// ── Pass 3 (Kalshi monotonicity) ─────────────────────────────────────────────
console.log('\nTest 8: Pass 3 — KXBTC above-$100k @ 0.30 vs above-$120k @ 0.35 → emit');
{
  const fresh = new Date().toISOString();
  const mk = (ticker, strike, yes_ask) => ({
    ticker, event_ticker: 'KXBTC-26MAY31', _series_ticker_hint: 'KXBTC',
    yes_sub_title: `$${strike.toLocaleString()} or above`, strike_type: 'greater',
    expiration_time: '2026-05-31T20:00:00Z', close_time: '2026-05-31T20:00:00Z',
    open_time: '2026-05-30T00:00:00Z',
    yes_bid_dollars: (yes_ask - 0.005).toFixed(4),
    yes_ask_dollars: yes_ask.toFixed(4),
    no_bid_dollars: (1 - yes_ask).toFixed(4),
    no_ask_dollars: (1 - yes_ask + 0.005).toFixed(4),
    last_price_dollars: yes_ask.toFixed(4),
    volume_24h_fp: 5000, volume_fp: 50000,
    liquidity_dollars: '8000.00', updated_time: fresh, status: 'active',
  });
  const markets = [mk('KXBTC-26MAY31-T100000', 100000, 0.30), mk('KXBTC-26MAY31-T120000', 120000, 0.35)];
  const r = await runPass3(markets, log);
  assert(r.opportunities.length === 1, `1 opportunity (got ${r.opportunities.length})`);
  if (r.opportunities[0]) {
    const o = r.opportunities[0];
    assert(o.type === 'kalshi_monotonicity', 'type === kalshi_monotonicity');
    assert(Math.abs(o.edge_gross_pct - 5.0) < 0.01, `edge ≈ 5pp (got ${o.edge_gross_pct})`);
    assert(o.legs.every(l => l.platform === 'kalshi'), 'all legs kalshi');
  }
}

console.log('\nTest 9: Pass 3 — same-strike pair → no emit (degenerate)');
{
  const fresh = new Date().toISOString();
  const mk = (ticker, strike, yes_ask) => ({
    ticker, _series_ticker_hint: 'KXBTC',
    yes_sub_title: `$${strike.toLocaleString()} or above`, strike_type: 'greater',
    expiration_time: '2026-05-31T20:00:00Z', close_time: '2026-05-31T20:00:00Z',
    open_time: '2026-05-30T00:00:00Z',
    yes_bid_dollars: (yes_ask - 0.005).toFixed(4),
    yes_ask_dollars: yes_ask.toFixed(4),
    volume_24h_fp: 5000, liquidity_dollars: '8000.00', updated_time: fresh, status: 'active',
  });
  // Two markets with same strike (shouldn't typically happen, but the canonical
  // key would dedup these — guarding against it anyway).
  const r = await runPass3([mk('A', 100000, 0.40), mk('B', 100000, 0.30)], log);
  assert(r.opportunities.length === 0, 'no emit for same-strike pair');
}

console.log(`\n${pass}/${pass + fail} tests passed`);
process.exit(fail > 0 ? 1 : 0);
