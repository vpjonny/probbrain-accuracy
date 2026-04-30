// scanner/lib/persistence.js
//
// Roll up a per-opportunity history into a compact summary that gets embedded
// in opportunities.json. Frontend reads `persistence.trend` + `hours_persisted`
// + `gross_pct_history` to render the persistence pill and (optionally) a
// sparkline.
//
// Trend classification: linear-fit slope of gross_pct over the last
// HISTORY_WINDOW samples.
//   • slope ≥ +0.3pp/scan  → "widening"
//   • slope ≤ -0.3pp/scan  → "tightening"
//   • |slope| < 0.3        → "stable"
//   • <3 samples           → "new"
//
// Slope thresholds chosen so a multi-pp shift over a few hours registers but
// noise (±0.05pp wobble in mid-prices) doesn't.

const HISTORY_WINDOW = 10;
const TREND_SLOPE_THRESHOLD = 0.3;

// Linear regression slope (least-squares) of y vs x where x is sample index.
// Returns NaN if fewer than 2 samples.
export function linearSlope(values) {
  const n = values.length;
  if (n < 2) return NaN;
  let sx = 0, sy = 0, sxx = 0, sxy = 0;
  for (let i = 0; i < n; i++) {
    sx += i; sy += values[i];
    sxx += i * i; sxy += i * values[i];
  }
  const denom = n * sxx - sx * sx;
  if (denom === 0) return 0;
  return (n * sxy - sx * sy) / denom;
}

export function classifyTrend(grossPctHistory) {
  if (!Array.isArray(grossPctHistory) || grossPctHistory.length < 3) return 'new';
  const slope = linearSlope(grossPctHistory);
  if (!Number.isFinite(slope)) return 'new';
  if (slope >= TREND_SLOPE_THRESHOLD) return 'widening';
  if (slope <= -TREND_SLOPE_THRESHOLD) return 'tightening';
  return 'stable';
}

// Compute the persistence summary for a single opportunity.
// `priorSamples` is an array of compact samples (oldest-first) loaded from
// history.js for this opportunity ID. `currentSample` is today's freshly
// computed sample (already shaped — same projection as compactSample writes).
//
// Returns null if there are no prior samples and no current — caller should
// just omit the persistence field.
export function computePersistence(priorSamples, currentSample) {
  // Combine prior + current, oldest-first. The current sample is what's about
  // to be appended to history; we include it in the rollup so the embedded
  // summary already reflects "this scan."
  const all = [];
  if (Array.isArray(priorSamples)) all.push(...priorSamples);
  if (currentSample) all.push(currentSample);
  if (all.length === 0) return null;

  all.sort((a, b) => Date.parse(a.ts) - Date.parse(b.ts));

  const firstSeenAt = all[0].ts;
  const firstMs = Date.parse(firstSeenAt);
  const lastMs = Date.parse(all[all.length - 1].ts);
  const hoursPersisted = Number.isFinite(firstMs) && Number.isFinite(lastMs)
    ? +((lastMs - firstMs) / 3600_000).toFixed(2)
    : 0;

  const window = all.slice(-HISTORY_WINDOW);
  const grossPctHistory = window
    .map(s => s.edge_gross_pct)
    .filter(v => Number.isFinite(v))
    .map(v => +Number(v).toFixed(2));

  const trend = classifyTrend(grossPctHistory);

  return {
    first_seen_at: firstSeenAt,
    scans_seen: all.length,
    hours_persisted: hoursPersisted,
    gross_pct_history: grossPctHistory,
    trend,
  };
}
