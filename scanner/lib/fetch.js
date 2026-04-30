// scanner/lib/fetch.js — built-in fetch with exponential backoff retries.
// 3 attempts at 1s, 3s, 9s. After that surface the error.

const RETRY_DELAYS_MS = [1000, 3000, 9000];
const DEFAULT_TIMEOUT_MS = 30_000;

export async function fetchJson(url, { timeoutMs = DEFAULT_TIMEOUT_MS, headers = {} } = {}) {
  let lastErr;
  for (let attempt = 0; attempt <= RETRY_DELAYS_MS.length; attempt++) {
    try {
      const ac = new AbortController();
      const t = setTimeout(() => ac.abort(), timeoutMs);
      try {
        const resp = await fetch(url, { headers, signal: ac.signal });
        if (!resp.ok) throw new Error(`HTTP ${resp.status} ${resp.statusText}`);
        return await resp.json();
      } finally {
        clearTimeout(t);
      }
    } catch (e) {
      lastErr = e;
      if (attempt < RETRY_DELAYS_MS.length) {
        await new Promise(r => setTimeout(r, RETRY_DELAYS_MS[attempt]));
      }
    }
  }
  throw lastErr;
}

const GAMMA = 'https://gamma-api.polymarket.com';

// Polymarket Gamma API — paginate active, non-closed events with their markets.
// Each event includes negRisk flag and a markets[] array.
export async function fetchPolymarketEvents({ pageLimit = 500, log } = {}) {
  const events = [];
  let offset = 0;
  while (true) {
    const url = `${GAMMA}/events?active=true&closed=false&limit=${pageLimit}&offset=${offset}`;
    const page = await fetchJson(url);
    if (!Array.isArray(page) || page.length === 0) break;
    events.push(...page);
    if (log) log.info(`[fetch] poly events offset=${offset} got=${page.length} total=${events.length}`);
    if (page.length < pageLimit) break;
    offset += pageLimit;
  }
  return events;
}
