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
const KALSHI = 'https://api.elections.kalshi.com/trade-api/v2';

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

// Kalshi public markets endpoint — cursor-paginated. Filtering by series_ticker
// pulls just the markets belonging to that underlying (BTC/ETH/SOL/etc.),
// which is dramatically cheaper than fetching all open markets and filtering.
async function fetchKalshiPaginated(url, { log, label }) {
  const all = [];
  let cursor = null;
  let pages = 0;
  while (true) {
    const next = cursor ? `${url}&cursor=${encodeURIComponent(cursor)}` : url;
    const data = await fetchJson(next);
    const page = data.markets || [];
    all.push(...page);
    pages++;
    if (log) log.info(`[fetch] kalshi ${label} page=${pages} got=${page.length} total=${all.length}`);
    cursor = data.cursor || null;
    if (!cursor || page.length === 0) break;
    // Safety stop — Kalshi's open universe per series should never exceed
    // a few thousand markets. Hard cap so a misbehaving cursor can't loop.
    if (pages > 25) {
      if (log) log.warn(`[fetch] kalshi ${label} hit page cap (${pages})`);
      break;
    }
  }
  return all;
}

// Fetch all open Kalshi markets for the given series_ticker prefixes. We
// query each series separately because the bulk markets endpoint without
// a series filter doesn't include series_ticker on every record.
export async function fetchKalshiMarketsBySeries(seriesTickers, { pageLimit = 200, log } = {}) {
  const all = [];
  const seenTickers = new Set();
  for (const series of seriesTickers) {
    const url = `${KALSHI}/markets?status=open&limit=${pageLimit}&series_ticker=${encodeURIComponent(series)}`;
    let page;
    try {
      page = await fetchKalshiPaginated(url, { log, label: series });
    } catch (e) {
      if (log) log.warn(`[fetch] kalshi ${series} failed: ${e.message || e}`);
      continue;
    }
    for (const m of page) {
      if (!m || !m.ticker || seenTickers.has(m.ticker)) continue;
      seenTickers.add(m.ticker);
      // Annotate with the series we queried under so normalization has a
      // stable hint even if the record itself doesn't carry series_ticker.
      m._series_ticker_hint = series;
      all.push(m);
    }
  }
  return all;
}
