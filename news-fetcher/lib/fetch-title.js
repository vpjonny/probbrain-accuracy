import { USER_AGENT, FETCH_TIMEOUT_MS } from '../sources.js';

function decodeHtml(s) {
  return (s || '')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&#x27;/g, "'").replace(/&nbsp;/g, ' ')
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(+n));
}

function applyClean(title, cleanList) {
  if (!title || !cleanList) return title;
  let t = title;
  for (const pattern of cleanList) {
    if (typeof pattern === 'string') {
      t = t.split(pattern).join('');
    } else if (pattern instanceof RegExp) {
      t = t.replace(pattern, '');
    }
  }
  return t.trim();
}

function extract(html) {
  const og = html.match(/<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']/i)
          || html.match(/<meta[^>]+content=["']([^"']+)["'][^>]+property=["']og:title["']/i);
  const tw = html.match(/<meta[^>]+name=["']twitter:title["'][^>]+content=["']([^"']+)["']/i);
  const tt = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  const ld = html.match(/"headline"\s*:\s*"([^"]+)"/);
  return {
    og: og ? decodeHtml(og[1]).trim() : null,
    twitter: tw ? decodeHtml(tw[1]).trim() : null,
    title: tt ? decodeHtml(tt[1]).replace(/\s+/g, ' ').trim() : null,
    headline: ld ? decodeHtml(ld[1]).trim() : null,
  };
}

export async function fetchTitle(url, opts = {}) {
  const { prefer = ['og', 'twitter', 'headline', 'title'], clean = null } = opts;
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  try {
    const r = await fetch(url, { headers: { 'User-Agent': USER_AGENT, 'Accept': 'text/html' }, redirect: 'follow', signal: ctrl.signal });
    if (!r.ok) throw new Error(`title fetch ${url}: HTTP ${r.status}`);
    const html = (await r.text()).slice(0, 200_000);
    const fields = extract(html);
    for (const key of prefer) {
      if (fields[key]) return applyClean(fields[key], clean);
    }
    return null;
  } finally {
    clearTimeout(t);
  }
}
