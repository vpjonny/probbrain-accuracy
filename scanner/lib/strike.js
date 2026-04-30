// scanner/lib/strike.js — shared strike parser used by both normalizers.
//
// Naive number-grab is unsafe — "Will Bitcoin hit $150k by June 30, 2026?"
// has both $150k (real strike) and 30 (a date day), and a groupItemTitle of
// "April 30" silently became strike=30 in our first version. Rules in
// priority order:
//
//   1. $-prefixed number with optional k/m/bn  →  dollar amount
//   2. number followed by %                    →  decimal rate
//   3. bare number with a k/m/bn suffix        →  expanded amount
//   4. number with a thousands-separator       →  as-is (real strike signal)
//   5. text is JUST a number (no surrounding non-digit-comma chars) → as-is
//   6. otherwise → null (don't guess from random numbers in prose)

const NUMBER_BODY = '\\d{1,3}(?:,\\d{3})+(?:\\.\\d+)?|\\d+(?:\\.\\d+)?';
const RE_DOLLAR     = new RegExp(`\\$\\s*(${NUMBER_BODY})\\s*(k|m|bn)?\\b`, 'i');
const RE_PERCENT    = new RegExp(`(${NUMBER_BODY})\\s*%`, 'i');
const RE_KMB_SUFFIX = new RegExp(`\\b(${NUMBER_BODY})\\s*(k|m|bn)\\b`, 'i');
const RE_THOUSANDS  = new RegExp(`\\b(\\d{1,3}(?:,\\d{3})+(?:\\.\\d+)?)\\b`);
const RE_BARE_ONLY  = new RegExp(`^\\s*(${NUMBER_BODY})\\s*$`);

function expandSuffix(n, suffix) {
  const s = (suffix || '').toLowerCase();
  if (s === 'k')  return n * 1_000;
  if (s === 'm')  return n * 1_000_000;
  if (s === 'bn') return n * 1_000_000_000;
  return n;
}
function toNumber(raw) {
  const n = parseFloat(String(raw).replace(/,/g, ''));
  return Number.isFinite(n) ? n : null;
}

export function parseStrike(text) {
  if (!text) return null;
  let m;
  if ((m = text.match(RE_DOLLAR))) {
    const n = toNumber(m[1]);
    return n == null ? null : expandSuffix(n, m[2]);
  }
  if ((m = text.match(RE_PERCENT))) {
    const n = toNumber(m[1]);
    return n == null ? null : n / 100;
  }
  if ((m = text.match(RE_KMB_SUFFIX))) {
    const n = toNumber(m[1]);
    return n == null ? null : expandSuffix(n, m[2]);
  }
  if ((m = text.match(RE_THOUSANDS))) return toNumber(m[1]);
  if ((m = text.match(RE_BARE_ONLY))) return toNumber(m[1]);
  return null;
}
