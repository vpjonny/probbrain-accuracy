import { TwitterApi } from 'twitter-api-v2';
import { loadEnv } from './env.js';

const NEWS_PAGE = 'probbrain.com/news';
const HEADER = '🆕 AI news past 2h:\n';
const FOOTER = `\n→ ${NEWS_PAGE}`;
const TWEET_LIMIT = 280;

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
