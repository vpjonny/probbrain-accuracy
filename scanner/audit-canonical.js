// Audit: what canonical keys does each platform produce for BTC?
// Goal: find why Pass 5 has 0 shared canonical keys, calibrate normalizers.

import { fetchPolymarketEvents, fetchKalshiMarketsBySeries } from './lib/fetch.js';
import { normalizePolymarket } from './normalize/polymarket.js';
import { normalizeKalshi } from './normalize/kalshi.js';
import { serializeCanonicalKey } from './lib/canonical.js';
import { createLogger } from './lib/log.js';
import { UNDERLYINGS } from './dicts/underlyings.js';

const log = createLogger({ verbose: false });
const ASSET = process.argv[2] || 'BTC';

console.log(`\n=== Audit: ${ASSET} canonical keys on Poly vs Kalshi ===\n`);

const polyEvents = await fetchPolymarketEvents({ log });
const kalshiSeries = (UNDERLYINGS[ASSET]?.kalshi_series) || [];
const kalshiMarkets = await fetchKalshiMarketsBySeries(kalshiSeries, { log });

const nowMs = Date.now();
const polyKeys = new Map();   // key -> {price, market_id, q}
const kalshiKeys = new Map();

let polyAssetCount = 0;
for (const event of polyEvents) {
  for (const m of (event.markets || [])) {
    if (m.closed || m.active === false) continue;
    if (m.endDate && Date.parse(m.endDate) <= nowMs) continue;
    const norm = normalizePolymarket(m, event);
    if (norm.skip) continue;
    if (norm.underlying !== ASSET) continue;
    polyAssetCount++;
    const key = serializeCanonicalKey(norm);
    if (!polyKeys.has(key)) polyKeys.set(key, []);
    polyKeys.get(key).push({
      market_id: m.id,
      question: (m.question || '').slice(0, 80),
      slug: m.slug,
      yes: parseFloat((JSON.parse(m.outcomePrices || '["0","0"]'))[0] || 0),
      end: m.endDate,
    });
  }
}

let kalshiAssetCount = 0;
for (const m of kalshiMarkets) {
  const norm = normalizeKalshi(m);
  if (norm.skip) continue;
  if (norm.underlying !== ASSET) continue;
  kalshiAssetCount++;
  const key = serializeCanonicalKey(norm);
  if (!kalshiKeys.has(key)) kalshiKeys.set(key, []);
  kalshiKeys.get(key).push({
    ticker: m.ticker,
    sub: m.yes_sub_title,
    yes_ask: m.yes_ask_dollars,
    exp: m.expiration_time,
  });
}

console.log(`Poly ${ASSET} normalized: ${polyAssetCount} markets, ${polyKeys.size} unique keys`);
console.log(`Kalshi ${ASSET} normalized: ${kalshiAssetCount} markets, ${kalshiKeys.size} unique keys`);

const shared = [...polyKeys.keys()].filter(k => kalshiKeys.has(k));
console.log(`Shared canonical keys: ${shared.length}`);

console.log(`\n--- Poly ${ASSET} keys (sample 5) ---`);
let i = 0;
for (const [key, items] of polyKeys.entries()) {
  if (i++ >= 5) break;
  console.log(`  ${key}`);
  console.log(`    "${items[0].question}" yes=${items[0].yes} end=${items[0].end}`);
}

console.log(`\n--- Kalshi ${ASSET} keys (sample 5) ---`);
i = 0;
for (const [key, items] of kalshiKeys.entries()) {
  if (i++ >= 5) break;
  console.log(`  ${key}`);
  console.log(`    "${items[0].sub}" yes_ask=${items[0].yes_ask} exp=${items[0].exp}`);
}

// Look for near-misses: same (underlying, direction, strike, calendar_date)
// but possibly different resolution_type or hourly slot.
function sameDayKey(canonicalKey) {
  const [u, d, s, date] = canonicalKey.split('|');
  return `${u}|${d}|${s}|${(date || '').slice(0, 10)}`;
}

const polyDay = new Map();
for (const k of polyKeys.keys()) {
  const sd = sameDayKey(k);
  if (!polyDay.has(sd)) polyDay.set(sd, []);
  polyDay.get(sd).push(k);
}
const kalshiDay = new Map();
for (const k of kalshiKeys.keys()) {
  const sd = sameDayKey(k);
  if (!kalshiDay.has(sd)) kalshiDay.set(sd, []);
  kalshiDay.get(sd).push(k);
}

const sharedDays = [...polyDay.keys()].filter(d => kalshiDay.has(d));
console.log(`\n--- Same (underlying|direction|strike|calendar_date) — ignoring resolution_type ---`);
console.log(`Total shared same-day keys: ${sharedDays.length}`);
for (const sd of sharedDays.slice(0, 12)) {
  console.log(`\n  ${sd}`);
  for (const pk of polyDay.get(sd)) console.log(`    POLY:   ${pk}`);
  for (const kk of kalshiDay.get(sd)) console.log(`    KALSHI: ${kk}`);
}

// And triples — strikes that exist on both venues regardless of date.
const polyTriple = new Map();
for (const k of polyKeys.keys()) {
  const [u, d, s] = k.split('|');
  const t = `${u}|${d}|${s}`;
  if (!polyTriple.has(t)) polyTriple.set(t, []);
  polyTriple.get(t).push(k);
}
const kalshiTriple = new Map();
for (const k of kalshiKeys.keys()) {
  const [u, d, s] = k.split('|');
  const t = `${u}|${d}|${s}`;
  if (!kalshiTriple.has(t)) kalshiTriple.set(t, []);
  kalshiTriple.get(t).push(k);
}

const sharedTriples = [...polyTriple.keys()].filter(t => kalshiTriple.has(t));
console.log(`\n--- Triples present on both venues regardless of date: ${sharedTriples.length} ---`);
