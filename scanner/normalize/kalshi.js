// scanner/normalize/kalshi.js
//
// Kalshi's schema is more regular than Polymarket's — series_ticker (or our
// _series_ticker_hint annotation) maps directly to underlying via the dict,
// and direction + strike come from yes_sub_title using a simpler regex set.
//
// Returns canonical key {underlying, direction, strike, resolution_date,
// resolution_type} or {skip: true, reason: "..."}.

import { matchUnderlyingByKalshiSeries } from '../dicts/underlyings.js';

const ABOVE_PATTERNS = /\bor above\b|\babove\b|\bover\b|≥|>=|>|\bat or above\b|\bgreater than\b|\bat least\b/i;
const BELOW_PATTERNS = /\bor below\b|\bbelow\b|\bunder\b|≤|<=|<|\bat or below\b|\bless than\b|\bat most\b/i;

function detectDirection(text) {
  const above = ABOVE_PATTERNS.test(text);
  const below = BELOW_PATTERNS.test(text);
  if (above && !below) return 'above';
  if (below && !above) return 'below';
  return null;
}

const STRIKE_REGEX = /\$?\s*(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(k|m|bn|%)?\b/i;
function parseStrike(text) {
  if (!text) return null;
  const m = text.match(STRIKE_REGEX);
  if (!m) return null;
  let n = parseFloat(m[1].replace(/,/g, ''));
  if (!Number.isFinite(n)) return null;
  const suffix = (m[2] || '').toLowerCase();
  if (suffix === 'k') n *= 1_000;
  else if (suffix === 'm') n *= 1_000_000;
  else if (suffix === 'bn') n *= 1_000_000_000;
  else if (suffix === '%') n /= 100;
  return n;
}

// Kalshi sometimes labels series explicitly as DAILY / WEEKLY in the ticker
// or close cadence. Detect with explicit hints first, then infer from the
// gap between open_time and close_time.
function detectResolutionType(market) {
  const ticker = (market.ticker || '').toUpperCase();
  const text = `${ticker} ${market.event_ticker || ''}`.toUpperCase();
  if (/\bH(OURLY)?\b|\bHR\b/.test(text)) return 'hourly';
  if (/\bDAILY\b|\bD\b/.test(text)) {
    // The single 'D' check is too loose, only honor the long form.
    if (/\bDAILY\b/.test(text)) return 'daily';
  }
  if (/\bWEEKLY\b|\bWK\b/.test(text)) return 'weekly';
  if (/\bMONTHLY\b/.test(text)) return 'monthly';
  if (/\bQUARTERLY\b|\bQTR\b/.test(text)) return 'quarterly';

  // Infer from gap. Kalshi has open_time and close_time on each market.
  const open = market.open_time ? Date.parse(market.open_time) : NaN;
  const close = market.close_time ? Date.parse(market.close_time) : NaN;
  if (Number.isFinite(open) && Number.isFinite(close)) {
    const hours = (close - open) / 3.6e6;
    if (hours < 6)         return 'hourly';
    if (hours < 36)        return 'daily';
    if (hours < 24 * 8)    return 'weekly';
    if (hours < 24 * 100)  return 'monthly';
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

export function normalizeKalshi(market) {
  // Step 1: underlying via series. Honor the explicit hint we annotated
  // during fetch first; if the Kalshi record carries series_ticker, match
  // that; finally fall back to ticker prefix parsing (everything before
  // the first dash).
  const seriesHint = market._series_ticker_hint
    || market.series_ticker
    || (market.event_ticker ? market.event_ticker.split('-')[0] : '')
    || (market.ticker ? market.ticker.split('-')[0] : '');
  const underlying = matchUnderlyingByKalshiSeries(seriesHint);
  if (!underlying) {
    return { skip: true, reason: 'kalshi_series_not_in_dict', context: { ticker: market.ticker, series: seriesHint } };
  }

  // Step 2: direction from yes_sub_title (preferred) or subtitle.
  const subtitle = market.yes_sub_title || market.subtitle || market.no_sub_title || '';
  const strikeType = String(market.strike_type || '').toLowerCase();
  // Check strike_type === 'between' early — these are price-range bins, not
  // threshold markets. They'd otherwise fall through to direction-unparseable.
  if (strikeType === 'between') {
    return { skip: true, reason: 'kalshi_strike_type_between_not_threshold', context: { ticker: market.ticker } };
  }
  let direction = detectDirection(subtitle);
  if (!direction) {
    if (strikeType === 'greater') direction = 'above';
    else if (strikeType === 'less') direction = 'below';
  }
  if (!direction) {
    return { skip: true, reason: 'kalshi_direction_unparseable', context: { ticker: market.ticker, sub: subtitle.slice(0, 60), strike_type: strikeType } };
  }

  // Step 3: strike.
  let strike = parseStrike(subtitle);
  if (strike == null) {
    // Last resort — pull from ticker suffix (e.g. T86299.99).
    const suffixMatch = (market.ticker || '').match(/-[A-Z](\d+(?:\.\d+)?)$/);
    if (suffixMatch) strike = parseFloat(suffixMatch[1]);
  }
  if (strike == null || !Number.isFinite(strike)) {
    return { skip: true, reason: 'kalshi_strike_unparseable', context: { ticker: market.ticker, sub: subtitle.slice(0, 60) } };
  }

  // Step 5: resolution_type
  const resolutionType = detectResolutionType(market);

  // Step 4: resolution_date — prefer expiration_time over close_time. close_time
  // is when the orderbook closes; expiration_time is when the market settles.
  // For monotonicity within a single platform either works but expiration_time
  // is the cleaner key for cross-platform matching later (Pass 5).
  const rawDate = market.expiration_time || market.close_time;
  if (!rawDate) {
    return { skip: true, reason: 'kalshi_resolution_date_unavailable', context: { ticker: market.ticker } };
  }
  const resolutionDate = formatResolutionDate(rawDate, resolutionType);
  if (!resolutionDate) {
    return { skip: true, reason: 'kalshi_resolution_date_unparseable', context: { ticker: market.ticker, raw: rawDate } };
  }

  return {
    underlying,
    direction,
    strike,
    resolution_date: resolutionDate,
    resolution_type: resolutionType,
  };
}
