import { readdirSync, statSync, writeFileSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const BASE_URL = 'https://probbrain.com';

// Curated metadata for known top-level pages. Anything else gets the
// TOPLEVEL_META default so new pages are indexed without code changes.
const PAGE_META = {
  '/':            { priority: '1.0', changefreq: 'daily' },
  '/arbitrage':   { priority: '0.9', changefreq: 'hourly' },
  '/news':        { priority: '0.8', changefreq: 'daily' },
  '/kelly':       { priority: '0.7', changefreq: 'weekly' },
  '/methodology': { priority: '0.7', changefreq: 'monthly' },
  '/status':      { priority: '0.4', changefreq: 'hourly' },
};
const SIGNAL_META   = { priority: '0.5', changefreq: 'monthly' };
const TOPLEVEL_META = { priority: '0.6', changefreq: 'weekly' };

const EXCLUDE_TOPLEVEL = new Set(['404.html']);

// Signals with these statuses are drafts or internal paper-trades — keep them
// out of the sitemap so Google doesn't waste crawl budget on content we don't
// want indexed. WIN/LOSS/PENDING are real public calls and stay in.
const EXCLUDE_SIGNAL_STATUSES = new Set(['NOT_PUBLISHED', 'SHADOW']);

function readSignalStatus(filePath) {
  try {
    const html = readFileSync(filePath, 'utf8');
    const m = html.match(/Status:\s*([A-Z_]+)/);
    return m ? m[1] : null;
  } catch {
    return null;
  }
}

function htmlToUrl(file) {
  if (file === 'index.html') return '/';
  return '/' + file.replace(/\.html$/, '');
}

function fmtDate(d) { return d.toISOString().slice(0, 10); }

export function generateSitemap(repoRoot) {
  const entries = [];

  for (const f of readdirSync(repoRoot)) {
    if (!f.endsWith('.html') || EXCLUDE_TOPLEVEL.has(f)) continue;
    const url = htmlToUrl(f);
    const stat = statSync(join(repoRoot, f));
    entries.push({ url, lastmod: fmtDate(stat.mtime), ...(PAGE_META[url] || TOPLEVEL_META) });
  }

  const signalsDir = join(repoRoot, 'signals');
  let signalsExist = false;
  try { signalsExist = statSync(signalsDir).isDirectory(); } catch {}
  let skipped = 0;
  if (signalsExist) {
    for (const f of readdirSync(signalsDir).sort()) {
      if (!f.endsWith('.html')) continue;
      const path = join(signalsDir, f);
      const status = readSignalStatus(path);
      if (status && EXCLUDE_SIGNAL_STATUSES.has(status)) { skipped++; continue; }
      const stat = statSync(path);
      entries.push({ url: '/signals/' + f.replace(/\.html$/, ''), lastmod: fmtDate(stat.mtime), ...SIGNAL_META });
    }
  }

  // Root first, then alphabetical so output is deterministic across runs
  // and diffs only reflect real adds/removes.
  entries.sort((a, b) => a.url === '/' ? -1 : b.url === '/' ? 1 : a.url.localeCompare(b.url));

  const xml = '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
    entries.map(e =>
      `  <url><loc>${BASE_URL}${e.url}</loc><lastmod>${e.lastmod}</lastmod><changefreq>${e.changefreq}</changefreq><priority>${e.priority}</priority></url>`
    ).join('\n') + '\n</urlset>\n';

  const path = join(repoRoot, 'sitemap.xml');
  let prev = '';
  try { prev = readFileSync(path, 'utf8'); } catch {}
  if (prev !== xml) writeFileSync(path, xml, 'utf8');
  return { count: entries.length, changed: prev !== xml, skipped };
}
