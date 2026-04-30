// scanner/scan.js — entrypoint.
//
// Flags:
//   --dry-run         no file write, no git, prints summary
//   --no-push         write opportunities.json but skip commit/push
//   --pass=1,2,3,4,5  comma-separated pass IDs to run (default: 1,2,3,4,5)
//   --verbose         full skip-reason logging
//
// Output: ../opportunities.json (one level up — repo root, served by Vercel/Pages)
//
// Failure handling: if a fetch fails entirely, we preserve the previous
// opportunities[], populate errors[], flag legs as stale, and exit non-zero
// so a watchdog can notice. The page never goes blank.

import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';

import { createLogger } from './lib/log.js';
import { fetchPolymarketEvents, fetchKalshiMarketsBySeries } from './lib/fetch.js';
import { SCHEMA_VERSION, emptyOutput, tallyTiers, validateOpportunity } from './lib/schema.js';
import { appendHistory, loadHistory, pruneHistory } from './lib/history.js';
import { computePersistence } from './lib/persistence.js';
import { computeTrackRecord } from './lib/track-record.js';
import { UNDERLYINGS } from './dicts/underlyings.js';
import { runPass1 } from './passes/pass1-poly-sum.js';
import { runPass2 } from './passes/pass2-poly-monotonicity.js';
import { runPass3 } from './passes/pass3-kalshi-monotonicity.js';
import { runPass4 } from './passes/pass4-curated-cross.js';
import { runPass5 } from './passes/pass5-cross-platform.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..');
const OUTPUT_PATH = resolve(REPO_ROOT, 'opportunities.json');
const HISTORY_DIR = resolve(REPO_ROOT, 'history');
const HISTORY_LOOKBACK_DAYS = 14;
const HISTORY_RETENTION_DAYS = 30;

function parseArgs(argv) {
  const flags = { dryRun: false, noPush: false, verbose: false, passes: [1, 2, 3, 4, 5] };
  for (const a of argv.slice(2)) {
    if (a === '--dry-run') flags.dryRun = true;
    else if (a === '--no-push') flags.noPush = true;
    else if (a === '--verbose') flags.verbose = true;
    else if (a.startsWith('--pass=') || a.startsWith('--passes=')) {
      flags.passes = a.split('=')[1].split(',').map(s => parseInt(s, 10)).filter(n => !Number.isNaN(n));
    }
  }
  return flags;
}

function uniqueKalshiSeries() {
  const seen = new Set();
  for (const entry of Object.values(UNDERLYINGS)) {
    for (const s of (entry.kalshi_series || [])) seen.add(s);
  }
  return [...seen];
}

function loadPrevious() {
  if (!existsSync(OUTPUT_PATH)) return null;
  try {
    return JSON.parse(readFileSync(OUTPUT_PATH, 'utf8'));
  } catch {
    return null;
  }
}

// If the only thing that changed between two runs is the timestamps and
// duration, skip the git push to avoid a noisy commit history. Persistence
// summaries also tick every scan (scans_seen, hours_persisted, the rolling
// history window) — strip those too. We still push when a NEW opportunity
// appears, an old one disappears, or any tier/price/size field changes.
function nonTrivialDiff(prev, next) {
  if (!prev) return true;
  const stripVolatile = (o) => {
    const c = JSON.parse(JSON.stringify(o));
    delete c.generated_at;
    delete c.scan_duration_ms;
    delete c.track_record;
    if (Array.isArray(c.opportunities)) {
      for (const opp of c.opportunities) delete opp.persistence;
    }
    return c;
  };
  return JSON.stringify(stripVolatile(prev)) !== JSON.stringify(stripVolatile(next));
}

function gitPush(message) {
  const opts = { cwd: REPO_ROOT, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] };
  try {
    execFileSync('git', ['add', 'opportunities.json'], opts);
    execFileSync('git', ['commit', '-m', message], opts);
    execFileSync('git', ['push', 'origin', 'HEAD'], opts);
    return { ok: true };
  } catch (e) {
    return { ok: false, error: e.stderr?.toString() || e.message };
  }
}

async function main() {
  const flags = parseArgs(process.argv);
  const log = createLogger({ verbose: flags.verbose });
  const t0 = Date.now();
  const errors = [];

  log.info(`scanner: start passes=${flags.passes.join(',')} dry-run=${flags.dryRun} no-push=${flags.noPush}`);

  // ── Fetch ──────────────────────────────────────────────────────────────────
  const needsPoly = flags.passes.some(p => p === 1 || p === 2 || p === 4 || p === 5);
  const needsKalshi = flags.passes.some(p => p === 3 || p === 4 || p === 5);

  let polyEvents = [];
  if (needsPoly) {
    try {
      polyEvents = await fetchPolymarketEvents({ log });
      log.info(`scanner: fetched ${polyEvents.length} polymarket events`);
    } catch (e) {
      log.error(`scanner: polymarket fetch failed: ${e.message || e}`);
      errors.push({ source: 'polymarket', msg: `fetch failed: ${e.message || e}` });
    }
  }

  let kalshiMarkets = [];
  if (needsKalshi) {
    try {
      kalshiMarkets = await fetchKalshiMarketsBySeries(uniqueKalshiSeries(), { log });
      log.info(`scanner: fetched ${kalshiMarkets.length} kalshi markets`);
    } catch (e) {
      log.error(`scanner: kalshi fetch failed: ${e.message || e}`);
      errors.push({ source: 'kalshi', msg: `fetch failed: ${e.message || e}` });
    }
  }

  // If both APIs failed entirely and we have a previous file, mark its legs
  // stale and surface errors. Page never goes blank because of a transient
  // outage at one or both venues.
  const totalFetched = polyEvents.length + kalshiMarkets.length;
  if (totalFetched === 0 && errors.length > 0 && (needsPoly || needsKalshi)) {
    const prev = loadPrevious();
    if (prev && Array.isArray(prev.opportunities)) {
      for (const o of prev.opportunities) {
        const flags = new Set(o.confidence_flags || []);
        flags.add('stale_price');
        o.confidence_flags = [...flags];
        if (o.tier < 3) o.tier = 3;
      }
      const out = {
        ...prev,
        schema_version: SCHEMA_VERSION,
        generated_at: new Date().toISOString(),
        scan_duration_ms: Date.now() - t0,
        errors,
      };
      out.stats = { ...(out.stats || {}), ...tallyTiers(out.opportunities) };
      writeOutput(out, flags);
      log.error('scanner: full fetch failure — preserved previous opportunities, flagged stale, exit 1');
      process.exit(1);
    }
  }

  // ── Run passes ─────────────────────────────────────────────────────────────
  const opportunities = [];
  let stats = { poly_markets_scanned: 0, kalshi_markets_scanned: 0, candidates_pre_filter: 0 };

  if (flags.passes.includes(1) && polyEvents.length) {
    const r1 = await runPass1(polyEvents, log);
    opportunities.push(...r1.opportunities);
    stats.poly_markets_scanned = Math.max(stats.poly_markets_scanned, r1.stats.poly_markets_scanned || 0);
    stats.candidates_pre_filter += r1.stats.candidates_pre_filter || 0;
    log.info(`pass1: ${r1.opportunities.length} opportunities (${r1.stats.candidates_pre_filter} candidates pre-filter)`);
  }

  if (flags.passes.includes(2) && polyEvents.length) {
    const r2 = await runPass2(polyEvents, log);
    opportunities.push(...r2.opportunities);
    stats.poly_markets_scanned = Math.max(stats.poly_markets_scanned, r2.stats.poly_markets_scanned || 0);
    stats.candidates_pre_filter += r2.stats.candidates_pre_filter || 0;
    log.info(`pass2: ${r2.opportunities.length} opportunities (${r2.stats.candidates_pre_filter} candidates, ${r2.stats.poly_normalized} normalized)`);
  }

  if (flags.passes.includes(3) && kalshiMarkets.length) {
    const r3 = await runPass3(kalshiMarkets, log);
    opportunities.push(...r3.opportunities);
    stats.kalshi_markets_scanned += r3.stats.kalshi_markets_scanned || 0;
    stats.candidates_pre_filter += r3.stats.candidates_pre_filter || 0;
    log.info(`pass3: ${r3.opportunities.length} opportunities (${r3.stats.candidates_pre_filter} candidates, ${r3.stats.kalshi_normalized} normalized)`);
  }

  // Pass 4 runs before Pass 5 so its coveredPairs set can suppress duplicate
  // emissions in Pass 5. When the same physical (poly_market, kalshi_ticker)
  // pair would surface from both, Pass 4's curated context wins.
  let coveredPairs = new Set();
  if (flags.passes.includes(4) && polyEvents.length && kalshiMarkets.length) {
    const r4 = await runPass4(polyEvents, kalshiMarkets, log);
    opportunities.push(...r4.opportunities);
    coveredPairs = r4.coveredPairs || new Set();
    stats.candidates_pre_filter += r4.stats.candidates_pre_filter || 0;
    log.info(`pass4: ${r4.opportunities.length} opportunities (${r4.stats.candidates_pre_filter} candidates, ${r4.stats.curated_pairs_evaluated} curated pairs; poly_norm=${r4.stats.poly_normalized_for_match}, kalshi_norm=${r4.stats.kalshi_normalized_for_match})`);
  } else if (flags.passes.includes(4)) {
    log.warn('pass4: skipped — needs both polymarket + kalshi data');
  }

  if (flags.passes.includes(5) && polyEvents.length && kalshiMarkets.length) {
    const r5 = await runPass5(polyEvents, kalshiMarkets, log, { coveredPairs });
    opportunities.push(...r5.opportunities);
    stats.candidates_pre_filter += r5.stats.candidates_pre_filter || 0;
    log.info(`pass5: ${r5.opportunities.length} opportunities (${r5.stats.candidates_pre_filter} candidates, ${r5.stats.shared_canonical_keys} shared keys, ${r5.stats.curated_dedup_skipped || 0} curated-dedup skipped; poly_norm=${r5.stats.poly_normalized_for_match}, kalshi_norm=${r5.stats.kalshi_normalized_for_match})`);
  } else if (flags.passes.includes(5)) {
    log.warn('pass5: skipped — needs both polymarket + kalshi data');
  }

  // ── Validate ───────────────────────────────────────────────────────────────
  const valid = [];
  for (const o of opportunities) {
    const err = validateOpportunity(o);
    if (err) {
      log.warn(`scanner: dropping invalid opportunity ${o.id || '?'}: ${err}`);
      errors.push({ source: 'validator', msg: `${o.id || '?'}: ${err}` });
    } else {
      valid.push(o);
    }
  }

  // ── Cap per tier — keep the JSON small and signal-dense ───────────────────
  // Sort by net edge desc within tier, keep top N. Pre-cap counts in stats so
  // we know how many were filtered.
  const PER_TIER_CAP = 50;
  const preCapTallies = tallyTiers(valid);
  const capped = [];
  for (const t of [1, 2, 3]) {
    const tierOpps = valid.filter(o => o.tier === t);
    tierOpps.sort((a, b) => (b.edge_net_estimate_pct ?? 0) - (a.edge_net_estimate_pct ?? 0));
    capped.push(...tierOpps.slice(0, PER_TIER_CAP));
  }

  // ── Assemble ───────────────────────────────────────────────────────────────
  const generatedAtIso = new Date().toISOString();
  const out = emptyOutput({ generatedAt: generatedAtIso, scanDurationMs: Date.now() - t0 });

  // ── Persistence: roll up prior scan samples into per-opp summaries ────────
  // History is local-only (gitignored) — opportunities.json carries the
  // computed summary, which is what the dashboard renders.
  const priorHistory = loadHistory(HISTORY_DIR, HISTORY_LOOKBACK_DAYS);
  for (const o of capped) {
    const prior = priorHistory.get(o.id) || [];
    const currentSample = {
      ts: generatedAtIso,
      id: o.id,
      tier: o.tier,
      edge_gross_pct: o.edge_gross_pct ?? null,
      edge_net_estimate_pct: o.edge_net_estimate_pct ?? null,
      max_size: o.max_executable_size_per_leg_usd ?? null,
      flags: o.confidence_flags || [],
    };
    const summary = computePersistence(prior, currentSample);
    if (summary) o.persistence = summary;
  }

  out.opportunities = capped;
  out.errors = errors;
  out.stats = {
    ...out.stats,
    ...stats,
    ...tallyTiers(capped),
    pre_cap_tier1: preCapTallies.tier1_count,
    pre_cap_tier2: preCapTallies.tier2_count,
    pre_cap_tier3: preCapTallies.tier3_count,
    per_tier_cap: PER_TIER_CAP,
    history_lookback_days: HISTORY_LOOKBACK_DAYS,
  };

  // Track record — aggregate of "what happened to flagged opps" computed off
  // the same history. Frontend renders this above the tier sections.
  // Note: priorHistory only contains samples from BEFORE this scan; for the
  // track-record rollup we want today's samples included too, otherwise opps
  // appearing for the first time would inflate "left_feed" on next scan. So
  // we materialize a combined Map.
  const liveIds = new Set(capped.map(o => o.id));
  const combinedHistory = new Map();
  for (const [id, samples] of priorHistory.entries()) {
    combinedHistory.set(id, samples.slice());
  }
  for (const o of capped) {
    const arr = combinedHistory.get(o.id) || [];
    arr.push({
      ts: generatedAtIso,
      id: o.id,
      tier: o.tier,
      edge_gross_pct: o.edge_gross_pct ?? null,
    });
    combinedHistory.set(o.id, arr);
  }
  out.track_record = computeTrackRecord(combinedHistory, liveIds, {
    lookbackDays: HISTORY_LOOKBACK_DAYS,
  });

  // Append today's samples to local JSONL + prune old day files. Done after
  // assembly so a write failure mid-pipeline doesn't leave a half-baked file.
  // Honor --dry-run (no fs side effects). --no-push still appends (history is
  // local; no-push only suppresses git).
  if (!flags.dryRun) {
    try {
      const r = appendHistory(HISTORY_DIR, generatedAtIso, capped);
      log.info(`history: appended ${r.written} samples → ${r.path}`);
    } catch (e) {
      log.warn(`history: append failed: ${e.message}`);
    }
    try {
      const p = pruneHistory(HISTORY_DIR, HISTORY_RETENTION_DAYS, log);
      if (p.deleted > 0) log.info(`history: pruned ${p.deleted} day files older than ${HISTORY_RETENTION_DAYS}d`);
    } catch (e) {
      log.warn(`history: prune failed: ${e.message}`);
    }
  }

  // ── Skip log summary (always, since it's the debugging surface) ────────────
  const skipSummary = log.skipSummary();
  if (skipSummary.length) {
    log.info('scanner: skip summary');
    for (const s of skipSummary) log.info(`  ${s.count.toString().padStart(5)}× ${s.reason}`);
  }

  log.info(`scanner: complete in ${Date.now() - t0}ms — T1=${out.stats.tier1_count} T2=${out.stats.tier2_count} T3=${out.stats.tier3_count}`);

  // ── Write + push ───────────────────────────────────────────────────────────
  if (flags.dryRun) {
    log.info(`scanner: --dry-run — skipping write to ${OUTPUT_PATH}`);
    log.info(JSON.stringify({ ...out, opportunities: `[${out.opportunities.length} items]` }, null, 2));
    return;
  }

  const prev = loadPrevious();
  const changed = nonTrivialDiff(prev, out);
  writeOutput(out, flags);

  if (flags.noPush) {
    log.info('scanner: --no-push — skipping git commit/push');
    return;
  }
  if (!changed) {
    log.info('scanner: no opportunity changes since last scan — skipping git push');
    return;
  }

  const msg = `scan: ${out.generated_at}, T1=${out.stats.tier1_count} T2=${out.stats.tier2_count} T3=${out.stats.tier3_count}`;
  const push = gitPush(msg);
  if (push.ok) log.info(`scanner: pushed → "${msg}"`);
  else log.error(`scanner: git push failed: ${push.error}`);
}

function writeOutput(out, flags) {
  writeFileSync(OUTPUT_PATH, JSON.stringify(out, null, 2) + '\n', 'utf8');
}

main().catch(e => {
  console.error('scanner: fatal', e);
  process.exit(2);
});
