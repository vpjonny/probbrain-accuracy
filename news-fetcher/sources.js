export const CATEGORIES = {
  lab:       { emoji: '🧠', hashtag: 'lab' },
  paper:     { emoji: '📄', hashtag: 'paper' },
  code:      { emoji: '💻', hashtag: 'code' },
  writing:   { emoji: '✍️', hashtag: 'writing' },
  community: { emoji: '🔥', hashtag: 'community' },
};

export const SOURCES = [
  { id: 'anthropic',    name: 'Anthropic',         type: 'sitemap',    url: 'https://www.anthropic.com/sitemap.xml', filter: ['/news/', '/research/', '/engineering/'], limit: 30, category: 'lab', summarize: false, hashtag: 'anthropic' },
  { id: 'openai',       name: 'OpenAI',            type: 'rss',        url: 'https://openai.com/news/rss.xml',                          category: 'lab',       summarize: false, hashtag: 'openai' },
  { id: 'deepmind',     name: 'Google DeepMind',   type: 'rss',        url: 'https://deepmind.google/blog/rss.xml',                     category: 'lab',       summarize: false, hashtag: 'deepmind' },
  { id: 'meta-ai',      name: 'Meta AI',           type: 'html-index', url: 'https://ai.meta.com/blog/', urlPattern: '/blog/[^"\'/?#]+/?', excludeRe: ['/blog/(\\?|$|page=|#)'], limit: 20, category: 'lab', summarize: false, hashtag: 'meta' },
  { id: 'mistral',      name: 'Mistral',           type: 'sitemap',    url: 'https://mistral.ai/sitemap.xml', filter: ['/news/'], limit: 25, category: 'lab', summarize: false, hashtag: 'mistral', title: { clean: [' | Mistral AI'] } },
  // skipDescription: xai serves the same generic site-wide og:description on
  // every news page ("xAI builds Grok…"), so showing it in the modal would be
  // identical boilerplate on every item. Drop it.
  { id: 'xai',          name: 'xAI',               type: 'sitemap',    url: 'https://x.ai/sitemap.xml', filter: ['/news/'], limit: 25, category: 'lab', summarize: false, hashtag: 'xai', skipDescription: true, title: { prefer: ['headline', 'title', 'og', 'twitter'], clean: [' | xAI'] } },

  { id: 'arxiv-cs.LG',  name: 'arXiv cs.LG',       type: 'rss',  url: 'https://rss.arxiv.org/rss/cs.LG',                          category: 'paper',     summarize: true,  hashtag: 'arxiv' },
  { id: 'arxiv-cs.CL',  name: 'arXiv cs.CL',       type: 'rss',  url: 'https://rss.arxiv.org/rss/cs.CL',                          category: 'paper',     summarize: true,  hashtag: 'arxiv' },

  { id: 'huggingface',  name: 'HuggingFace',       type: 'hf',   url: 'https://huggingface.co/api/models?sort=likes7d&direction=-1&limit=15', category: 'code', summarize: true, hashtag: 'huggingface' },
  { id: 'github',       name: 'GitHub Trending',   type: 'github', url: 'https://github.com/trending?since=daily',                category: 'code',      summarize: true,  hashtag: 'github' },

  { id: 'hn',           name: 'Hacker News',       type: 'hn',   url: 'https://hacker-news.firebaseio.com/v0',                    category: 'community', summarize: false, hashtag: 'hn' },

  { id: 'simonw',       name: 'Simon Willison',    type: 'rss',  url: 'https://simonwillison.net/atom/everything/',               category: 'writing',   summarize: false, hashtag: 'simonw', aiOnly: true },
  { id: 'latentspace',  name: 'Latent Space',      type: 'rss',  url: 'https://www.latent.space/feed',                            category: 'writing',   summarize: false, hashtag: 'latentspace' },
  { id: 'interconnects', name: 'Interconnects',    type: 'rss',  url: 'https://www.interconnects.ai/feed',                        category: 'writing',   summarize: false, hashtag: 'interconnects' },
];

export const HN_AI_KEYWORDS = [
  'ai', 'a.i.', 'llm', 'gpt', 'claude', 'anthropic', 'openai', 'gemini', 'deepmind',
  'llama', 'mistral', 'hugging face', 'huggingface', 'transformer', 'neural', 'agent',
  'rag', 'fine-tun', 'prompt', 'embedding', 'inference', 'mlops', 'ml ',
  'machine learning', 'machine-learning', 'deep learning', 'deep-learning',
  'language model', 'language-model', 'foundation model', 'multimodal',
  'diffusion', 'stable diffusion', 'tokenizer', 'tokeniz', 'open-source ai', 'open source ai',
  'codex', 'chatgpt', 'grok', 'copilot', 'agentic', 'qwen', 'deepseek', 'mlx', 'rlhf',
  'vibe cod', 'vibe-cod', 'tts', 'voice model', 'speech model',
];

// Reused by fetch-rss when source.aiOnly is set: drops items whose title+URL
// don't match any AI keyword. Description is excluded on purpose — Simon's
// blog tags (e.g. "ai", "llms") get embedded in description HTML and would
// false-positive on photography/wildlife posts that happen to be tagged.
export function matchesAiKeyword(item) {
  const hay = `${item.title || ''} ${item.url || ''}`.toLowerCase();
  return HN_AI_KEYWORDS.some(k => hay.includes(k));
}

export const HN_MIN_SCORE = 100;
export const HN_TOP_LIMIT = 60;

export const USER_AGENT = 'ProbBrainNewsFetcher/0.1 (+https://probbrain.com/news)';
export const ARXIV_INTERVAL_MS = 3100;
export const FETCH_TIMEOUT_MS = 15000;
