// scanner/lib/canonical.js — canonical key serialization + grouping.
//
// The matching pass (Pass 5) groups Polymarket and Kalshi markets by exact
// canonical-key string equality. No fuzzy logic. If two markets on the same
// platform produce the same canonical key, that's a normalization bug — log
// loudly but don't crash.

// Round strike to a deterministic precision so 100000 and 100000.0 hash the
// same. 4 decimal places handles both whole-dollar strikes and percentage
// rates (which are stored as decimals like 0.0525).
function roundStrike(s) {
  if (!Number.isFinite(s)) return null;
  return Math.round(s * 10_000) / 10_000;
}

export function serializeCanonicalKey({ underlying, direction, strike, resolution_date, resolution_type }) {
  const r = roundStrike(strike);
  return `${underlying}|${direction}|${r}|${resolution_date}|${resolution_type}`;
}

// Group an array of normalized markets by canonical key.
// Each item must have shape: { canonical, market, ...rest }
// Returns Map<canonical_string, items[]>.
export function groupByCanonical(items) {
  const map = new Map();
  for (const item of items) {
    const k = serializeCanonicalKey(item.canonical);
    if (!map.has(k)) map.set(k, []);
    map.get(k).push(item);
  }
  return map;
}

// Detect collisions on a single platform. Same canonical key from two markets
// of the same platform = normalization is producing identical keys for
// distinct markets, which means matching will be wrong. Logs but never throws.
export function logCollisions(map, platform, log) {
  let collisions = 0;
  for (const [key, items] of map.entries()) {
    const samePlatform = items.filter(i => i.market.platform === platform);
    if (samePlatform.length > 1) {
      collisions++;
      log.warn(`canonical-key collision on ${platform}: key=${key} n=${samePlatform.length} ids=[${samePlatform.map(i => i.market.id).join(', ')}]`);
    }
  }
  return collisions;
}
