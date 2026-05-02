export function toUtcIso(input) {
  if (!input) return null;
  const d = input instanceof Date ? input : new Date(input);
  if (isNaN(d.getTime())) return null;
  return d.toISOString().replace(/\.\d{3}Z$/, 'Z');
}

export function canonicalUrl(raw) {
  if (!raw) return null;
  try {
    const u = new URL(raw);
    u.hash = '';
    const drop = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content', 'ref', 'ref_src', 'ref_url'];
    for (const k of drop) u.searchParams.delete(k);
    u.hostname = u.hostname.toLowerCase();
    if (u.pathname.endsWith('/') && u.pathname.length > 1) u.pathname = u.pathname.slice(0, -1);
    return u.toString();
  } catch {
    return raw;
  }
}

export function itemId(sourceId, url) {
  return `${sourceId}|${canonicalUrl(url)}`;
}

export function cleanTitle(s) {
  if (!s) return '';
  return s.replace(/\s+/g, ' ').replace(/ /g, ' ').trim();
}

export function buildHashtags(source, category) {
  const out = [];
  if (category && !out.includes(category)) out.push(category);
  if (source.hashtag && !out.includes(source.hashtag)) out.push(source.hashtag);
  return out;
}
