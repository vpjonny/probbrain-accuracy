// page-pills.js — drop-in floating pills for any ProbBrain page.
// Adds:
//   • Status pill  — links to /status, dot color reflects pipeline health.
//   • Visit count  — site-wide hit counter; increments once per session
//                    via sessionStorage so navigation doesn't inflate.
// Usage: <script src="/assets/page-pills.js" defer></script>
// Self-contained: injects its own <style>, builds DOM, no markup needed.

(function () {
  if (window.__probbrainPills) return;          // idempotent
  window.__probbrainPills = true;

  const HIT_NS = 'probbrain-dashboard';
  const HIT_KEY = 'visits';
  const HIT_BASE = 'https://abacus.jasoncameron.dev';
  const SESSION_FLAG = 'pb_hit_counted_v1';

  const path = location.pathname.replace(/\/$/, '').replace(/\.html$/, '');
  const onStatusPage      = path === '/status';
  const onMethodologyPage = path === '/methodology';
  const onArbitragePage   = path === '/arbitrage';

  // ── Styles ─────────────────────────────────────────────────────────────
  const css = `
    .pb-pill {
      position: fixed; right: 16px;
      display: flex; align-items: center; gap: 7px;
      background: #171717;
      border: 1px solid #222;
      border-radius: 20px;
      padding: 6px 12px;
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.72rem;
      color: #a0a0a0;
      text-decoration: none;
      z-index: 100;
      transition: border-color .15s, color .15s, background .15s, box-shadow .15s;
    }
    .pb-pill:hover { border-color: #6366f1; color: #e8e8e8; }
    .pb-status { bottom: 56px; }
    .pb-visits { bottom: 16px; }
    .pb-status .pb-dot {
      width: 7px; height: 7px; border-radius: 50%; background: #555;
      flex: none;
      transition: background .2s, box-shadow .2s;
    }
    .pb-status.ok   .pb-dot { background: #22c55e; box-shadow: 0 0 0 0 rgba(34,197,94,.6); animation: pb-pulse 2.4s cubic-bezier(.4,0,.6,1) infinite; }
    .pb-status.warn .pb-dot { background: #f59e0b; box-shadow: 0 0 6px rgba(245,158,11,.55); }
    .pb-status.bad  .pb-dot { background: #ef4444; box-shadow: 0 0 8px rgba(239,68,68,.65); }
    @keyframes pb-pulse {
      0% { box-shadow: 0 0 0 0 rgba(34,197,94,.55); }
      70% { box-shadow: 0 0 0 8px rgba(34,197,94,0); }
      100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); }
    }
    .pb-status .pb-label { color: #e8e8e8; font-weight: 700; }
    .pb-status .pb-sub   { color: #888; }
    .pb-visits svg { width: 13px; height: 13px; flex: none; }
    .pb-visits .pb-count { font-family: 'JetBrains Mono', ui-monospace, monospace;
                           font-weight: 700; color: #e8e8e8;
                           font-variant-numeric: tabular-nums; }
    .pb-visits .pb-vlabel { color: #888; }
    .pb-visits.loaded { animation: pb-count-pop .3s ease; }
    @keyframes pb-count-pop {
      0% { transform: scale(1); } 50% { transform: scale(1.10); } 100% { transform: scale(1); }
    }
    @media (prefers-reduced-motion: reduce) {
      .pb-status.ok .pb-dot { animation: none; }
      .pb-visits.loaded     { animation: none; }
    }
    @media (max-width: 640px) {
      .pb-pill   { padding: 4px 9px; font-size: 0.65rem; right: 12px; }
      .pb-visits { bottom: 12px; }
      .pb-status { bottom: 46px; }
    }

    /* Bottom-LEFT nav pills — mirror the right-side stack but use the
       header-cta indigo gradient treatment (these are buttons, not status). */
    .pb-nav {
      position: fixed; left: 16px;
      display: inline-flex; align-items: center; gap: 6px;
      padding: 7px 12px; border-radius: 20px;
      background: linear-gradient(135deg, rgba(99,102,241,.18), rgba(139,92,246,.12));
      border: 1px solid rgba(99,102,241,.32);
      color: #e8e8e8; text-decoration: none;
      font-family: 'Inter', system-ui, sans-serif;
      font-size: 0.78rem; font-weight: 600; letter-spacing: .01em;
      z-index: 100;
      transition: border-color .15s, background .15s, transform .12s, box-shadow .15s;
      box-shadow: 0 4px 14px rgba(99,102,241,.10);
    }
    .pb-nav:hover {
      border-color: rgba(99,102,241,.65);
      background: linear-gradient(135deg, rgba(99,102,241,.30), rgba(139,92,246,.20));
      transform: translateY(-1px);
      box-shadow: 0 8px 22px rgba(99,102,241,.20);
    }
    .pb-nav.top    { bottom: 56px; }
    .pb-nav.bottom { bottom: 16px; }
    @media (max-width: 640px) {
      .pb-nav        { padding: 5px 10px; font-size: 0.70rem; left: 12px; }
      .pb-nav.top    { bottom: 46px; }
      .pb-nav.bottom { bottom: 12px; }
    }
  `;
  const style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);

  // ── DOM ────────────────────────────────────────────────────────────────
  let statusPill = null;
  if (!onStatusPage) {
    statusPill = document.createElement('a');
    statusPill.className = 'pb-pill pb-status ok';
    statusPill.href = '/status';
    statusPill.title = 'Pipeline status & uptime';
    statusPill.innerHTML =
      '<span class="pb-dot" aria-hidden="true"></span>' +
      '<span class="pb-label">Status</span>' +
      '<span class="pb-sub" data-pp-sub>live</span>';
    document.body.appendChild(statusPill);
  }

  const visits = document.createElement('div');
  visits.className = 'pb-pill pb-visits';
  visits.title = 'Total page visits';
  visits.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>' +
    '</svg>' +
    '<span class="pb-count" data-pp-count>—</span>' +
    '<span class="pb-vlabel">visits</span>';
  document.body.appendChild(visits);

  // ── Hit counter ────────────────────────────────────────────────────────
  // Use /hit (increment) once per session; /get (read-only) on every other
  // pageview so cross-page navigation doesn't inflate the count.
  let counted = false;
  try { counted = !!sessionStorage.getItem(SESSION_FLAG); } catch {}
  const hitUrl = `${HIT_BASE}/${counted ? 'get' : 'hit'}/${HIT_NS}/${HIT_KEY}`;
  fetch(hitUrl)
    .then(r => r.ok ? r.json() : null)
    .then(d => {
      if (!d || d.value == null) return;
      try { sessionStorage.setItem(SESSION_FLAG, '1'); } catch {}
      const el = visits.querySelector('[data-pp-count]');
      if (el) el.textContent = d.value.toLocaleString();
      visits.classList.add('loaded');
    })
    .catch(() => {});

  // ── Status severity ────────────────────────────────────────────────────
  if (statusPill) {
    const CADENCE_MS = 15 * 60 * 1000;
    const ageMs = iso => iso ? Math.max(0, Date.now() - new Date(iso).getTime()) : Infinity;
    const fresh = iso => { const a = ageMs(iso); return a < 2 * CADENCE_MS ? 'ok' : a < 4 * CADENCE_MS ? 'warn' : 'bad'; };
    const lat   = s => s == null ? 'idle' : s <= 60 ? 'ok' : s <= 300 ? 'warn' : 'bad';

    Promise.all([
      fetch('/news.json',          { cache: 'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/opportunities.json', { cache: 'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null),
      fetch('/status.json',        { cache: 'no-store' }).then(r => r.ok ? r.json() : null).catch(() => null),
    ]).then(([news, opps, status]) => {
      const levels = [
        fresh(news?.generated_at),
        fresh(opps?.generated_at),
        lat(status?.telegram?.median_latency_sec),
        lat(status?.bluesky?.median_latency_sec),
      ];
      let level = 'ok';
      if (levels.includes('bad')) level = 'bad';
      else if (levels.includes('warn')) level = 'warn';
      statusPill.classList.remove('ok', 'warn', 'bad');
      statusPill.classList.add(level);
      const sub = statusPill.querySelector('[data-pp-sub]');
      if (sub) sub.textContent = level === 'ok' ? 'live' : level === 'warn' ? 'stale' : 'down';
    }).catch(() => { /* keep default green */ });
  }

  // ── Bottom-left nav pills ──────────────────────────────────────────────
  // Methodology + Arbitrage. Each pill suppresses itself on its own page,
  // and if only one is visible it drops to the bottom slot so it doesn't
  // float alone in the upper position.
  const navItems = [
    { href: '/methodology', label: '📊 Methodology', title: 'How the arb scanner works', skip: onMethodologyPage },
    { href: '/arbitrage',   label: '⚖ Arbitrage',    title: 'Polymarket × Kalshi arbitrage scanner', skip: onArbitragePage },
  ];
  const visible = navItems.filter(it => !it.skip);
  visible.forEach((it, i) => {
    const a = document.createElement('a');
    // If both visible: first → top slot, second → bottom slot. If only one
    // visible: it always takes the bottom slot.
    const slot = (visible.length === 2 && i === 0) ? 'top' : 'bottom';
    a.className = `pb-nav ${slot}`;
    a.href = it.href;
    a.title = it.title;
    a.textContent = it.label;
    document.body.appendChild(a);
  });
})();
