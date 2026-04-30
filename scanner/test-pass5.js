// Hand-crafted unit tests for Pass 5 (cross-platform matching).
// Run: node scanner/test-pass5.js
//
// Per spec sanity tests #4 and #6.

import { runPass5 } from './passes/pass5-cross-platform.js';
import { createLogger } from './lib/log.js';

let pass = 0, fail = 0;
function assert(cond, msg) {
  if (cond) { pass++; console.log(`  ✓ ${msg}`); }
  else { fail++; console.log(`  ✗ ${msg}`); }
}
const log = createLogger({ verbose: false });

const fresh = new Date().toISOString();

function makePolyEvent({ slug, title, strike, yes, endDate, marketId }) {
  return {
    id: `poly-event-${slug}`, slug, title,
    category: 'crypto', tags: [],
    markets: [{
      id: marketId, slug: `${slug}-m`,
      question: `Will Bitcoin be above $${strike.toLocaleString()} on ${endDate.slice(0, 10)}?`,
      groupItemTitle: `$${strike.toLocaleString()}`,
      endDate,
      outcomePrices: JSON.stringify([yes, 1 - yes]),
      liquidityNum: 8000, volume24hr: 12000, lastTradeTime: fresh,
      active: true, closed: false,
    }],
  };
}

function makeKalshi({ ticker, strike, yesAsk, expiration }) {
  const yesBid = Math.max(0, yesAsk - 0.005);
  return {
    ticker, event_ticker: `KXBTC-${expiration.slice(2, 8)}`,
    _series_ticker_hint: 'KXBTC',
    yes_sub_title: `$${strike.toLocaleString()} or above`,
    strike_type: 'greater',
    expiration_time: expiration, close_time: expiration,
    open_time: new Date(Date.parse(expiration) - 86400_000).toISOString(),
    yes_bid_dollars: yesBid.toFixed(4),
    yes_ask_dollars: yesAsk.toFixed(4),
    no_bid_dollars: (1 - yesAsk).toFixed(4),
    no_ask_dollars: (1 - yesBid).toFixed(4),
    last_price_dollars: yesAsk.toFixed(4),
    volume_24h_fp: 5000, volume_fp: 50000,
    liquidity_dollars: '8000.00', updated_time: fresh,
    status: 'active',
  };
}

// ── Test 1: same strike + same date + 4% spread → match ─────────────────────
// Per spec sanity test #4. Daily market: closes within 36h of now.
console.log('Test 1 (spec test #4): BTC daily, same strike, 4% spread → match');
{
  // Close ~20h from now → both venues classify as 'daily' from time-to-end.
  const closeMs = Date.now() + 20 * 3600_000;
  const closeIso = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'btc-100k-today', title: 'BTC today',
    strike: 100000, yes: 0.30, endDate: closeIso, marketId: 'p1',
  });
  // Make Kalshi open_time 6h before close → Kalshi infers 'hourly'? No,
  // 6h falls in daily band. Use 12h before close.
  const kalshi = makeKalshi({
    ticker: 'KXBTC-DAILY-T100000', strike: 100000,
    yesAsk: 0.34, expiration: closeIso,
  });
  kalshi.open_time = new Date(closeMs - 12 * 3600_000).toISOString();
  const r = await runPass5([polyEv], [kalshi], log);
  assert(r.opportunities.length === 1, `1 opportunity (got ${r.opportunities.length})`);
  if (r.opportunities[0]) {
    const o = r.opportunities[0];
    assert(o.type === 'cross_platform', 'type === cross_platform');
    // Kalshi YES = (yes_bid 0.335 + yes_ask 0.34)/2 = 0.3375 → spread 3.75pp.
    assert(Math.abs(o.edge_gross_pct - 3.75) < 0.01, `edge_gross_pct ≈ 3.75 (got ${o.edge_gross_pct})`);
    assert(o.legs.length === 2, '2 legs');
    const polyLeg = o.legs.find(l => l.platform === 'polymarket');
    const kalshiLeg = o.legs.find(l => l.platform === 'kalshi');
    assert(polyLeg && polyLeg.side === 'YES', 'YES on Polymarket (cheaper at 0.30)');
    assert(kalshiLeg && kalshiLeg.side === 'NO', 'NO on Kalshi (more expensive)');
    assert(o.underlying === 'BTC', 'underlying === BTC');
    assert(o.resolution_type === 'daily', `resolution_type === daily (got ${o.resolution_type})`);
    assert(r.stats.shared_canonical_keys === 1, '1 shared canonical key');
  }
}

// ── Test 2: spread under 2pp → no emit ──────────────────────────────────────
console.log('\nTest 2: BTC daily, same strike, 1pp spread → no match');
{
  const closeMs = Date.now() + 20 * 3600_000;
  const closeIso = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'btc-100k-today', title: 'BTC today',
    strike: 100000, yes: 0.32, endDate: closeIso, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTC-DAILY-T100000', strike: 100000,
    yesAsk: 0.33, expiration: closeIso,
  });
  kalshi.open_time = new Date(closeMs - 12 * 3600_000).toISOString();
  const r = await runPass5([polyEv], [kalshi], log);
  assert(r.opportunities.length === 0, 'no opportunity (1pp spread under 2pp threshold)');
}

// ── Test 3: different strikes → no canonical key match ──────────────────────
console.log('\nTest 3: different strikes → no match');
{
  const closeMs = Date.now() + 20 * 3600_000;
  const closeIso = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'btc-100k-today', title: 'BTC today',
    strike: 100000, yes: 0.30, endDate: closeIso, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTC-DAILY-T120000', strike: 120000,
    yesAsk: 0.20, expiration: closeIso,
  });
  kalshi.open_time = new Date(closeMs - 12 * 3600_000).toISOString();
  const r = await runPass5([polyEv], [kalshi], log);
  assert(r.opportunities.length === 0, 'no match — different strikes');
  assert(r.stats.shared_canonical_keys === 0, '0 shared keys');
}

// ── Test 4 (spec test #6): 2h offset on a daily market → offset_warning ─────
console.log('\nTest 4 (spec test #6): 2h settlement offset on daily → offset_warning + downgrade');
{
  // Both within ~24h of now → both 'daily'. Same calendar day for matching.
  const dayMs = Date.now() + 14 * 3600_000;
  const dayStr = new Date(dayMs).toISOString().slice(0, 10);
  const polyEnd = `${dayStr}T18:00:00Z`;
  const kalshiEnd = `${dayStr}T20:00:00Z`; // 2h later
  const polyEv = makePolyEvent({
    slug: 'btc-100k-daily', title: 'BTC daily',
    strike: 100000, yes: 0.30, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTC-DAILY-T100000', strike: 100000,
    yesAsk: 0.36, expiration: kalshiEnd,
  });
  kalshi.open_time = new Date(Date.parse(kalshiEnd) - 12 * 3600_000).toISOString();
  const r = await runPass5([polyEv], [kalshi], log);
  assert(r.opportunities.length === 1, `1 opportunity (got ${r.opportunities.length})`);
  if (r.opportunities[0]) {
    const o = r.opportunities[0];
    assert(o.confidence_flags.includes('offset_warning'), 'has offset_warning flag');
    assert(o.tier >= 2, `tier downgraded ≥ 2 (got ${o.tier})`);
  }
}

// ── Test 5: completely dead Kalshi leg → skipped ────────────────────────────
console.log('\nTest 5: dead Kalshi leg → skipped');
{
  const closeIso = '2026-05-15T20:00:00Z';
  const polyEv = makePolyEvent({
    slug: 'btc-100k-may15', title: 'BTC by May 15',
    strike: 100000, yes: 0.30, endDate: closeIso, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTC-26MAY15-T100000', strike: 100000,
    yesAsk: 0.40, expiration: closeIso,
  });
  kalshi.volume_24h_fp = 0;
  kalshi.updated_time = null;
  const r = await runPass5([polyEv], [kalshi], log);
  assert(r.opportunities.length === 0, 'no emit — kalshi leg has no v24');
}

// ── Test 6: Poly endDate in past → not normalized for matching ──────────────
console.log('\nTest 6: Polymarket market past endDate → not in match');
{
  const polyClose = new Date(Date.now() - 86400_000).toISOString();
  const kalshiClose = new Date(Date.now() + 86400_000).toISOString();
  const polyEv = makePolyEvent({
    slug: 'btc-100k-past', title: 'BTC',
    strike: 100000, yes: 0.30, endDate: polyClose, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTC-FUTURE-T100000', strike: 100000,
    yesAsk: 0.40, expiration: kalshiClose,
  });
  const r = await runPass5([polyEv], [kalshi], log);
  assert(r.opportunities.length === 0, 'no emit — poly is past expiry');
}

console.log(`\n${pass}/${pass + fail} tests passed`);
process.exit(fail > 0 ? 1 : 0);
