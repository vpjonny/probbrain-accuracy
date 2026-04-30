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

export const UNDERLYINGS = {
  BTC: {
    aliases: ['bitcoin', 'btc', '₿'],
    category_hints: ['crypto', 'bitcoin'],
    kalshi_series: ['KXBTC', 'KXBTCD', 'KXBTCMAXY'],
  },
  ETH: {
    aliases: ['ethereum', 'eth'],
    category_hints: ['crypto', 'ethereum'],
    kalshi_series: ['KXETH', 'KXETHD'],
  },
  SOL: {
    aliases: ['solana', 'sol'],
    category_hints: ['crypto', 'solana'],
    kalshi_series: ['KXSOL', 'KXSOLD'],
  },
  FED_RATE: {
    aliases: ['federal funds rate', 'fed funds', 'fomc', 'fed rate', 'interest rate decision'],
    category_hints: ['economics', 'fed', 'interest rates'],
    kalshi_series: ['KXFED', 'FED'],
  },
  CPI: {
    aliases: ['cpi', 'consumer price index', 'inflation print'],
    category_hints: ['economics', 'inflation'],
    kalshi_series: ['KXCPI', 'CPI'],
  },
  NFP: {
    aliases: ['nfp', 'nonfarm payrolls', 'non-farm payrolls', 'jobs report'],
    category_hints: ['economics', 'jobs'],
    kalshi_series: ['KXNFP', 'NFP'],
  },
};

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
