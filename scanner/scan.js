// scanner/scan.js — entrypoint.
//
// Flags:
//   --dry-run     no file write, no git, prints summary
//   --no-push     write opportunities.json but skip commit/push
//   --pass=1,2,3  comma-separated pass IDs to run (default: 1)
//   --verbose     full skip-reason logging
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
import { fetchPolymarketEvents } from './lib/fetch.js';
import { SCHEMA_VERSION, emptyOutput, tallyTiers, validateOpportunity } from './lib/schema.js';
import { runPass1 } from './passes/pass1-poly-sum.js';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname, '..');
const OUTPUT_PATH = resolve(REPO_ROOT, 'opportunities.json');

function parseArgs(argv) {
  const flags = { dryRun: false, noPush: false, verbose: false, passes: [1] };
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

function loadPrevious() {
  if (!existsSync(OUTPUT_PATH)) return null;
  try {
    return JSON.parse(readFileSync(OUTPUT_PATH, 'utf8'));
  } catch {
    return null;
  }
}

// If the only thing that changed between two runs is the timestamps and
// duration, skip the git push to avoid a noisy commit history.
function nonTrivialDiff(prev, next) {
  if (!prev) return true;
  const stripVolatile = (o) => {
    const c = JSON.parse(JSON.stringify(o));
    delete c.generated_at;
    delete c.scan_duration_ms;
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
  let polyEvents = [];
  try {
    polyEvents = await fetchPolymarketEvents({ log });
    log.info(`scanner: fetched ${polyEvents.length} polymarket events`);
  } catch (e) {
    log.error(`scanner: polymarket fetch failed: ${e.message || e}`);
    errors.push({ source: 'polymarket', msg: `fetch failed: ${e.message || e}` });
  }

  // If everything failed and we have a previous file, mark its legs stale and surface errors.
  if (polyEvents.length === 0 && errors.length > 0) {
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

  if (flags.passes.includes(1)) {
    const r1 = await runPass1(polyEvents, log);
    opportunities.push(...r1.opportunities);
    stats.poly_markets_scanned += r1.stats.poly_markets_scanned || 0;
    stats.candidates_pre_filter += r1.stats.candidates_pre_filter || 0;
    log.info(`pass1: ${r1.opportunities.length} opportunities (${r1.stats.candidates_pre_filter} candidates pre-filter)`);
  }
  // passes 2/3/5 wired in subsequent steps

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
  const out = emptyOutput({ generatedAt: new Date().toISOString(), scanDurationMs: Date.now() - t0 });
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
  };

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
