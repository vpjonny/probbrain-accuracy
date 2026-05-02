import { itemAnchor } from './normalize.js';

const TG_API = 'https://api.telegram.org';
const SEND_TIMEOUT_MS = 20_000;
const NEWS_PAGE = 'https://probbrain.com/news';
const DESC_MAX = 220;

function escapeHtml(s) {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

// Strip HTML, decode common entities, collapse whitespace, truncate. Some
// feeds (Simon's atom, OpenAI RSS) ship HTML in <description>; others ship
// plain text. We need clean text either way before re-escaping for Telegram.
function cleanDescription(raw) {
  if (!raw) return '';
  let s = String(raw)
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, ' ')
    .trim();
  if (s.length > DESC_MAX) s = s.slice(0, DESC_MAX - 1).replace(/\s+\S*$/, '') + '…';
  return s;
}

// Drop the description if it's just a near-duplicate of the title (common
// for OpenAI/Anthropic feeds that put the same line in both fields).
function descIsRedundant(title, desc) {
  if (!desc) return true;
  const t = title.toLowerCase().trim();
  const d = desc.toLowerCase().trim();
  if (!t || !d) return !d;
  if (d.startsWith(t.slice(0, Math.min(50, t.length)))) return true;
  if (t.startsWith(d.slice(0, Math.min(50, d.length)))) return true;
  return false;
}

export function formatPost(item) {
  const rawHeadline = (item.headline || item.title || '').trim();
  const headline = escapeHtml(rawHeadline);
  const sourceName = (item.source_name || '').trim();
  const emoji = item.category_emoji || '';
  const anchor = itemAnchor(item.id);

  const desc = cleanDescription(item.description);
  const showDesc = desc && !descIsRedundant(rawHeadline, desc);

  const tags = Array.from(new Set([item.category, ...(item.hashtags || [])]))
    .filter(Boolean)
    .slice(0, 3)
    .map(h => '#' + h)
    .join(' ');

  const lines = [`<b>${headline}</b>`];
  if (showDesc) lines.push(escapeHtml(desc));
  const attribution = sourceName ? `— ${emoji} <i>${escapeHtml(sourceName)}</i>` : '';
  const footer = `<a href="${NEWS_PAGE}#${anchor}">read on probbrain.com</a>`;
  // Attribution + tags + read-more on the same trailing block, separated by
  // line breaks so even a one-word headline gets visual weight underneath.
  const trailer = [attribution, tags ? `${escapeHtml(tags)} · ${footer}` : footer]
    .filter(Boolean)
    .join('\n');
  lines.push(trailer);

  return lines.join('\n\n');
}

export async function sendMessage({ token, chat_id, text }) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), SEND_TIMEOUT_MS);
  try {
    const r = await fetch(`${TG_API}/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id,
        text,
        parse_mode: 'HTML',
        disable_web_page_preview: true,
      }),
      signal: ctrl.signal,
    });
    const body = await r.json();
    if (!body.ok) {
      const err = new Error(`telegram: ${body.error_code} ${body.description}`);
      err.body = body;
      throw err;
    }
    return body.result;
  } finally {
    clearTimeout(t);
  }
}
