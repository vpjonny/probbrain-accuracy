import { USER_AGENT, FETCH_TIMEOUT_MS } from '../sources.js';
import { toUtcIso, canonicalUrl, cleanTitle, itemId } from './normalize.js';
import { fetchPageMeta } from './fetch-title.js';

async function fetchText(url) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  try {
    const r = await fetch(url, { headers: { 'User-Agent': USER_AGENT, 'Accept': 'text/html' }, redirect: 'follow', signal: ctrl.signal });
    if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
    return await r.text();
  } finally {
    clearTimeout(t);
  }
}

export async function fetchHtmlIndex(source, knownIds) {
  const html = await fetchText(source.url);
  const re = new RegExp(`href=["']([^"']*${source.urlPattern}[^"']*)["']`, 'gi');
  const seen = new Set();
  const candidates = [];
  let m;
  while ((m = re.exec(html)) !== null) {
    let href = m[1];
    if (href.startsWith('/')) {
      const base = new URL(source.url);
      href = base.origin + href;
    }
    if (!/^https?:\/\//.test(href)) continue;
    if (source.excludeRe && source.excludeRe.some(rx => new RegExp(rx).test(href))) continue;
    const url = canonicalUrl(href);
    if (seen.has(url)) continue;
    seen.add(url);
    candidates.push(url);
  }
  const limit = source.limit || 20;
  const picked = candidates.slice(0, limit);

  const now = toUtcIso(new Date());
  const out = [];
  for (const url of picked) {
    const id = itemId(source.id, url);
    if (knownIds.has(id)) continue;
    let meta = null;
    try { meta = await fetchPageMeta(url, source.title || {}); } catch { meta = null; }
    if (!meta?.title) continue;
    out.push({
      title: cleanTitle(meta.title),
      url,
      published_at: now,
      description: source.skipDescription ? '' : (meta.description || ''),
    });
  }
  return out;
}
