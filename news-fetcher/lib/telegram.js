const TG_API = 'https://api.telegram.org';
const SEND_TIMEOUT_MS = 20_000;

function escapeHtml(s) {
  return (s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function displayDomain(url) {
  try {
    const h = new URL(url).hostname.toLowerCase();
    return h.startsWith('www.') ? h.slice(4) : h;
  } catch {
    return url;
  }
}

export function formatPost(item) {
  const headline = escapeHtml(item.headline || item.title);
  const domain = escapeHtml(displayDomain(item.url));
  const href = escapeHtml(item.url);
  return `${headline}\n\n🔗 <a href="${href}">${domain}</a>`;
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
