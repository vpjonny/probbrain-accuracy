// Hand-crafted unit tests for Pass 4 (curated cross-platform pairs).
// Run: node scanner/test-pass4.js

import { runPass4 } from './passes/pass4-curated-cross.js';
import { runPass5 } from './passes/pass5-cross-platform.js';
import { pairsMatch } from './dicts/curated-pairs.js';
import { createLogger } from './lib/log.js';

let pass = 0, fail = 0;
function assert(cond, msg) {
  if (cond) { pass++; console.log(`  ✓ ${msg}`); }
  else { fail++; console.log(`  ✗ ${msg}`); }
}
const log = createLogger({ verbose: false });

const fresh = new Date().toISOString();

function makePolyEvent({ slug, title, strike, yes, endDate, marketId, question, groupItemTitle }) {
  return {
    id: `poly-event-${slug}`, slug, title,
    category: 'crypto', tags: [],
    markets: [{
      id: marketId, slug: `${slug}-m`,
      question: question || `Will Bitcoin reach $${strike.toLocaleString()} by December 31, 2026?`,
      groupItemTitle: groupItemTitle || `$${strike.toLocaleString()}`,
      endDate,
      outcomePrices: JSON.stringify([yes, 1 - yes]),
      liquidityNum: 8000, volume24hr: 12000, lastTradeTime: fresh,
      active: true, closed: false,
    }],
  };
}

function makeKalshi({ ticker, strike, yesAsk, expiration, seriesHint = 'KXBTCMAXY', sub }) {
  const yesBid = Math.max(0, yesAsk - 0.005);
  return {
    ticker, event_ticker: `KXBTCMAXY-26DEC31`,
    _series_ticker_hint: seriesHint,
    yes_sub_title: sub || `Above $${strike.toLocaleString()}`,
    strike_type: 'greater',
    expiration_time: expiration, close_time: expiration,
    open_time: new Date(Date.parse(expiration) - 30 * 86400_000).toISOString(),
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

// Synthetic curated pair used by every test below — keeps tests independent of
// whatever lives in dicts/curated-pairs.js.
function syntheticPair({
  id = 'test-pair', strikeTolerancePct = 0.5,
  requireSameDirection = true, sameResolutionWindow = true,
  polyFilter, kalshiFilter,
} = {}) {
  return {
    id, underlying: 'BTC',
    polyFilter: polyFilter || ((e, m) => /test-/.test(e.slug || '')),
    kalshiFilter: kalshiFilter || ((m) => (m._series_ticker_hint || '').startsWith('KXBTCMAXY')),
    match: { strikeTolerancePct, requireSameDirection },
    sameResolutionWindow,
    notes: 'synthetic test pair',
  };
}

// ── Test 1: pairsMatch helper basics ────────────────────────────────────────
console.log('Test 1: pairsMatch — penny strike diff within tolerance');
{
  const pair = syntheticPair({ strikeTolerancePct: 0.5 });
  const m = pairsMatch(pair,
    { underlying: 'BTC', direction: 'above', strike: 150000 },
    { underlying: 'BTC', direction: 'above', strike: 149999.99 },
  );
  assert(m.matches === true, '$150k vs $149,999.99 within 0.5% tolerance');
}

console.log('\nTest 2: pairsMatch — strike outside tolerance rejected');
{
  const pair = syntheticPair({ strikeTolerancePct: 0.5 });
  const m = pairsMatch(pair,
    { underlying: 'BTC', direction: 'above', strike: 150000 },
    { underlying: 'BTC', direction: 'above', strike: 200000 },
  );
  assert(m.matches === false, '$150k vs $200k rejected');
  assert(m.reason && m.reason.startsWith('strike_diff'), `reason=strike_diff* (got ${m.reason})`);
}

console.log('\nTest 3: pairsMatch — direction mismatch rejected when required');
{
  const pair = syntheticPair({ requireSameDirection: true });
  const m = pairsMatch(pair,
    { underlying: 'BTC', direction: 'above', strike: 150000 },
    { underlying: 'BTC', direction: 'below', strike: 150000 },
  );
  assert(m.matches === false, 'above vs below rejected');
  assert(m.reason === 'direction_differs', `reason=direction_differs (got ${m.reason})`);
}

// ── Test 4: end-to-end strike-tolerance match emits Tier 1 ──────────────────
console.log('\nTest 4: end-to-end — penny strike diff emits Tier 1 with curated_pair flag');
{
  // Long horizon (year-end ladder is the seed use case) — bump the spread
  // wide enough that fees + capital cost don't push net edge negative.
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const kalshiEnd = new Date(closeMs + 30 * 86400_000).toISOString(); // 30d later
  const polyEv = makePolyEvent({
    slug: 'test-btc-yearend', title: 'BTC year-end',
    strike: 150000, yes: 0.10, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-149999.99', strike: 149999.99,
    yesAsk: 0.30, expiration: kalshiEnd,
  });
  const r = await runPass4([polyEv], [kalshi], log, { curatedPairs: [syntheticPair()] });
  assert(r.opportunities.length === 1, `1 opportunity (got ${r.opportunities.length})`);
  if (r.opportunities[0]) {
    const o = r.opportunities[0];
    assert(o.confidence_flags.includes('curated_pair'), 'has curated_pair flag');
    assert(!o.confidence_flags.includes('resolution_mismatch'), 'no resolution_mismatch (sameResolutionWindow=true)');
    assert(!o.confidence_flags.includes('offset_warning'), 'no offset_warning (sameResolutionWindow=true)');
    assert(o.curated_pair_id === 'test-pair', `curated_pair_id set (got ${o.curated_pair_id})`);
    assert(o.tier === 1, `tier === 1 (got ${o.tier})`);
    assert(r.coveredPairs.has(`p1|KXBTCMAXY-26DEC31-149999.99`), 'coveredPairs populated');
  }
}

// ── Test 5: sameResolutionWindow=false caps at Tier 2 with flag ─────────────
console.log('\nTest 5: sameResolutionWindow=false caps non-strict matches at Tier 2');
{
  // Small offset within tolerance (so the offset_too_large hard cap doesn't
  // skip), wide spread so we'd otherwise be Tier 1 — but sameResolutionWindow
  // is false, so Pass 4 must still cap at Tier 2 + add resolution_mismatch.
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const kalshiEnd = polyEnd; // identical timestamp
  const polyEv = makePolyEvent({
    slug: 'test-btc-yearend', title: 'BTC year-end',
    strike: 150000, yes: 0.10, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-149999.99', strike: 149999.99,
    yesAsk: 0.30, expiration: kalshiEnd,
  });
  const r = await runPass4([polyEv], [kalshi], log, {
    curatedPairs: [syntheticPair({ sameResolutionWindow: false })],
  });
  assert(r.opportunities.length === 1, `1 opportunity emitted (got ${r.opportunities.length})`);
  if (r.opportunities[0]) {
    const o = r.opportunities[0];
    assert(o.confidence_flags.includes('resolution_mismatch'), 'has resolution_mismatch flag');
    assert(o.confidence_flags.includes('curated_pair'), 'still has curated_pair flag');
    assert(o.tier >= 2, `tier ≥ 2 (got ${o.tier})`);
  }
}

// ── Test 6: strike outside tolerance is skipped ─────────────────────────────
console.log('\nTest 6: strike outside tolerance → skipped (no emit)');
{
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-yearend', title: 'BTC year-end',
    strike: 150000, yes: 0.20, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-200000', strike: 200000,
    yesAsk: 0.30, expiration: polyEnd,
  });
  const r = await runPass4([polyEv], [kalshi], log, { curatedPairs: [syntheticPair()] });
  assert(r.opportunities.length === 0, 'no emit — strikes too far apart');
  assert(r.coveredPairs.size === 0, 'coveredPairs empty');
}

// ── Test 7: spread under threshold → no emit ────────────────────────────────
console.log('\nTest 7: spread under 2pp → no emit');
{
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-yearend', title: 'BTC year-end',
    strike: 150000, yes: 0.295, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-149999.99', strike: 149999.99,
    yesAsk: 0.30, expiration: polyEnd,
  });
  const r = await runPass4([polyEv], [kalshi], log, { curatedPairs: [syntheticPair()] });
  assert(r.opportunities.length === 0, 'no emit — spread under 2pp threshold');
}

// ── Test 8: dead Kalshi leg → skipped ───────────────────────────────────────
console.log('\nTest 8: dead Kalshi leg (v24=0) → skipped');
{
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-yearend', title: 'BTC year-end',
    strike: 150000, yes: 0.20, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-149999.99', strike: 149999.99,
    yesAsk: 0.30, expiration: polyEnd,
  });
  kalshi.volume_24h_fp = 0;
  kalshi.updated_time = null;
  const r = await runPass4([polyEv], [kalshi], log, { curatedPairs: [syntheticPair()] });
  assert(r.opportunities.length === 0, 'no emit — kalshi leg has no v24');
}

// ── Test 9: Pass 5 dedupes when given Pass 4 coveredPairs ───────────────────
console.log('\nTest 9: Pass 5 honors Pass 4 coveredPairs (dedupe)');
{
  // Identical strikes so Pass 5 strike-key matching would normally fire.
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-yearend', title: 'BTC year-end',
    strike: 150000, yes: 0.20, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-150000', strike: 150000,
    yesAsk: 0.30, expiration: polyEnd,
  });
  // Without dedupe, Pass 5 would emit one cross_platform card.
  const r5alone = await runPass5([polyEv], [kalshi], log);
  assert(r5alone.opportunities.length >= 1, `Pass 5 alone emits (got ${r5alone.opportunities.length})`);

  // With Pass 4 covering this pair, Pass 5 must skip.
  const covered = new Set(['p1|KXBTCMAXY-26DEC31-150000']);
  const r5dedup = await runPass5([polyEv], [kalshi], log, { coveredPairs: covered });
  assert(r5dedup.opportunities.length === 0, `Pass 5 with covered set emits 0 (got ${r5dedup.opportunities.length})`);
  assert(r5dedup.stats.curated_dedup_skipped >= 1, `curated_dedup_skipped ≥ 1 (got ${r5dedup.stats.curated_dedup_skipped})`);
}

// ── Test 10: empty curated dict → 0 opportunities ───────────────────────────
console.log('\nTest 10: empty curated dict → 0 opportunities');
{
  const polyEv = makePolyEvent({
    slug: 'test-btc-yearend', title: 'BTC',
    strike: 150000, yes: 0.20, endDate: new Date(Date.now() + 200 * 86400_000).toISOString(),
    marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-149999.99', strike: 149999.99,
    yesAsk: 0.30, expiration: new Date(Date.now() + 200 * 86400_000).toISOString(),
  });
  const r = await runPass4([polyEv], [kalshi], log, { curatedPairs: [] });
  assert(r.opportunities.length === 0, 'no opportunities when dict is empty');
  assert(r.stats.curated_pairs_evaluated === 0, 'stat reflects 0 pairs');
}

// ── Test 11: BTC year-end seed entry filters work on realistic data ─────────
console.log('\nTest 11: real seed entry — BTC Dec 31 2026 ladder filter shape');
{
  // We don't import the seed list; we just confirm the filter shapes used by
  // the seed work on realistic Poly + Kalshi market shapes. The point is to
  // catch silent regressions if someone tightens the regex.
  const realPolyEvent = {
    id: 'poly-real',
    slug: 'will-bitcoin-reach-200000-by-december-31-2026',
    title: 'Will Bitcoin reach $200,000 by December 31, 2026?',
    category: 'crypto', tags: [{ label: 'crypto' }],
    markets: [{
      id: 'real-poly-1', slug: 'real-poly-1',
      question: 'Will Bitcoin reach $200,000 by December 31, 2026?',
      groupItemTitle: '$200,000',
      endDate: '2027-01-01T05:00:00Z',
      outcomePrices: JSON.stringify([0.05, 0.95]),
      liquidityNum: 50000, volume24hr: 5000, lastTradeTime: fresh,
      active: true, closed: false,
    }],
  };
  const realKalshi = {
    ticker: 'KXBTCMAXY-26DEC31-199999.99',
    event_ticker: 'KXBTCMAXY-26DEC31',
    _series_ticker_hint: 'KXBTCMAXY',
    yes_sub_title: 'Above $199,999.99',
    strike_type: 'greater',
    expiration_time: '2027-01-31T04:59:00Z',
    close_time: '2027-01-31T04:59:00Z',
    open_time: '2026-04-01T00:00:00Z',
    yes_bid_dollars: '0.0500', yes_ask_dollars: '0.0600',
    no_bid_dollars: '0.94', no_ask_dollars: '0.95',
    last_price_dollars: '0.06',
    volume_24h_fp: 1500, volume_fp: 30000,
    liquidity_dollars: '5000.00', updated_time: fresh,
    status: 'active',
  };
  // Use the actual exported seed pair from the dict — verifies the regex shapes
  // still match the real product line.
  const { CURATED_PAIRS } = await import('./dicts/curated-pairs.js');
  const r = await runPass4([realPolyEvent], [realKalshi], log, { curatedPairs: CURATED_PAIRS });
  // No spread (0.05 vs 0.055 mid) — but we just need the filter to pick the
  // markets up. Either an opportunity emits or it gets filtered for spread —
  // both are fine; what we want to avoid is "0 candidates" which would mean
  // the filter regex broke.
  // Stat we care about: at least the seed pair was evaluated AND the pre-emit
  // logging would have shown >0 candidates per side. We can't see that here,
  // but we can probe by making one side have a clear spread.
  realPolyEvent.markets[0].outcomePrices = JSON.stringify([0.02, 0.98]);
  const r2 = await runPass4([realPolyEvent], [realKalshi], log, { curatedPairs: CURATED_PAIRS });
  // Now Poly=0.02, Kalshi mid=0.055 → 3.5pp spread. If the seed filters work,
  // we'll get an opportunity.
  assert(r2.opportunities.length >= 1, `seed entry matches realistic markets (got ${r2.opportunities.length})`);
}

console.log(`\n${pass}/${pass + fail} tests passed`);
process.exit(fail > 0 ? 1 : 0);
