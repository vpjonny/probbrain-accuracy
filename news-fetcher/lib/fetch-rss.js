import Parser from 'rss-parser';
import { USER_AGENT, FETCH_TIMEOUT_MS, matchesAiKeyword } from '../sources.js';
import { toUtcIso, canonicalUrl, cleanTitle } from './normalize.js';

const parser = new Parser({
  timeout: FETCH_TIMEOUT_MS,
  headers: { 'User-Agent': USER_AGENT, 'Accept': 'application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8' },
});

export async function fetchRss(source) {
  const feed = await parser.parseURL(source.url);
  let items = (feed.items || []).map(it => ({
    title: cleanTitle(it.title || ''),
    url: canonicalUrl(it.link || it.guid || ''),
    published_at: toUtcIso(it.isoDate || it.pubDate || it.published || it.updated),
    description: cleanTitle(it.contentSnippet || it.summary || ''),
  })).filter(it => it.title && it.url);
  if (source.aiOnly) items = items.filter(matchesAiKeyword);
  return items;
}
