#!/usr/bin/env node
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { SOURCES, CATEGORIES, ARXIV_INTERVAL_MS } from './sources.js';
import { itemId, itemAnchor, buildHashtags, toUtcIso } from './lib/normalize.js';
import { readJson, writeJsonAtomic, indexBy } from './lib/persist.js';
import { fetchRss } from './lib/fetch-rss.js';
import { fetchHn } from './lib/fetch-hn.js';
import { fetchHf } from './lib/fetch-hf.js';
import { fetchGithubTrending } from './lib/fetch-github.js';
import { fetchSitemap } from './lib/fetch-sitemap.js';
import { fetchHtmlIndex } from './lib/fetch-html-index.js';
import { summarize } from './lib/summarize.js';
import { loadEnv, require_ } from './lib/env.js';
import { formatPost, sendMessage } from './lib/telegram.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..');
const NEWS_JSON = join(REPO_ROOT, 'news.json');
const LAST_POSTED = join(__dirname, 'last_posted.json');
const DEFAULT_PER_SOURCE_KEEP = 30;
const SUMMARY_MAX_PER_RUN = 8;
const TELEGRAM_THROTTLE_MS = 1100;
const TELEGRAM_MAX_PER_RUN = 30;

const argv = new Set(process.argv.slice(2));
const DRY_RUN = argv.has('--dry-run');
const VERBOSE = argv.has('--verbose');
const NO_POST = argv.has('--no-post');
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
  } else {
    await writeJsonAtomic(NEWS_JSON, out);
    log(`wrote news.json: ${items.length} items (${stats.new} new, ${stats.summarized} summarized, ${stats.errors} fetch errors, ${stats.summarizeFails} summary errors)`);
  }

  if (DRY_RUN || NO_POST) return;
  await postToTelegram(items);
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
    const seed = { posted_ids: items.map(it => it.id), updated_at: toUtcIso(new Date()), seeded: true };
    await writeJsonAtomic(LAST_POSTED, seed);
    log(`first-run silent seed: ${seed.posted_ids.length} ids written to last_posted.json (no telegram posts)`);
    return;
  }

  const posted = new Set(state.posted_ids || []);
  const candidates = items
    .filter(it => !posted.has(it.id))
    .sort((a, b) => (a.published_at || '').localeCompare(b.published_at || ''));

  if (candidates.length === 0) {
    vlog('telegram: nothing new to post');
    return;
  }

  if (candidates.length > TELEGRAM_MAX_PER_RUN) {
    log(`telegram: capping batch ${candidates.length} → ${TELEGRAM_MAX_PER_RUN} (rest will post next run)`);
  }
  const batch = candidates.slice(0, TELEGRAM_MAX_PER_RUN);

  let sent = 0, failed = 0;
  for (let i = 0; i < batch.length; i++) {
    const it = batch[i];
    const text = formatPost(it);
    try {
      await sendMessage({ ...creds, text });
      posted.add(it.id);
      sent++;
      vlog(`  → tg ${it.source_id}: ${(it.headline || it.title).slice(0, 60)}`);
      const next = { posted_ids: [...posted], updated_at: toUtcIso(new Date()) };
      await writeJsonAtomic(LAST_POSTED, next);
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
  log(`telegram: sent=${sent} failed=${failed} posted_total=${posted.size}`);
}

run().catch(e => { console.error('FATAL:', e); process.exit(1); });
