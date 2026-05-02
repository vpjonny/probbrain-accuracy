import { USER_AGENT, FETCH_TIMEOUT_MS, HN_AI_KEYWORDS, HN_MIN_SCORE, HN_TOP_LIMIT } from '../sources.js';
import { toUtcIso, cleanTitle } from './normalize.js';

const HN_BASE = 'https://hacker-news.firebaseio.com/v0';

async function getJson(url) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  try {
    const r = await fetch(url, { headers: { 'User-Agent': USER_AGENT }, signal: ctrl.signal });
    if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
    return await r.json();
  } finally {
    clearTimeout(t);
  }
}

function isAi(title) {
  const t = title.toLowerCase();
  return HN_AI_KEYWORDS.some(k => t.includes(k));
}

export async function fetchHn(_source, knownIds) {
  const ids = (await getJson(`${HN_BASE}/topstories.json`)).slice(0, HN_TOP_LIMIT);
  const out = [];
  const conc = 5;
  for (let i = 0; i < ids.length; i += conc) {
    const batch = ids.slice(i, i + conc);
    const results = await Promise.allSettled(batch.map(async id => {
      const candidateId = `hn|https://news.ycombinator.com/item?id=${id}`;
      if (knownIds.has(candidateId)) return null;
      const it = await getJson(`${HN_BASE}/item/${id}.json`);
      if (!it || it.dead || it.deleted || it.type !== 'story') return null;
      if (typeof it.score !== 'number' || it.score < HN_MIN_SCORE) return null;
      const title = cleanTitle(it.title || '');
      if (!title || !isAi(title)) return null;
      const url = it.url || `https://news.ycombinator.com/item?id=${id}`;
      return {
        title,
        url,
        published_at: toUtcIso(new Date((it.time || 0) * 1000)),
        description: `HN score ${it.score} · ${it.descendants || 0} comments`,
      };
    }));
    for (const r of results) if (r.status === 'fulfilled' && r.value) out.push(r.value);
  }
  return out;
}
