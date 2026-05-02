import { USER_AGENT, FETCH_TIMEOUT_MS } from '../sources.js';
import { toUtcIso, cleanTitle } from './normalize.js';

export async function fetchHf(source) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  try {
    const r = await fetch(source.url, { headers: { 'User-Agent': USER_AGENT, 'Accept': 'application/json' }, signal: ctrl.signal });
    if (!r.ok) throw new Error(`HF: HTTP ${r.status}`);
    const arr = await r.json();
    return arr.map(m => ({
      title: cleanTitle(`${m.modelId || m.id} · ${m.likes || 0}♥ · ${m.downloads || 0} dl`),
      url: `https://huggingface.co/${m.modelId || m.id}`,
      published_at: toUtcIso(m.lastModified || m.createdAt),
      description: cleanTitle(m.pipeline_tag ? `${m.pipeline_tag}` : ''),
    })).filter(it => it.url && it.title);
  } finally {
    clearTimeout(t);
  }
}
