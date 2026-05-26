#!/usr/bin/env node
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { homedir } from 'node:os';
import { mkdir } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import { SOURCES, CATEGORIES, ARXIV_INTERVAL_MS } from './sources.js';
import { itemId, itemAnchor, buildHashtags, toUtcIso } from './lib/normalize.js';
import { readJson, writeJsonAtomic, indexBy } from './lib/persist.js';
import { fetchRss } from './lib/fetch-rss.js';
import { fetchHn } from './lib/fetch-hn.js';
import { fetchHf } from './lib/fetch-hf.js';
import { fetchGithubTrending } from './lib/fetch-github.js';
import { fetchSitemap } from './lib/fetch-sitemap.js';
import { fetchHtmlIndex } from './lib/fetch-html-index.js';
import { fetchPageMeta } from './lib/fetch-title.js';
import { summarize } from './lib/summarize.js';
import { loadEnv, require_ } from './lib/env.js';
import { formatPost, formatDigest as formatTgDigest, sendMessage } from './lib/telegram.js';
import { createBlueskyClient, postNewsItem as postBskyItem, postDigest as postBskyDigest } from './lib/bluesky.js';
import { createXClient, pickAllRecent, postThread as postXThread } from './lib/x.js';
import { generateSitemap } from './lib/sitemap.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..');
const NEWS_JSON = join(REPO_ROOT, 'news.json');
const NEWS_FEED = join(REPO_ROOT, 'news.xml');
const STATUS_JSON = join(REPO_ROOT, 'status.json');
const OPPORTUNITIES_JSON = join(REPO_ROOT, 'opportunities.json');
const PUBLISHED_SIGNALS = join(REPO_ROOT, 'data', 'published_signals.json');
const LAST_POSTED = join(__dirname, 'last_posted.json');
const LAST_POSTED_BSKY = join(__dirname, 'last_posted_bsky.json');
const LAST_POSTED_X = join(__dirname, 'last_posted_x.json');
// Shared with the Python signal publisher (pipeline/x_publisher.py) so every
// outbound tweet — news digest or signal thread — quotes whatever this account
// posted last, regardless of which subsystem sent it.
const LAST_X_TWEET = join(homedir(), '.config', 'probbrain', 'last_x_tweet.json');
const DEFAULT_PER_SOURCE_KEEP = 30;
const FEED_LIMIT = 60;
const SUMMARY_MAX_PER_RUN = 8;
const DESC_BACKFILL_MAX_PER_RUN = 12;
const TELEGRAM_THROTTLE_MS = 1100;
const TELEGRAM_MAX_PER_RUN = 30;
const BSKY_THROTTLE_MS = 1100;
const BSKY_MAX_PER_RUN = 25;
const X_DIGEST_WINDOW_MS = 2 * 60 * 60 * 1000;
const X_MIN_INTERVAL_MS = 2 * 60 * 60 * 1000;
const X_DIGEST_MIN_ITEMS = 3;
const X_DIGEST_PICK = 3;

const argv = new Set(process.argv.slice(2));
const DRY_RUN = argv.has('--dry-run');
const VERBOSE = argv.has('--verbose');
const NO_POST = argv.has('--no-post');
const NO_BSKY = argv.has('--no-bsky');
const NO_TELEGRAM = argv.has('--no-telegram');
const NO_X = argv.has('--no-x');
const NO_PUSH = argv.has('--no-push');
const log = (...a) => console.log(`[${toUtcIso(new Date())}]`, ...a);
const vlog = (...a) => { if (VERBOSE) log(...a); };

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function fetchSource(source, knownIds) {
  switch (source.type) {
    case 'rss':        return await fetchRss(source);
    case 'hn':         return await fetchHn(source, knownIds);
    case 'hf':         return await fetchHf(source);
    case 'github':     return await fetchGithubTrending(source);
    case 'sitemap':    return await fetchSitemap(source, knownIds);
    case 'html-index': return await fetchHtmlIndex(source, knownIds);
    default: throw new Error(`unknown source type: ${source.type}`);
  }
}

async function run() {
  const existing = await readJson(NEWS_JSON, { generated_at: null, items: [] });
  const byId = indexBy(existing.items || [], it => it.id);
  const knownIds = new Set(byId.keys());
  vlog(`existing news.json: ${byId.size} items`);

  let lastArxivAt = 0;
  const stats = { sources: 0, fetched: 0, new: 0, errors: 0, summarized: 0, summarizeFails: 0 };

  for (const source of SOURCES) {
    if (source.disabled) {
      vlog(`  ${source.id}: SKIP (disabled — ${source.note || 'no reason given'})`);
      continue;
    }
    if (source.id.startsWith('arxiv-')) {
      const wait = ARXIV_INTERVAL_MS - (Date.now() - lastArxivAt);
      if (wait > 0) await sleep(wait);
      lastArxivAt = Date.now();
    }
    let raw;
    try {
      raw = await fetchSource(source, knownIds);
    } catch (e) {
      stats.errors++;
      log(`ERR ${source.id}: ${e.message}`);
      continue;
    }
    stats.sources++;
    stats.fetched += raw.length;
    const cat = CATEGORIES[source.category];
    let added = 0;
    for (const it of raw) {
      if (!it.url || !it.title) continue;
      const id = itemId(source.id, it.url);
      if (byId.has(id)) continue;
      const item = {
        id,
        anchor: itemAnchor(id),
        source_id: source.id,
        source_name: source.name,
        category: source.category,
        category_emoji: cat.emoji,
        hashtags: buildHashtags(source, source.category),
        title: it.title,
        headline: it.title,
        url: it.url,
        published_at: it.published_at || toUtcIso(new Date()),
        // discovered_at = when ProbBrain first saw it. Drives the "ago" badge
        // on /news so timing matches Telegram/Bluesky notifs, not the source's
        // original publish time (which can be hours stale for HN-trending links).
        discovered_at: toUtcIso(new Date()),
        description: it.description || '',
        summarize: !!source.summarize,
        summarized: false,
        summarized_at: null,
      };
      byId.set(id, item);
      added++;
    }
    stats.new += added;
    vlog(`  ${source.id}: fetched=${raw.length} new=${added}`);
  }

  // Backfill descriptions for sitemap/html-index items that predate
  // og:description extraction. Newest-first so freshly visible items get
  // their card filled in soonest.
  const backfillCandidates = [...byId.values()]
    .filter(it => !it.description)
    .filter(it => {
      const s = SOURCES.find(x => x.id === it.source_id);
      return s && (s.type === 'sitemap' || s.type === 'html-index') && !s.skipDescription;
    })
    .sort((a, b) => (b.published_at || '').localeCompare(a.published_at || ''))
    .slice(0, DESC_BACKFILL_MAX_PER_RUN);

  for (const it of backfillCandidates) {
    if (DRY_RUN) { vlog(`(dry) would backfill desc for ${it.id}`); continue; }
    const s = SOURCES.find(x => x.id === it.source_id);
    try {
      const meta = await fetchPageMeta(it.url, s.title || {});
      if (meta?.description) {
        it.description = meta.description;
        stats.descBackfilled = (stats.descBackfilled || 0) + 1;
        vlog(`  ✓ desc backfilled ${it.id}`);
      }
    } catch (e) {
      vlog(`  desc backfill failed ${it.id}: ${e.message}`);
    }
  }

  const toSummarize = [...byId.values()]
    .filter(it => it.summarize && !it.summarized)
    .sort((a, b) => (b.published_at || '').localeCompare(a.published_at || ''))
    .slice(0, SUMMARY_MAX_PER_RUN);

  for (const it of toSummarize) {
    if (DRY_RUN) { vlog(`(dry) would summarize ${it.id}`); continue; }
    try {
      const abstract = it.description;
      const sum = await summarize({ source_name: it.source_name, title: it.title, abstract });
      it.headline = sum;
      it.summarized = true;
      it.summarized_at = toUtcIso(new Date());
      stats.summarized++;
      vlog(`  ✓ summarized ${it.id}`);
    } catch (e) {
      stats.summarizeFails++;
      log(`SUMMARY ERR ${it.id}: ${e.message}`);
    }
  }

  for (const it of byId.values()) {
    if (!it.anchor) it.anchor = itemAnchor(it.id);
  }

  const grouped = new Map();
  for (const it of byId.values()) {
    if (!grouped.has(it.source_id)) grouped.set(it.source_id, []);
    grouped.get(it.source_id).push(it);
  }
  const sourceCap = id => {
    const s = SOURCES.find(x => x.id === id);
    return (s && s.keep) || (s && s.limit) || DEFAULT_PER_SOURCE_KEEP;
  };
  const kept = [];
  for (const [sid, list] of grouped) {
    list.sort((a, b) => (b.published_at || '').localeCompare(a.published_at || ''));
    kept.push(...list.slice(0, sourceCap(sid)));
  }
  const items = kept.sort((a, b) => (b.published_at || '').localeCompare(a.published_at || ''));

  const out = { generated_at: toUtcIso(new Date()), items };

  if (DRY_RUN) {
    log(`(dry) would write news.json with ${items.length} items`);
    log(`(dry) would write news.xml with ${Math.min(items.length, FEED_LIMIT)} items`);
  } else {
    await writeJsonAtomic(NEWS_JSON, out);
    log(`wrote news.json: ${items.length} items (${stats.new} new, ${stats.summarized} summarized, ${stats.descBackfilled || 0} desc backfilled, ${stats.errors} fetch errors, ${stats.summarizeFails} summary errors)`);
    const { writeFile } = await import('node:fs/promises');
    const xml = renderRssFeed(items.slice(0, FEED_LIMIT));
    await writeFile(NEWS_FEED, xml, 'utf8');
    log(`wrote news.xml: ${Math.min(items.length, FEED_LIMIT)} items`);
  }

  if (DRY_RUN) return;

  // Push news.json + news.xml live BEFORE we notify subscribers — Telegram and
  // Bluesky posts deep-link to probbrain.com/news#anchor, and that anchor
  // doesn't exist on the live site until Vercel sees the commit.
  if (!NO_PUSH && stats.new > 0) gitPushNews(stats.new);

  if (!NO_POST) {
    if (!NO_TELEGRAM) await postToTelegram(items);
    if (!NO_BSKY)     await postToBluesky(items);
    if (!NO_X)        await postToX(items);
  }

  // Status snapshot reads gitignored last_posted*.json (which we own) and
  // surfaces aggregate latency to the public /status page.
  await writeStatusJson(items);

  // Regenerate sitemap.xml from current HTML files (top-level + signals/).
  // No-op when content unchanged; otherwise rides along with the status push.
  const sm = generateSitemap(REPO_ROOT);
  if (sm.changed) log(`wrote sitemap.xml: ${sm.count} urls`);

  if (!NO_PUSH) gitPushStatus();
}

async function writeStatusJson(items) {
  const itemById = new Map(items.map(it => [it.id, it]));
  const tg = await readJson(LAST_POSTED, null);
  const bs = await readJson(LAST_POSTED_BSKY, null);
  const xs = await readJson(LAST_POSTED_X, null);
  const status = {
    generated_at: toUtcIso(new Date()),
    fetcher: { last_run_at: toUtcIso(new Date()), items_count: items.length, new_last_run: items.filter(it => it.discovered_at && (Date.now() - new Date(it.discovered_at).getTime()) < 30 * 60 * 1000).length, expected_cadence_sec: 900 },
    telegram: postChannelStats(tg, itemById),
    bluesky: postChannelStats(bs, itemById),
    x: postChannelStats(xs, itemById),
  };
  try {
    const { writeFile } = await import('node:fs/promises');
    await writeFile(STATUS_JSON, JSON.stringify(status, null, 2) + '\n', 'utf8');
    log(`wrote status.json: tg=${status.telegram.posts_24h}/24h p50=${status.telegram.median_latency_sec ?? '—'}s · bsky=${status.bluesky.posts_24h}/24h p50=${status.bluesky.median_latency_sec ?? '—'}s · x=${status.x.posts_24h}/24h`);
  } catch (e) {
    log(`status.json write failed: ${e.message}`);
  }
}

function postChannelStats(state, itemById) {
  const out = { last_post_at: null, posts_24h: 0, posts_total: 0, median_latency_sec: null, p95_latency_sec: null, seeded: !!state?.seeded };
  if (!state) return out;
  const posted = readPostedMap(state);
  const entries = Object.entries(posted).filter(([, t]) => !!t);
  out.posts_total = Object.keys(posted).length;
  if (entries.length === 0) return out;

  const cutoff = Date.now() - 24 * 3600 * 1000;
  const last24 = entries.filter(([, t]) => new Date(t).getTime() >= cutoff);
  out.posts_24h = last24.length;
  out.last_post_at = entries.reduce((m, [, t]) => (t > m ? t : m), entries[0][1]);

  const latencies = last24
    .map(([id, postedAt]) => {
      const it = itemById.get(id);
      if (!it?.discovered_at) return null;
      return (new Date(postedAt).getTime() - new Date(it.discovered_at).getTime()) / 1000;
    })
    .filter(x => x != null && x >= 0)
    .sort((a, b) => a - b);
  if (latencies.length > 0) {
    out.median_latency_sec = Math.round(latencies[Math.floor(latencies.length * 0.5)]);
    out.p95_latency_sec = Math.round(latencies[Math.min(latencies.length - 1, Math.floor(latencies.length * 0.95))]);
  }
  return out;
}

function gitPushStatus() {
  const opts = { cwd: REPO_ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] };
  try {
    execFileSync('git', ['add', 'status.json', 'sitemap.xml'], opts);
    const staged = execFileSync('git', ['diff', '--cached', '--name-only'], opts).trim();
    if (!staged) return;
    const msg = staged.includes('sitemap.xml') ? `status + sitemap: ${toUtcIso(new Date())}` : `status: ${toUtcIso(new Date())}`;
    execFileSync('git', ['commit', '-m', msg], opts);
    try {
      execFileSync('git', ['pull', '--rebase', '--autostash', 'origin', 'main'], opts);
    } catch (e) {
      try { execFileSync('git', ['rebase', '--abort'], { ...opts, stdio: 'ignore' }); } catch {}
      throw e;
    }
    execFileSync('git', ['push', 'origin', 'HEAD'], opts);
  } catch (e) {
    console.error(`git: status push failed: ${e.stderr?.toString() || e.message}`);
  }
}

function gitPushNews(newCount) {
  const opts = { cwd: REPO_ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] };
  const message = `news: ${newCount} new item${newCount === 1 ? '' : 's'} ${toUtcIso(new Date())}`;
  try {
    execFileSync('git', ['add', 'news.json', 'news.xml'], opts);
    // Bail if nothing actually staged (e.g. files unchanged on disk).
    const staged = execFileSync('git', ['diff', '--cached', '--name-only'], opts).trim();
    if (!staged) { log('git: no news changes to commit'); return; }
    execFileSync('git', ['commit', '-m', message], opts);
    // Rebase before push — the arb scanner pushes opportunities.json to this
    // same remote every 15 min, so a plain push gets rejected as non-fast-fwd.
    try {
      execFileSync('git', ['pull', '--rebase', '--autostash', 'origin', 'main'], opts);
    } catch (e) {
      try { execFileSync('git', ['rebase', '--abort'], { ...opts, stdio: 'ignore' }); } catch {}
      throw e;
    }
    execFileSync('git', ['push', 'origin', 'HEAD'], opts);
    log(`git: pushed → "${message}"`);
  } catch (e) {
    console.error(`git: push failed: ${e.stderr?.toString() || e.message}`);
  }
}

function rssEscape(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

function rfc822(d) {
  // RSS 2.0 spec requires RFC 822 dates. toUTCString() emits "GMT" suffix
  // which is technically valid, but Google's feed validator only accepts
  // the numeric offset form. Convert
  // "Sat, 02 May 2026 16:31:37 GMT" → "Sat, 02 May 2026 16:31:37 +0000".
  return d.toUTCString().replace(/GMT$/, '+0000');
}

function renderRssFeed(items) {
  const now = new Date();
  const itemXml = items.map(it => {
    const src = it.source_name || '';
    let title = it.title || it.headline || '(untitled)';
    if (src && !title.startsWith(`[${src}]`)) title = `[${src}] ${title}`;
    const link = it.url || `https://probbrain.com/news#${it.anchor || ''}`;
    const pub = it.published_at ? new Date(it.published_at) : now;
    const desc = it.headline || it.description || '';
    const cat = it.category || '';
    const guid = it.id || it.url || title.slice(0, 80);
    return (
      '    <item>\n' +
      `      <title>${rssEscape(title)}</title>\n` +
      `      <link>${rssEscape(link)}</link>\n` +
      `      <guid isPermaLink="false">${rssEscape(guid)}</guid>\n` +
      `      <pubDate>${rfc822(pub)}</pubDate>\n` +
      `      <category>${rssEscape(cat)}</category>\n` +
      `      <description><![CDATA[${desc}]]></description>\n` +
      '    </item>'
    );
  }).join('\n');
  return (
    '<?xml version="1.0" encoding="UTF-8"?>\n' +
    '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n' +
    '  <channel>\n' +
    '    <title>ProbBrain - AI News Terminal</title>\n' +
    '    <link>https://probbrain.com/news</link>\n' +
    '    <atom:link href="https://probbrain.com/news.xml" rel="self" type="application/rss+xml"/>\n' +
    '    <description>AI lab announcements, arXiv papers, GitHub and HuggingFace trending, AI Hacker News, and independent writers - aggregated, deduped, and posted to @ProbBrain on Telegram.</description>\n' +
    '    <language>en</language>\n' +
    `    <lastBuildDate>${rfc822(now)}</lastBuildDate>\n` +
    '    <ttl>15</ttl>\n' +
    itemXml + '\n' +
    '  </channel>\n</rss>\n'
  );
}

async function postToTelegram(items) {
  loadEnv();
  let creds;
  try {
    const e = require_('TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHANNEL_ID');
    creds = { token: e.TELEGRAM_BOT_TOKEN, chat_id: e.TELEGRAM_CHANNEL_ID };
  } catch (e) {
    log(`SKIP telegram: ${e.message}`);
    return;
  }

  const state = await readJson(LAST_POSTED, null);
  const isFirstRun = state === null;

  if (isFirstRun) {
    const ts = toUtcIso(new Date());
    const posted = Object.fromEntries(items.map(it => [it.id, null])); // null = unknown post time (silent seed)
    const seed = { posted, updated_at: ts, seeded: true };
    await writeJsonAtomic(LAST_POSTED, seed);
    log(`first-run silent seed: ${Object.keys(posted).length} ids written to last_posted.json (no telegram posts)`);
    return;
  }

  const posted = readPostedMap(state);
  const candidates = items
    .filter(it => !(it.id in posted))
    .sort((a, b) => (a.published_at || '').localeCompare(b.published_at || ''));

  if (candidates.length === 0) {
    vlog('telegram: nothing new to post');
    return;
  }

  if (candidates.length > TELEGRAM_MAX_PER_RUN) {
    log(`telegram: capping batch ${candidates.length} → ${TELEGRAM_MAX_PER_RUN} (rest will post next run)`);
  }
  const batch = candidates.slice(0, TELEGRAM_MAX_PER_RUN);

  // Digest path: when 2+ fresh items, send ONE rolled-up message instead of
  // N individual messages so the channel doesn't get spammed.
  if (batch.length > 1) {
    const text = formatTgDigest(batch);
    try {
      await sendMessage({ ...creds, text });
      const postedAt = toUtcIso(new Date());
      for (const it of batch) posted[it.id] = postedAt;
      await writeJsonAtomic(LAST_POSTED, { posted, updated_at: postedAt });
      log(`telegram: sent 1 digest with ${batch.length} items posted_total=${Object.keys(posted).length}`);
    } catch (e) {
      log(`TG DIGEST ERR: ${e.message}`);
      if (e.body && e.body.error_code === 429) {
        const wait = (e.body.parameters?.retry_after || 30) * 1000;
        log(`telegram 429 — sleeping ${wait}ms`);
        await sleep(wait);
      }
    }
    return;
  }

  // Single-item path: 1 fresh item → post normally.
  let sent = 0, failed = 0;
  for (let i = 0; i < batch.length; i++) {
    const it = batch[i];
    const text = formatPost(it);
    try {
      await sendMessage({ ...creds, text });
      const postedAt = toUtcIso(new Date());
      posted[it.id] = postedAt;
      sent++;
      vlog(`  → tg ${it.source_id}: ${(it.headline || it.title).slice(0, 60)}`);
      await writeJsonAtomic(LAST_POSTED, { posted, updated_at: postedAt });
    } catch (e) {
      failed++;
      log(`TG ERR ${it.id}: ${e.message}`);
      if (e.body && e.body.error_code === 429) {
        const wait = (e.body.parameters?.retry_after || 30) * 1000;
        log(`telegram 429 — sleeping ${wait}ms`);
        await sleep(wait);
      }
    }
    if (i < batch.length - 1) await sleep(TELEGRAM_THROTTLE_MS);
  }
  log(`telegram: sent=${sent} failed=${failed} posted_total=${Object.keys(posted).length}`);
}

async function postToBluesky(items) {
  let session;
  try {
    session = await createBlueskyClient();
  } catch (e) {
    log(`SKIP bluesky: login failed — ${e.message}`);
    return;
  }
  if (!session) {
    log(`SKIP bluesky: no creds at ~/automation/bluesky-poster/probbrain-config.json`);
    return;
  }

  const state = await readJson(LAST_POSTED_BSKY, null);
  const isFirstRun = state === null;

  if (isFirstRun) {
    const ts = toUtcIso(new Date());
    const posted = Object.fromEntries(items.map(it => [it.id, null]));
    const seed = { posted, updated_at: ts, seeded: true, handle: session.creds.handle };
    await writeJsonAtomic(LAST_POSTED_BSKY, seed);
    log(`first-run silent seed: ${Object.keys(posted).length} ids written to last_posted_bsky.json (no bluesky posts)`);
    return;
  }

  const posted = readPostedMap(state);
  const candidates = items
    .filter(it => !(it.id in posted))
    .sort((a, b) => (a.published_at || '').localeCompare(b.published_at || ''));

  if (candidates.length === 0) {
    vlog('bluesky: nothing new to post');
    return;
  }

  if (candidates.length > BSKY_MAX_PER_RUN) {
    log(`bluesky: capping batch ${candidates.length} → ${BSKY_MAX_PER_RUN} (rest will post next run)`);
  }
  const batch = candidates.slice(0, BSKY_MAX_PER_RUN);

  // Digest path: 2+ fresh items → one rolled-up post (Bluesky has a 300-char
  // cap so the digest only includes as many items as fit; we still mark all
  // batch items as posted so they don't try to repost individually next run).
  if (batch.length > 1) {
    try {
      await postBskyDigest(session.agent, batch);
      const postedAt = toUtcIso(new Date());
      for (const it of batch) posted[it.id] = postedAt;
      await writeJsonAtomic(LAST_POSTED_BSKY, { posted, updated_at: postedAt, handle: session.creds.handle });
      log(`bluesky: sent 1 digest with ${batch.length} items posted_total=${Object.keys(posted).length}`);
    } catch (e) {
      log(`BSKY DIGEST ERR: ${e.message}`);
      const status = e.status || e.statusCode;
      if (status === 429) {
        log(`bluesky 429 — sleeping 60s`);
        await sleep(60_000);
      }
    }
    return;
  }

  // Single-item path: 1 fresh item → post normally with per-item embed card.
  let sent = 0, failed = 0;
  for (let i = 0; i < batch.length; i++) {
    const it = batch[i];
    try {
      await postBskyItem(session.agent, it);
      const postedAt = toUtcIso(new Date());
      posted[it.id] = postedAt;
      sent++;
      vlog(`  → bsky ${it.source_id}: ${(it.headline || it.title).slice(0, 60)}`);
      await writeJsonAtomic(LAST_POSTED_BSKY, { posted, updated_at: postedAt, handle: session.creds.handle });
    } catch (e) {
      failed++;
      log(`BSKY ERR ${it.id}: ${e.message}`);
      const status = e.status || e.statusCode;
      if (status === 429) {
        log(`bluesky 429 — sleeping 60s`);
        await sleep(60_000);
      }
    }
    if (i < batch.length - 1) await sleep(BSKY_THROTTLE_MS);
  }
  log(`bluesky: sent=${sent} failed=${failed} posted_total=${Object.keys(posted).length}`);
}

async function postToX(items) {
  const client = createXClient();
  if (!client) {
    log(`SKIP x: missing X_CONSUMER_KEY/SECRET or X_ACCESS_TOKEN/SECRET in env`);
    return;
  }

  const state = await readJson(LAST_POSTED_X, null);
  const isFirstRun = state === null;

  if (isFirstRun) {
    const ts = toUtcIso(new Date());
    const posted = Object.fromEntries(items.map(it => [it.id, null]));
    const seed = { posted, last_digest_at: null, updated_at: ts, seeded: true };
    await writeJsonAtomic(LAST_POSTED_X, seed);
    log(`first-run silent seed: ${Object.keys(posted).length} ids written to last_posted_x.json (no x posts)`);
    return;
  }

  const posted = readPostedMap(state);
  const lastDigestAt = state.last_digest_at ? new Date(state.last_digest_at).getTime() : 0;
  const now = Date.now();

  if (lastDigestAt && now - lastDigestAt < X_MIN_INTERVAL_MS) {
    const mins = Math.round((now - lastDigestAt) / 60000);
    vlog(`x: skip (last digest ${mins}m ago, min ${X_MIN_INTERVAL_MS / 60000}m)`);
    return;
  }

  const picked = pickAllRecent(items, X_DIGEST_WINDOW_MS, posted);

  if (picked.length < X_DIGEST_MIN_ITEMS) {
    vlog(`x: skip (${picked.length} unposted items in past 2h, need ≥${X_DIGEST_MIN_ITEMS})`);
    return;
  }

  const quoteTarget = await readLastTweetId();

  try {
    const result = await postXThread(client, picked, quoteTarget);
    const postedAt = toUtcIso(new Date());
    const postedCount = result.ids.filter(Boolean).length;
    for (const it of picked.slice(0, postedCount)) posted[it.id] = postedAt;
    await writeJsonAtomic(LAST_POSTED_X, { posted, last_digest_at: postedAt, updated_at: postedAt });
    if (result.ids[0]) await writeLastTweetId(result.ids[0]);
    log(`x: posted thread with ${postedCount} items (first tweet_id=${result.ids[0]}, quote_of=${quoteTarget || '—'})`);
  } catch (e) {
    log(`X ERR: ${e.message}`);
    if (e.data) log(`  details: ${JSON.stringify(e.data).slice(0, 300)}`);
    // Burn the 2h slot on failure too, so we don't hammer X every 15min
    // when last_digest_at would otherwise stay frozen at the last success.
    // Spamming attempts almost certainly is what trips X's per-app cap.
    const failedAt = toUtcIso(new Date());
    await writeJsonAtomic(LAST_POSTED_X, { posted, last_digest_at: failedAt, updated_at: failedAt });
  }
}

async function readLastTweetId() {
  const state = await readJson(LAST_X_TWEET, null);
  if (!state) return null;
  const tid = String(state.tweet_id || '').trim();
  return tid || null;
}

async function writeLastTweetId(tweetId) {
  await mkdir(dirname(LAST_X_TWEET), { recursive: true });
  await writeJsonAtomic(LAST_X_TWEET, {
    tweet_id: String(tweetId),
    posted_at: toUtcIso(new Date()),
  });
}

// Migrate legacy {posted_ids:[]} to {posted:{id:postedAt}} on read. Legacy
// entries get null post-times (we never recorded them), so they show up in
// the dedupe set but won't contribute to latency stats.
function readPostedMap(state) {
  if (!state) return {};
  if (state.posted && typeof state.posted === 'object' && !Array.isArray(state.posted)) return { ...state.posted };
  if (Array.isArray(state.posted_ids)) return Object.fromEntries(state.posted_ids.map(id => [id, null]));
  return {};
}

run().catch(e => { console.error('FATAL:', e); process.exit(1); });
