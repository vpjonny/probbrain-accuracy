import { USER_AGENT, FETCH_TIMEOUT_MS } from '../sources.js';
import { toUtcIso, cleanTitle, canonicalUrl } from './normalize.js';

const AI_KEYWORDS = [
  'ai', 'llm', 'gpt', 'claude', 'gemini', 'llama', 'mistral', 'hugging', 'deepmind',
  'transformer', 'neural', 'agent', 'rag', 'embedding', 'inference', 'mlops', 'ml-',
  'machine-learning', 'deep-learning', 'diffusion', 'tokenizer', 'fine-tun',
  'prompt', 'vector', 'rerank', 'multimodal', 'vision-language', 'speech-to-text',
];

function decodeHtml(s) {
  return (s || '')
    .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&nbsp;/g, ' ');
}

function looksAI(name, desc) {
  const hay = `${name} ${desc}`.toLowerCase();
  return AI_KEYWORDS.some(k => hay.includes(k));
}

export async function fetchGithubTrending(source) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), FETCH_TIMEOUT_MS);
  try {
    const r = await fetch(source.url, { headers: { 'User-Agent': USER_AGENT, 'Accept': 'text/html' }, signal: ctrl.signal });
    if (!r.ok) throw new Error(`GH trending: HTTP ${r.status}`);
    const html = await r.text();
    const out = [];
    const seen = new Set();
    const articleRe = /<article\b[\s\S]*?<\/article>/g;
    const articles = html.match(articleRe) || [];
    const now = toUtcIso(new Date());
    for (const block of articles) {
      const m = block.match(/<a[^>]+href="\/([^"\/]+)\/([^"]+)"/);
      if (!m) continue;
      const owner = m[1], repo = m[2].split('"')[0].split('#')[0].trim();
      const slug = `${owner}/${repo}`;
      if (seen.has(slug)) continue;
      seen.add(slug);
      const descMatch = block.match(/<p[^>]*class="[^"]*col-9[^"]*"[^>]*>([\s\S]*?)<\/p>/);
      const desc = decodeHtml((descMatch ? descMatch[1] : '').replace(/<[^>]+>/g, '')).trim();
      if (!looksAI(slug, desc)) continue;
      out.push({
        title: cleanTitle(`${slug}${desc ? ' — ' + desc : ''}`),
        url: canonicalUrl(`https://github.com/${slug}`),
        published_at: now,
        description: desc,
      });
    }
    return out;
  } finally {
    clearTimeout(t);
  }
}
