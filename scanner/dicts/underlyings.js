// scanner/dicts/underlyings.js
//
// Hardcoded — not derived. Adding a new underlying is intentionally a manual
// code change. Fuzzy matching on this layer would silently produce wrong
// matches (ETH ↔ ETHE, BTC ↔ BCH) and the scanner would output fake arbs.
// Don't.
//
// Each entry:
//   aliases:        case-insensitive substrings to match in slug/title with
//                   word-boundary awareness (BCH should not match BTC).
//   category_hints: Polymarket event.category / event.tags labels that lock
//                   the underlying when present (preferred over slug parsing).
//   kalshi_series:  Kalshi series_ticker prefixes that map to this underlying.
//   strike_range:   [min, max] sanity bounds. Strikes outside the range are
//                   rejected with reason "strike_out_of_plausible_range".
//                   Catches cross-asset slips: a "MegaETH market cap $800M"
//                   market shouldn't match BTC just because the event slug
//                   mentioned bitcoin tangentially. Rate ranges are decimal
//                   (0.05 = 5%).

export const UNDERLYINGS = {
  BTC: {
    aliases: ['bitcoin', 'btc', '₿'],
    category_hints: ['crypto', 'bitcoin'],
    kalshi_series: ['KXBTC', 'KXBTCD', 'KXBTCMAXY'],
    strike_range: [1_000, 5_000_000],
  },
  ETH: {
    aliases: ['ethereum', 'eth'],
    category_hints: ['crypto', 'ethereum'],
    kalshi_series: ['KXETH', 'KXETHD'],
    strike_range: [50, 50_000],
  },
  SOL: {
    aliases: ['solana', 'sol'],
    category_hints: ['crypto', 'solana'],
    kalshi_series: ['KXSOL', 'KXSOLD'],
    strike_range: [1, 5_000],
  },
  FED_RATE: {
    aliases: ['federal funds rate', 'fed funds', 'fomc', 'fed rate', 'interest rate decision'],
    category_hints: ['economics', 'fed', 'interest rates'],
    kalshi_series: ['KXFED', 'FED'],
    strike_range: [0, 0.20],
  },
  CPI: {
    aliases: ['cpi', 'consumer price index', 'inflation print'],
    category_hints: ['economics', 'inflation'],
    kalshi_series: ['KXCPI', 'CPI'],
    strike_range: [-0.05, 0.30],
  },
  NFP: {
    aliases: ['nfp', 'nonfarm payrolls', 'non-farm payrolls', 'jobs report'],
    category_hints: ['economics', 'jobs'],
    kalshi_series: ['KXNFP', 'NFP'],
    strike_range: [-1_000_000, 5_000_000],
  },
};

// Sanity-check a parsed strike against the underlying's plausible range.
// Returns null if in range, else a string reason for the skip log.
export function strikeOutOfRange(underlying, strike) {
  const entry = UNDERLYINGS[underlying];
  if (!entry || !entry.strike_range) return null;
  const [lo, hi] = entry.strike_range;
  if (!Number.isFinite(strike)) return 'strike_not_finite';
  if (strike < lo || strike > hi) {
    return `strike_${strike}_outside_${underlying}_range_[${lo},${hi}]`;
  }
  return null;
}

const ALIAS_REGEX_CACHE = new Map();
function aliasRegex(alias) {
  if (ALIAS_REGEX_CACHE.has(alias)) return ALIAS_REGEX_CACHE.get(alias);
  // Word-boundary aware substring match. Symbols (₿) get a permissive boundary.
  const escaped = alias.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const isAllAlpha = /^[a-z]+$/i.test(alias);
  const r = isAllAlpha
    ? new RegExp(`\\b${escaped}\\b`, 'i')
    : new RegExp(escaped, 'i');
  ALIAS_REGEX_CACHE.set(alias, r);
  return r;
}

// Match underlying via aliases against any of the provided text fields.
// Returns the underlying key (e.g. "BTC") or null.
export function matchUnderlyingByText(...texts) {
  const blob = texts.filter(Boolean).join(' ');
  if (!blob) return null;
  for (const [key, entry] of Object.entries(UNDERLYINGS)) {
    for (const alias of entry.aliases) {
      if (aliasRegex(alias).test(blob)) return key;
    }
  }
  return null;
}

// Match underlying via Polymarket category_hints (preferred — authoritative).
export function matchUnderlyingByCategory(category, tagLabels = []) {
  const hints = [String(category || '').toLowerCase(), ...tagLabels.map(t => String(t || '').toLowerCase())];
  for (const [key, entry] of Object.entries(UNDERLYINGS)) {
    for (const h of entry.category_hints) {
      if (hints.includes(h.toLowerCase())) return key;
    }
  }
  return null;
}

// Match Kalshi series_ticker prefix → underlying. Strict prefix match.
export function matchUnderlyingByKalshiSeries(seriesTicker) {
  if (!seriesTicker) return null;
  const t = String(seriesTicker).toUpperCase();
  for (const [key, entry] of Object.entries(UNDERLYINGS)) {
    for (const prefix of entry.kalshi_series) {
      if (t === prefix || t.startsWith(prefix)) return key;
    }
  }
  return null;
}
