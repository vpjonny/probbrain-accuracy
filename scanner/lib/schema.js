// scanner/lib/schema.js — opportunities.json is the contract between
// scanner and frontend. Bump SCHEMA_VERSION on any breaking shape change.

export const SCHEMA_VERSION = 1;

export function emptyOutput({ generatedAt, scanDurationMs }) {
  return {
    schema_version: SCHEMA_VERSION,
    generated_at: generatedAt,
    scan_duration_ms: scanDurationMs,
    errors: [],
    stats: {
      poly_markets_scanned: 0,
      kalshi_markets_scanned: 0,
      candidates_pre_filter: 0,
      tier1_count: 0,
      tier2_count: 0,
      tier3_count: 0,
    },
    opportunities: [],
  };
}

export function tallyTiers(opportunities) {
  const out = { tier1_count: 0, tier2_count: 0, tier3_count: 0 };
  for (const o of opportunities) {
    if (o.tier === 1) out.tier1_count++;
    else if (o.tier === 2) out.tier2_count++;
    else if (o.tier === 3) out.tier3_count++;
  }
  return out;
}

// Validate a single opportunity has the required shape. Returns null on success
// or a string explaining what's missing — used as a tripwire so we never write
// malformed cards to the wire.
export function validateOpportunity(o) {
  if (!o || typeof o !== 'object') return 'not an object';
  for (const k of ['id', 'tier', 'type', 'summary', 'legs', 'edge_gross_pct',
                   'edge_net_estimate_pct', 'max_executable_size_per_leg_usd',
                   'edge_net_per_dollar', 'weakest_link_summary']) {
    if (o[k] === undefined) return `missing field: ${k}`;
  }
  if (![1, 2, 3].includes(o.tier)) return `invalid tier: ${o.tier}`;
  if (!Array.isArray(o.legs) || o.legs.length === 0) return 'legs must be non-empty array';
  if (!Array.isArray(o.confidence_flags)) return 'confidence_flags must be array';
  return null;
}
