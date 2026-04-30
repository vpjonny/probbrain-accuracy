// scanner/normalize/polymarket.js
//
// Returns canonical key {underlying, direction, strike, resolution_date,
// resolution_type} or {skip: true, reason: "..."}.
//
// The skip log IS the debugging surface — when expected matches don't appear,
// the skip reasons tell you which step in the field hierarchy gave up. Be
// specific. "underlying not in dict (slug=will-arsenal-...)" beats "no match".
//
// No fuzzy matching anywhere in this file. Every step is exact equality or a
// regex matching a specific pattern. Adding a new market type that doesn't
// fit the existing patterns is a code change in this file.

import {
  matchUnderlyingByText,
  matchUnderlyingByCategory,
  strikeOutOfRange,
} from '../dicts/underlyings.js';
import { parseStrike } from '../lib/strike.js';

// ── Step 2: direction detection ──────────────────────────────────────────────
const ABOVE_PATTERNS = /(\babove\b|\bover\b|≥|>=|>|reach(es)?|hit(s)?|exceed(s)?|\bgreater than\b|\bat least\b)/i;
const BELOW_PATTERNS = /(\bbelow\b|\bunder\b|≤|<=|<|\bstays? under\b|\bdoes ?not reach\b|\bless than\b|\bat most\b)/i;

function detectDirection(text) {
  const above = ABOVE_PATTERNS.test(text);
  const below = BELOW_PATTERNS.test(text);
  if (above && !below) return 'above';
  if (below && !above) return 'below';
  return null;
}

// Step 3: strike extraction lives in lib/strike.js (shared with Kalshi).

// ── Step 4 & 5: resolution date + type ──────────────────────────────────────
const TYPE_PATTERNS = [
  ['hourly',    /\bhourly\b|\bhour-by\b|\bevery hour\b/i],
  ['daily',     /\bdaily\b|\btoday\b|\btomorrow\b/i],
  ['weekly',    /\bweekly\b|\bweek-of\b|\bthis week\b/i],
  ['monthly',   /\bmonthly\b/i],
  ['quarterly', /\bquarterly\b|\bquarter\b/i],
];

function detectResolutionType(text, endDate) {
  for (const [name, re] of TYPE_PATTERNS) {
    if (re.test(text)) return name;
  }
  // Infer from time-to-end. Conservative: prefer the longer type when
  // ambiguous — calling a daily market "hourly" would tighten staleness
  // thresholds inappropriately.
  if (Number.isFinite(endDate)) {
    const hoursToEnd = (endDate - Date.now()) / 3.6e6;
    if (hoursToEnd <= 0)        return 'hourly';
    if (hoursToEnd < 6)         return 'hourly';
    if (hoursToEnd < 36)        return 'daily';
    if (hoursToEnd < 24 * 8)    return 'weekly';
    if (hoursToEnd < 24 * 100)  return 'monthly';
    return 'quarterly';
  }
  return 'monthly';
}

function formatResolutionDate(rawDate, resolutionType) {
  if (!rawDate) return null;
  const t = Date.parse(rawDate);
  if (Number.isNaN(t)) return null;
  const d = new Date(t);
  const yyyy = d.getUTCFullYear();
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(d.getUTCDate()).padStart(2, '0');
  if (resolutionType === 'hourly') {
    const hh = String(d.getUTCHours()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}T${hh}:00:00Z`;
  }
  return `${yyyy}-${mm}-${dd}`;
}

// ── normalize ────────────────────────────────────────────────────────────────
export function normalizePolymarket(market, event = {}) {
  const eventSlug = event.slug || '';
  const eventTitle = event.title || '';
  const marketQuestion = market.question || market.groupItemTitle || '';
  const marketSlug = market.slug || '';

  // Step 1: underlying — category first (authoritative), then alias scan.
  const tagLabels = Array.isArray(event.tags)
    ? event.tags.map(t => (t && typeof t === 'object') ? (t.label || '') : String(t || ''))
    : [];
  let underlying = matchUnderlyingByCategory(event.category, tagLabels);
  if (!underlying) {
    underlying = matchUnderlyingByText(eventSlug, eventTitle, marketQuestion, marketSlug);
  }
  if (!underlying) {
    return { skip: true, reason: 'underlying_not_in_dict', context: { event_slug: eventSlug, market_id: market.id } };
  }

  // Step 2: direction. ONLY use market-level text (question + groupItemTitle).
  // Event titles like "What price will Bitcoin hit?" contain "hit" which would
  // match ABOVE_PATTERNS, so a child market like "Will BTC dip to $65k" gets
  // mis-tagged as "above" when it's actually a "drops to" market that
  // shouldn't be grouped with above-X strike ladders at all.
  const directionText = `${marketQuestion} ${market.groupItemTitle || ''}`;
  const direction = detectDirection(directionText);
  if (!direction) {
    return { skip: true, reason: 'direction_ambiguous', context: { market_id: market.id, q: marketQuestion.slice(0, 60) } };
  }

  // Step 3: strike — prefer groupItemTitle (often "$100,000" or "above 3.0%")
  // because the question can have multiple numbers; fall back to question.
  let strike = parseStrike(market.groupItemTitle);
  if (strike == null) strike = parseStrike(marketQuestion);
  if (strike == null) {
    return { skip: true, reason: 'strike_unparseable', context: { market_id: market.id, group: market.groupItemTitle, q: marketQuestion.slice(0, 60) } };
  }
  // Sanity check: strike must be in the underlying's plausible range. Catches
  // cross-asset slips where Bitcoin alias matched but the actual market is
  // about something else priced in different units (e.g. a $800M market cap
  // matched as BTC because the event mentioned BTC tangentially).
  const rangeErr = strikeOutOfRange(underlying, strike);
  if (rangeErr) {
    return { skip: true, reason: 'strike_out_of_plausible_range', context: { market_id: market.id, underlying, strike, detail: rangeErr } };
  }

  // Step 5: resolution_type (need it before formatting date)
  const resolutionType = detectResolutionType(
    `${eventSlug} ${eventTitle} ${marketQuestion}`,
    market.endDate ? Date.parse(market.endDate) : NaN,
  );

  // Step 4: resolution_date from market.endDate
  if (!market.endDate) {
    return { skip: true, reason: 'resolution_date_unavailable', context: { market_id: market.id } };
  }
  const resolutionDate = formatResolutionDate(market.endDate, resolutionType);
  if (!resolutionDate) {
    return { skip: true, reason: 'resolution_date_unparseable', context: { market_id: market.id, raw: market.endDate } };
  }

  return {
    underlying,
    direction,
    strike,
    resolution_date: resolutionDate,
    resolution_type: resolutionType,
  };
}
