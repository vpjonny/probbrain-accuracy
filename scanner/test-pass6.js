// Hand-crafted unit tests for Pass 6 (cross-platform bracket arbs).
// Run: node scanner/test-pass6.js

import { runPass6 } from './passes/pass6-cross-bracket.js';
import { createLogger } from './lib/log.js';

let pass = 0, fail = 0;
function assert(cond, msg) {
  if (cond) { pass++; console.log(`  ✓ ${msg}`); }
  else { fail++; console.log(`  ✗ ${msg}`); }
}
const log = createLogger({ verbose: false });

const fresh = new Date().toISOString();

function makePolyEvent({ slug, title, strike, yes, endDate, marketId, direction = 'above' }) {
  const dirWord = direction === 'above' ? 'above' : 'below';
  return {
    id: `poly-event-${slug}`, slug, title,
    category: 'crypto', tags: [],
    markets: [{
      id: marketId, slug: `${slug}-m`,
      question: `Will Bitcoin be ${dirWord} $${strike.toLocaleString()} by December 31, 2026?`,
      groupItemTitle: `$${strike.toLocaleString()}`,
      endDate,
      outcomePrices: JSON.stringify([yes, 1 - yes]),
      liquidityNum: 8000, volume24hr: 12000, lastTradeTime: fresh,
      active: true, closed: false,
    }],
  };
}

function makeKalshi({ ticker, strike, yesAsk, expiration, direction = 'above' }) {
  const yesBid = Math.max(0, yesAsk - 0.005);
  const sub = direction === 'above'
    ? `Above $${strike.toLocaleString()}`
    : `Below $${strike.toLocaleString()}`;
  return {
    ticker, event_ticker: 'KXBTCMAXY-26DEC31',
    _series_ticker_hint: 'KXBTCMAXY',
    yes_sub_title: sub,
    strike_type: direction === 'above' ? 'greater' : 'less',
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

function syntheticPair({
  id = 'test-bracket', strikeTolerancePct = 0.5,
  sameResolutionWindow = true,
} = {}) {
  return {
    id, underlying: 'BTC',
    polyFilter: (e) => /test-/.test(e.slug || ''),
    kalshiFilter: (m) => (m._series_ticker_hint || '').startsWith('KXBTCMAXY'),
    match: { strikeTolerancePct, requireSameDirection: true },
    sameResolutionWindow,
    notes: 'synthetic test pair',
  };
}

// ── Test 1: above-direction violation — Poly stricter & priced higher ───────
console.log('Test 1: above — Poly@150k YES=0.30 vs Kalshi@130k YES=0.20 → bracket arb');
{
  // For "above": stricter (higher strike) should have LOWER P. Poly@150k is
  // stricter and is priced HIGHER than Kalshi@130k. Violation.
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-150k', title: 'BTC year-end',
    strike: 150000, yes: 0.30, endDate: polyEnd, marketId: 'p-strict',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-130000', strike: 130000,
    yesAsk: 0.20, expiration: polyEnd,
  });
  const r = await runPass6([polyEv], [kalshi], log, { curatedPairs: [syntheticPair()] });
  assert(r.opportunities.length === 1, `1 opportunity (got ${r.opportunities.length})`);
  if (r.opportunities[0]) {
    const o = r.opportunities[0];
    assert(o.type === 'cross_platform_bracket', 'type cross_platform_bracket');
    assert(Math.abs(o.edge_gross_pct - 10) < 0.5, `gross ≈ 10pp (got ${o.edge_gross_pct})`);
    // Looser side = Kalshi@130k → buy YES; stricter side = Poly@150k → buy NO
    const kLeg = o.legs.find(l => l.platform === 'kalshi');
    const pLeg = o.legs.find(l => l.platform === 'polymarket');
    assert(kLeg.side === 'YES', 'YES on Kalshi (looser side)');
    assert(pLeg.side === 'NO', 'NO on Polymarket (stricter side)');
    assert(o.confidence_flags.includes('curated_pair'), 'curated_pair flag');
    assert(o.confidence_flags.includes('bracket_arb'), 'bracket_arb flag');
  }
}

// ── Test 2: above — properly ordered (no violation) → no emit ───────────────
console.log('\nTest 2: above — Poly@150k YES=0.20 vs Kalshi@130k YES=0.30 → no violation');
{
  // Stricter (150k) has LOWER P than looser (130k). That's correct ordering.
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-150k', title: 'BTC year-end',
    strike: 150000, yes: 0.20, endDate: polyEnd, marketId: 'p-strict',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-130000', strike: 130000,
    yesAsk: 0.30, expiration: polyEnd,
  });
  const r = await runPass6([polyEv], [kalshi], log, { curatedPairs: [syntheticPair()] });
  assert(r.opportunities.length === 0, 'no emit — monotonicity holds');
}

// ── Test 3: below-direction violation ───────────────────────────────────────
console.log('\nTest 3: below — Poly@$70k YES=0.30 vs Kalshi@$80k YES=0.20 → bracket arb');
{
  // For "below": looser = higher strike. Kalshi@80k is looser (more outcomes
  // satisfy "below 80k"). Looser should have HIGHER P. Kalshi=0.20, Poly=0.30
  // → looser-side is priced lower → violation. Buy Kalshi YES (looser, cheap)
  // + Poly NO (stricter, cheap = $0.70).
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-70k-below', title: 'BTC',
    strike: 70000, yes: 0.30, endDate: polyEnd, marketId: 'p-strict-below',
    direction: 'below',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-80000', strike: 80000,
    yesAsk: 0.20, expiration: polyEnd, direction: 'below',
  });
  const r = await runPass6([polyEv], [kalshi], log, { curatedPairs: [syntheticPair()] });
  assert(r.opportunities.length === 1, `1 opportunity (got ${r.opportunities.length})`);
  if (r.opportunities[0]) {
    const o = r.opportunities[0];
    const kLeg = o.legs.find(l => l.platform === 'kalshi');
    const pLeg = o.legs.find(l => l.platform === 'polymarket');
    // Kalshi@80k below = looser side
    assert(kLeg.side === 'YES', 'YES on Kalshi@80k (looser side for below)');
    assert(pLeg.side === 'NO', 'NO on Poly@70k (stricter side for below)');
  }
}

// ── Test 4: direction mismatch → no emit ────────────────────────────────────
console.log('\nTest 4: direction mismatch (above vs below) → no emit');
{
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-150k', title: 'BTC',
    strike: 150000, yes: 0.30, endDate: polyEnd, marketId: 'p1',
    direction: 'above',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-100000', strike: 100000,
    yesAsk: 0.20, expiration: polyEnd, direction: 'below',
  });
  const r = await runPass6([polyEv], [kalshi], log, { curatedPairs: [syntheticPair()] });
  assert(r.opportunities.length === 0, 'no emit — opposite directions');
}

// ── Test 5: strikes within tolerance → skipped (Pass 4 territory) ──────────
console.log('\nTest 5: strike diff inside Pass 4 tolerance → no emit');
{
  // 0.5% tolerance: $150,000 vs $149,999.99 → 0.0007% diff. Pass 6 skips.
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-150k', title: 'BTC',
    strike: 150000, yes: 0.30, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-149999.99', strike: 149999.99,
    yesAsk: 0.20, expiration: polyEnd,
  });
  const r = await runPass6([polyEv], [kalshi], log, { curatedPairs: [syntheticPair({ strikeTolerancePct: 0.5 })] });
  assert(r.opportunities.length === 0, 'no emit — strikes inside Pass 4 tolerance');
}

// ── Test 6: gap below threshold → no emit ───────────────────────────────────
console.log('\nTest 6: violation gap < 2pp threshold → no emit');
{
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  // Poly@150k = 0.215, Kalshi@130k = 0.20 → 1.5pp violation, below threshold
  const polyEv = makePolyEvent({
    slug: 'test-btc-150k', title: 'BTC',
    strike: 150000, yes: 0.215, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-130000', strike: 130000,
    yesAsk: 0.20, expiration: polyEnd,
  });
  const r = await runPass6([polyEv], [kalshi], log, { curatedPairs: [syntheticPair()] });
  assert(r.opportunities.length === 0, 'no emit — gap below 2pp');
}

// ── Test 7: dead Kalshi leg → skipped ───────────────────────────────────────
console.log('\nTest 7: dead Kalshi leg → skipped');
{
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-150k', title: 'BTC',
    strike: 150000, yes: 0.30, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-130000', strike: 130000,
    yesAsk: 0.20, expiration: polyEnd,
  });
  kalshi.volume_24h_fp = 0;
  kalshi.updated_time = null;
  const r = await runPass6([polyEv], [kalshi], log, { curatedPairs: [syntheticPair()] });
  assert(r.opportunities.length === 0, 'no emit — kalshi leg dead');
}

// ── Test 8: sameResolutionWindow=false caps at Tier 2 ───────────────────────
console.log('\nTest 8: sameResolutionWindow=false → Tier 2 + resolution_mismatch');
{
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-150k', title: 'BTC',
    strike: 150000, yes: 0.30, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-130000', strike: 130000,
    yesAsk: 0.20, expiration: polyEnd,
  });
  const r = await runPass6([polyEv], [kalshi], log, {
    curatedPairs: [syntheticPair({ sameResolutionWindow: false })],
  });
  assert(r.opportunities.length === 1, `1 opportunity (got ${r.opportunities.length})`);
  if (r.opportunities[0]) {
    const o = r.opportunities[0];
    assert(o.tier >= 2, `tier ≥ 2 (got ${o.tier})`);
    assert(o.confidence_flags.includes('resolution_mismatch'), 'resolution_mismatch flag');
  }
}

// ── Test 9: ladder — multiple Kalshi strikes vs one Poly → all violations ──
console.log('\nTest 9: full Kalshi ladder vs one Poly market → emits all violations');
{
  // Poly@150k YES=0.30. Kalshi at multiple strikes below should ALL satisfy
  // "looser → higher P" — but if any Kalshi strike <150k has YES<0.30, that's
  // a bracket arb against Poly@150k.
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-150k', title: 'BTC',
    strike: 150000, yes: 0.30, endDate: polyEnd, marketId: 'p1',
  });
  // 3 Kalshi strikes below 150k, all priced lower than 0.30 → 3 violations
  const kLadder = [
    makeKalshi({ ticker: 'K1', strike: 120000, yesAsk: 0.25, expiration: polyEnd }),
    makeKalshi({ ticker: 'K2', strike: 130000, yesAsk: 0.22, expiration: polyEnd }),
    makeKalshi({ ticker: 'K3', strike: 140000, yesAsk: 0.20, expiration: polyEnd }),
    makeKalshi({ ticker: 'K4', strike: 160000, yesAsk: 0.10, expiration: polyEnd }), // stricter than poly, properly ordered → no violation
  ];
  const r = await runPass6([polyEv], kLadder, log, { curatedPairs: [syntheticPair()] });
  // K1, K2, K3 all looser than 150k and priced lower → 3 violations
  // K4 stricter than 150k and priced lower → properly ordered → no violation
  assert(r.opportunities.length === 3, `3 violations (got ${r.opportunities.length})`);
}

// ── Test 10: returns coveredPairs ───────────────────────────────────────────
console.log('\nTest 10: coveredPairs populated for emitted pairs');
{
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-150k', title: 'BTC',
    strike: 150000, yes: 0.30, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'KXBTCMAXY-26DEC31-130000', strike: 130000,
    yesAsk: 0.20, expiration: polyEnd,
  });
  const r = await runPass6([polyEv], [kalshi], log, { curatedPairs: [syntheticPair()] });
  assert(r.coveredPairs instanceof Set, 'coveredPairs is a Set');
  assert(r.coveredPairs.has('p1|KXBTCMAXY-26DEC31-130000'), 'pair recorded for dedupe');
}

// ── Test 11: identical strikes → skipped (no looseStrict relationship) ─────
console.log('\nTest 11: identical strikes → not Pass 6 territory');
{
  const closeMs = Date.now() + 200 * 86400_000;
  const polyEnd = new Date(closeMs).toISOString();
  const polyEv = makePolyEvent({
    slug: 'test-btc-150k', title: 'BTC',
    strike: 150000, yes: 0.30, endDate: polyEnd, marketId: 'p1',
  });
  const kalshi = makeKalshi({
    ticker: 'K1', strike: 150000, yesAsk: 0.20, expiration: polyEnd,
  });
  const r = await runPass6([polyEv], [kalshi], log, {
    curatedPairs: [syntheticPair({ strikeTolerancePct: 0 })], // no tolerance, identical strikes still skipped
  });
  assert(r.opportunities.length === 0, 'no emit — identical strikes are Pass 4 / Pass 5 territory');
}

console.log(`\n${pass}/${pass + fail} tests passed`);
process.exit(fail > 0 ? 1 : 0);
