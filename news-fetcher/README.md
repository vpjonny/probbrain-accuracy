# probbrain-news-fetcher

Pulls RSS + APIs from 14 AI sources, dedupes, optionally summarizes via the local `claude` CLI, and writes `../news.json` for the static frontend at probbrain.com/news.

## Files
- `sources.js` — source list + categories + HN keyword filter
- `news-fetch.js` — orchestrator (run via `npm run fetch`)
- `lib/fetch-rss.js` · `lib/fetch-hn.js` · `lib/fetch-hf.js` · `lib/fetch-github.js` · `lib/fetch-sitemap.js` · `lib/fetch-html-index.js`
- `lib/fetch-title.js` — extracts og:title / twitter:title / `<title>` / JSON-LD `headline` per source preference, with per-source `clean` suffix stripping
- `lib/normalize.js` — UTC ISO timestamps, URL canonicalization, item IDs
- `lib/persist.js` — atomic JSON read/write
- `lib/summarize.js` — wraps `claude -p --model claude-haiku-4-5-20251001`

## Source types
- `rss` — feedparser via `rss-parser`. Used for: openai, deepmind, arxiv, simonw, latent space, interconnects.
- `hn` — hacker-news firebase API (`topstories.json` + per-item). Filtered by score≥100 + AI keyword in title.
- `hf` — HuggingFace `/api/models` JSON.
- `github` — `/trending` HTML scraped once per run, post-filtered by AI keyword.
- `sitemap` — fetches `sitemap.xml`, filters URLs by path substring(s), sorts by `<lastmod>` desc, capped at `source.limit`. For each new URL, fetches the HTML once to extract title (cached forever after — re-runs skip known URLs). Used for: anthropic, mistral, xai.
- `html-index` — fetches a blog index page, regex-extracts post URLs, then same per-URL title fetch + cache. Used for: meta-ai.

Sources can override title extraction with `title: { prefer: ['headline','title','og','twitter'], clean: [' | xAI'] }`.

## Per-source cap
Each source contributes at most `source.keep || source.limit || 30` items to news.json. Prevents firehoses (e.g. OpenAI's 929-item RSS archive) from squeezing out lab content.

## Data shape (news.json, written one level up at repo root)
```json
{
  "generated_at": "2026-05-02T14:30:00Z",
  "items": [
    {
      "id": "anthropic|https://www.anthropic.com/news/...",
      "source_id": "anthropic",
      "source_name": "Anthropic",
      "category": "lab",
      "category_emoji": "🧠",
      "hashtags": ["lab", "anthropic"],
      "title": "...",
      "headline": "...",
      "url": "https://...",
      "published_at": "2026-05-02T13:00:00Z",
      "description": "...",
      "summarize": false,
      "summarized": false,
      "summarized_at": null
    }
  ]
}
```

`headline` is what the UI/Telegram show. For non-summarize sources `headline === title`. For summarize sources, `headline` is a one-line summary from the `claude` CLI; falls back to `title` if summarization fails.

## Run
```sh
npm install
npm run fetch         # write news.json
npm run fetch:dry     # parse/normalize but don't write or summarize
npm run fetch:verbose # log per-source counts
```

## Caches & state
- `../news.json` — full catalog, sorted by `published_at` desc, capped at 500 items. Acts as the summary cache (once `summarized: true`, never re-summarized).
- `last_posted.json` — Telegram dedupe state, owned by step 2 (poster). Gitignored.

## Etiquette
- arXiv: 3.1s between hits, descriptive UA
- HN: firebase API only, never HTML scrape
- GitHub trending: 1 HTML fetch per run
- All sources: 15s timeout, errors per-source non-fatal
