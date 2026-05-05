import { USER_AGENT, FETCH_TIMEOUT_MS } from '../sources.js';
import { toUtcIso, canonicalUrl, cleanTitle, itemId } from './normalize.js';
import { fetchPageMeta } from './fetch-title.js';

async function fetchText(url) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  try {
    const r = await fetch(url, { headers: { 'User-Agent': USER_AGENT, 'Accept': 'application/xml, text/xml, */*' }, signal: ctrl.signal });
    if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
    return await r.text();
  } finally {
    clearTimeout(t);
  }
}

function parseSitemap(xml) {
  const out = [];
  const blocks = xml.match(/<url\b[\s\S]*?<\/url>/g) || [];
  for (const b of blocks) {
    const loc = (b.match(/<loc>\s*([\s\S]*?)\s*<\/loc>/) || [])[1];
    const lastmod = (b.match(/<lastmod>\s*([\s\S]*?)\s*<\/lastmod>/) || [])[1];
    if (loc) out.push({ url: loc.trim(), lastmod: lastmod ? lastmod.trim() : null });
  }
  return out;
}

function matchesFilter(url, filter) {
  if (!filter) return true;
  if (Array.isArray(filter)) return filter.some(f => url.includes(f));
  return url.includes(filter);
}

export async function fetchSitemap(source, knownIds) {
  const xml = await fetchText(source.url);
  const all = parseSitemap(xml);
  const filtered = all
    .filter(e => matchesFilter(e.url, source.filter))
    .filter(e => !source.exclude || !source.exclude.some(x => e.url.includes(x)));
  filtered.sort((a, b) => (b.lastmod || '').localeCompare(a.lastmod || ''));
  const limit = source.limit || 30;
  const picked = filtered.slice(0, limit);

  const out = [];
  for (const e of picked) {
    const url = canonicalUrl(e.url);
    const id = itemId(source.id, url);
    if (knownIds.has(id)) continue;
    let meta = null;
    try { meta = await fetchPageMeta(url, source.title || {}); } catch (err) { meta = null; }
    if (!meta?.title) continue;
    out.push({
      title: cleanTitle(meta.title),
      url,
      published_at: toUtcIso(e.lastmod) || toUtcIso(new Date()),
      description: source.skipDescription ? '' : (meta.description || ''),
    });
  }
  return out;
}
