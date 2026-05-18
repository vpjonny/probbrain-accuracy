import { TwitterApi } from 'twitter-api-v2';
import { loadEnv } from './env.js';

const NEWS_PAGE = 'probbrain.com/news';
const HEADER = '🆕 AI news past 2h:\n';
const FOOTER = `\n→ ${NEWS_PAGE}`;
const THREAD_HEADER = '🆕 AI news past 2h';
const THREAD_FOOTER = `→ ${NEWS_PAGE}`;
const TWEET_LIMIT = 280;
const THREAD_MAX = 25;

export function createXClient() {
  loadEnv();
  const ck = process.env.X_CONSUMER_KEY;
  const cs = process.env.X_CONSUMER_SECRET;
  const at = process.env.X_ACCESS_TOKEN;
  const ats = process.env.X_ACCESS_TOKEN_SECRET;
  if (!ck || !cs || !at || !ats) return null;
  return new TwitterApi({ appKey: ck, appSecret: cs, accessToken: at, accessSecret: ats });
}

// Newest first, max 1 per source for diversity. Falls back to newest remaining
// if there aren't enough distinct sources to fill `max`.
export function pickDigestItems(items, max = 3) {
  const sorted = [...items].sort(
    (a, b) => (b.published_at || '').localeCompare(a.published_at || '')
  );
  const seen = new Set();
  const picked = [];
  for (const it of sorted) {
    if (seen.has(it.source_id)) continue;
    seen.add(it.source_id);
    picked.push(it);
    if (picked.length >= max) break;
  }
  if (picked.length < max) {
    const ids = new Set(picked.map(it => it.id));
    for (const it of sorted) {
      if (ids.has(it.id)) continue;
      picked.push(it);
      if (picked.length >= max) break;
    }
  }
  return picked;
}

export function formatDigest(items) {
  const lines = [];
  let used = HEADER.length + FOOTER.length;
  for (const it of items) {
    const src = (it.source_name || '').trim();
    const head = (it.headline || it.title || '').trim();
    if (!head) continue;
    const prefix = src ? `• ${src}: ` : '• ';
    const room = TWEET_LIMIT - used - prefix.length - 1; // -1 for newline
    if (room < 12) break;
    const trimmed = head.length > room ? head.slice(0, room - 1) + '…' : head;
    const line = prefix + trimmed;
    lines.push(line);
    used += line.length + 1;
  }
  return HEADER + lines.join('\n') + FOOTER;
}

export async function postDigest(client, items) {
  const text = formatDigest(items);
  const r = await client.v2.tweet(text);
  return { id: r.data?.id, text };
}

// All unposted items discovered in the last `cutoffMs`, newest first,
// source-diversified (each source's newest item first, then fill with
// remaining). No hard upper cap here — caller caps to THREAD_MAX.
export function pickAllRecent(items, cutoffMs, posted) {
  const cutoff = Date.now() - cutoffMs;
  const eligible = items.filter(it => {
    if (it.id in posted) return false;
    const t = it.discovered_at ? new Date(it.discovered_at).getTime() : 0;
    return t >= cutoff;
  });
  eligible.sort((a, b) => (b.discovered_at || '').localeCompare(a.discovered_at || ''));
  const seenSources = new Set();
  const head = [];
  const tail = [];
  for (const it of eligible) {
    if (seenSources.has(it.source_id)) tail.push(it);
    else { seenSources.add(it.source_id); head.push(it); }
  }
  return [...head, ...tail];
}

// Returns one tweet-text per item, sized to fit 280 chars each. First
// tweet gets the THREAD_HEADER, last gets the THREAD_FOOTER link.
export function formatThreadTweets(items) {
  const n = items.length;
  return items.map((it, idx) => {
    const i = idx + 1;
    const isFirst = idx === 0;
    const isLast = idx === n - 1;
    const src = (it.source_name || '').trim();
    const emoji = (it.category_emoji || '').trim();
    const head = (it.headline || it.title || '').trim();
    const url = (it.url || '').trim();
    const idxMarker = `[${i}/${n}] `;
    const sourceLine = emoji ? `${emoji} ${src}` : src;
    const headerPart = isFirst ? `${THREAD_HEADER}\n\n` : '';
    const footerPart = isLast ? `\n\n${THREAD_FOOTER}` : '';
    const urlPart = url ? `\n${url}` : '';
    // Reserve room for everything except the headline, then trim headline to fit.
    const fixed =
      headerPart.length + idxMarker.length + sourceLine.length + 1 +
      urlPart.length + footerPart.length;
    const room = Math.max(20, TWEET_LIMIT - fixed);
    const headTrim = head.length > room ? head.slice(0, room - 1) + '…' : head;
    return headerPart + idxMarker + sourceLine + '\n' + headTrim + urlPart + footerPart;
  });
}

export async function postThread(client, items) {
  const capped = items.slice(0, THREAD_MAX);
  const texts = formatThreadTweets(capped);
  if (texts.length === 0) throw new Error('postThread: no items');
  if (texts.length === 1) {
    const r = await client.v2.tweet(texts[0]);
    return { ids: [r.data?.id], texts };
  }
  const results = await client.v2.tweetThread(texts);
  const ids = results.map(r => r.data?.id);
  return { ids, texts };
}
