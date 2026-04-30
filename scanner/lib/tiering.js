// scanner/lib/tiering.js — fee model + filter pipeline + tier assignment.
// Order matters: a stale price isn't symmetric with a small offset — it kills
// the opportunity regardless of how juicy the gross edge looks.

// ─────────────────────────────────────────────────────────────────────────────
// Fee model — April 2026 reality, conservative estimate.
// Round-trip on a $1k–$5k cross-platform crypto ladder arb is ~6–9%.
//
// Components:
//   • Polymarket dynamic taker — peaks ~1.8% at 50/50, lower at extremes.
//     Modeled as 0.02 * p * (1-p) / 0.25 per Polymarket leg.
//   • Kalshi — 0.07 * C * P * (1-P) per contract, worst-case ~1.75% at 0.50.
//   • Bid-ask round-trip on liquid ladders — 1–3% (use 1.5% mid).
//   • Polygon gas + USDC bridge friction — 0.3–0.8% (use 0.5% mid).
//   • Capital tie-up — 8% annualized × days_to_resolution / 365.
// ─────────────────────────────────────────────────────────────────────────────

const POLY_TAKER_PEAK = 0.02;       // 2% at 50/50
const KALSHI_FEE_COEF = 0.07;
const SPREAD_ROUND_TRIP_PCT = 1.5;
const GAS_BRIDGE_PCT = 0.5;
const CAPITAL_COST_ANNUAL_PCT = 8.0;

function clampPrice(p) { return Math.min(0.99, Math.max(0.01, Number(p) || 0.5)); }

export function estimateFeesPct({ legs = [], daysToResolution = 30 } = {}) {
  let polyTaker = 0;
  let kalshiFee = 0;

  for (const leg of legs) {
    const p = clampPrice(leg.price);
    if (leg.platform === 'polymarket') {
      // 0.02 * p * (1-p) / 0.25 * 100 → percentage on this leg's notional
      polyTaker += POLY_TAKER_PEAK * p * (1 - p) / 0.25 * 100;
    } else if (leg.platform === 'kalshi') {
      kalshiFee += KALSHI_FEE_COEF * p * (1 - p) * 100;
    }
  }

  const capital = (Math.max(0, daysToResolution) / 365) * CAPITAL_COST_ANNUAL_PCT;
  return polyTaker + kalshiFee + SPREAD_ROUND_TRIP_PCT + GAS_BRIDGE_PCT + capital;
}

// ─────────────────────────────────────────────────────────────────────────────
// Recency thresholds (minutes) per resolution_type.
// "required" = no penalty if fresher than this.
// "acceptable" = warning but tradeable.
// Older than acceptable → Tier 3 only.
// ─────────────────────────────────────────────────────────────────────────────

const RECENCY = {
  hourly:    { required: 5,    acceptable: 30 },
  daily:     { required: 60,   acceptable: 240 },
  weekly:    { required: 240,  acceptable: 720 },
  monthly:   { required: 1440, acceptable: 2880 },
  quarterly: { required: 1440, acceptable: 2880 },
};

const OFFSET_TOLERANCE_MIN = {
  hourly:    0,
  daily:     30,
  weekly:    240,
  monthly:   1440,
  quarterly: 1440,
};

function legAgeMin(leg) {
  if (!leg.last_trade_at) return null;
  const t = Date.parse(leg.last_trade_at);
  if (Number.isNaN(t)) return null;
  return Math.max(0, (Date.now() - t) / 60000);
}

export function recencyTier(legs, resolutionType) {
  const cfg = RECENCY[resolutionType] || RECENCY.monthly;
  let worst = 1;
  for (const leg of legs) {
    const age = legAgeMin(leg);
    if (age == null) continue;
    if (age > cfg.acceptable) worst = Math.max(worst, 3);
    else if (age > cfg.required) worst = Math.max(worst, 2);
  }
  return worst;
}

export function offsetTolerance(resolutionType) {
  return OFFSET_TOLERANCE_MIN[resolutionType] ?? OFFSET_TOLERANCE_MIN.monthly;
}

// gross_edge ≥ 8% AND survives all guards → Tier 1
// 4% < gross_edge ≤ 8% → Tier 2
// gross_edge ≤ 4% → Tier 3
export function edgeBaseTier(grossEdgePct) {
  if (grossEdgePct >= 8) return 1;
  if (grossEdgePct >= 4) return 2;
  return 3;
}

// Filter pipeline. Each step can only worsen the tier (downgrade).
// Returns { tier, flags[] } where flags are confidence-flag tags.
export function assignTier({
  grossEdgePct,
  legs = [],
  resolutionType = 'monthly',
  hasOffsetWarning = false,
  depthSeverelyCapped = false,
  netEdgePct = null,
} = {}) {
  let tier = edgeBaseTier(grossEdgePct);
  const flags = [];

  const rTier = recencyTier(legs, resolutionType);
  if (rTier === 3) { tier = 3; flags.push('stale_price'); }
  else if (rTier === 2) { tier = Math.min(3, Math.max(tier, 2)); flags.push('stale_price'); }

  if (hasOffsetWarning) { tier = Math.min(3, tier + 1); flags.push('offset_warning'); }
  if (depthSeverelyCapped) { tier = Math.min(3, tier + 1); flags.push('depth_limited'); }

  if (grossEdgePct < 8 && grossEdgePct >= 4) flags.push('fee_tight');
  if (netEdgePct != null && grossEdgePct > 0 && Math.abs(netEdgePct) < grossEdgePct * 0.5) {
    if (!flags.includes('fee_tight')) flags.push('fee_tight');
  }

  return { tier, flags };
}
