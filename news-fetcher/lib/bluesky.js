import { readFileSync, existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { resolve } from 'node:path';
import { AtpAgent } from '@atproto/api';

const NEWS_PAGE = 'https://probbrain.com/news';
const OG_CARD_PATH = resolve(import.meta.dirname || '.', '..', '..', 'og-card.png');
const CONFIG_PATHS = [
  resolve(import.meta.dirname || '.', '..', 'bluesky.config.json'),
  resolve(homedir(), 'automation', 'bluesky-poster', 'probbrain-config.json'),
];

export function loadBlueskyCreds() {
  for (const p of CONFIG_PATHS) {
    if (!existsSync(p)) continue;
    const cfg = JSON.parse(readFileSync(p, 'utf8'));
    const bsky = cfg.bluesky || cfg;
    if (bsky?.handle && bsky?.app_password) {
      return { handle: bsky.handle, appPassword: bsky.app_password, source: p };
    }
  }
  return null;
}

export async function createBlueskyClient() {
  const creds = loadBlueskyCreds();
  if (!creds) return null;
  const agent = new AtpAgent({ service: 'https://bsky.social' });
  await agent.login({ identifier: creds.handle, password: creds.appPassword });
  return { agent, creds };
}

let cachedThumb = null;
async function getCardThumb(agent) {
  if (cachedThumb) return cachedThumb;
  const bytes = readFileSync(OG_CARD_PATH);
  const r = await agent.uploadBlob(bytes, { encoding: 'image/png' });
  cachedThumb = r.data.blob;
  return cachedThumb;
}

export async function postNewsItem(agent, item) {
  const url = `${NEWS_PAGE}#${item.anchor}`;
  const headline = (item.headline || item.title || '').trim();
  const source = item.source_name || '';
  const thumb = await getCardThumb(agent).catch(() => null);

  const text = headline.length > 280 ? headline.slice(0, 277) + '…' : headline;

  const embed = {
    $type: 'app.bsky.embed.external',
    external: {
      uri: url,
      title: headline.length > 240 ? headline.slice(0, 237) + '…' : headline,
      description: source ? `${source} · ProbBrain News` : 'ProbBrain News',
      ...(thumb ? { thumb } : {}),
    },
  };

  return await agent.post({ text, embed, langs: ['en'], createdAt: new Date().toISOString() });
}
