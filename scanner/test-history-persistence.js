// Hand-crafted unit tests for history.js + persistence.js.
// Run: node scanner/test-history-persistence.js

import { mkdtempSync, rmSync, readdirSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

import { appendHistory, loadHistory, pruneHistory } from './lib/history.js';
import { computePersistence, classifyTrend, linearSlope } from './lib/persistence.js';
import { createLogger } from './lib/log.js';

let pass = 0, fail = 0;
function assert(cond, msg) {
  if (cond) { pass++; console.log(`  ✓ ${msg}`); }
  else { fail++; console.log(`  ✗ ${msg}`); }
}
const log = createLogger({ verbose: false });

function tmpDir() {
  return mkdtempSync(join(tmpdir(), 'probbrain-history-'));
}

// ── linearSlope ─────────────────────────────────────────────────────────────
console.log('Test 1: linearSlope — constant series → slope 0');
{
  assert(linearSlope([5, 5, 5, 5, 5]) === 0, 'all 5s → slope 0');
}
console.log('\nTest 2: linearSlope — strictly increasing → positive');
{
  const s = linearSlope([1, 2, 3, 4, 5]);
  assert(Math.abs(s - 1) < 1e-9, `1,2,3,4,5 → slope 1 (got ${s})`);
}
console.log('\nTest 3: linearSlope — strictly decreasing → negative');
{
  const s = linearSlope([5, 4, 3, 2, 1]);
  assert(Math.abs(s - (-1)) < 1e-9, `5,4,3,2,1 → slope -1 (got ${s})`);
}
console.log('\nTest 4: linearSlope — fewer than 2 points → NaN');
{
  assert(Number.isNaN(linearSlope([])) && Number.isNaN(linearSlope([5])), 'empty/single → NaN');
}

// ── classifyTrend ───────────────────────────────────────────────────────────
console.log('\nTest 5: classifyTrend — <3 samples → "new"');
{
  assert(classifyTrend([5]) === 'new', 'single sample');
  assert(classifyTrend([5, 5]) === 'new', 'two samples');
}
console.log('\nTest 6: classifyTrend — flat → "stable"');
{
  assert(classifyTrend([5, 5.05, 5.1, 5.05, 5]) === 'stable', 'small noise still stable');
}
console.log('\nTest 7: classifyTrend — clearly widening');
{
  assert(classifyTrend([2, 3, 4, 5, 6, 7]) === 'widening', '2→7 series');
}
console.log('\nTest 8: classifyTrend — clearly tightening');
{
  assert(classifyTrend([7, 6, 5, 4, 3, 2]) === 'tightening', '7→2 series');
}

// ── computePersistence ──────────────────────────────────────────────────────
console.log('\nTest 9: computePersistence — only current sample → "new" + scans_seen 1');
{
  const cur = { ts: '2026-04-30T12:00:00Z', edge_gross_pct: 5.0 };
  const p = computePersistence([], cur);
  assert(p.scans_seen === 1, `scans_seen 1 (got ${p.scans_seen})`);
  assert(p.trend === 'new', `trend new (got ${p.trend})`);
  assert(p.first_seen_at === cur.ts, 'first_seen_at = current ts');
  assert(p.hours_persisted === 0, '0 hours persisted on first sight');
}

console.log('\nTest 10: computePersistence — hours_persisted across days');
{
  const prior = [
    { ts: '2026-04-29T12:00:00Z', edge_gross_pct: 4.0 },
    { ts: '2026-04-29T18:00:00Z', edge_gross_pct: 4.5 },
  ];
  const cur = { ts: '2026-04-30T12:00:00Z', edge_gross_pct: 5.0 };
  const p = computePersistence(prior, cur);
  assert(p.scans_seen === 3, `scans_seen 3 (got ${p.scans_seen})`);
  assert(p.first_seen_at === '2026-04-29T12:00:00Z', 'first_seen_at = oldest');
  assert(Math.abs(p.hours_persisted - 24) < 0.01, `hours ≈ 24 (got ${p.hours_persisted})`);
}

console.log('\nTest 11: computePersistence — gross_pct_history rolling window of 10');
{
  const prior = [];
  for (let i = 0; i < 15; i++) {
    prior.push({ ts: `2026-04-30T${String(i).padStart(2, '0')}:00:00Z`, edge_gross_pct: 5 + i * 0.5 });
  }
  const cur = { ts: '2026-04-30T15:00:00Z', edge_gross_pct: 12.5 };
  const p = computePersistence(prior, cur);
  assert(p.gross_pct_history.length === 10, `window length 10 (got ${p.gross_pct_history.length})`);
  assert(p.gross_pct_history[p.gross_pct_history.length - 1] === 12.5, `most recent = 12.5 (got ${p.gross_pct_history.at(-1)})`);
  assert(p.trend === 'widening', `trend widening on 0.5pp/scan ramp (got ${p.trend})`);
  assert(p.scans_seen === 16, 'scans_seen counts all, not just window');
}

console.log('\nTest 12: computePersistence — null when no samples');
{
  assert(computePersistence([], null) === null, 'returns null');
}

// ── history.js round-trip ───────────────────────────────────────────────────
console.log('\nTest 13: appendHistory + loadHistory round-trip');
{
  const dir = tmpDir();
  try {
    const opps = [
      { id: 'op-1', tier: 1, edge_gross_pct: 5.0, edge_net_estimate_pct: 2.0, max_executable_size_per_leg_usd: 1000, confidence_flags: ['curated_pair'] },
      { id: 'op-2', tier: 3, edge_gross_pct: 3.0, edge_net_estimate_pct: -1.0, max_executable_size_per_leg_usd: 200, confidence_flags: [] },
    ];
    const ts = '2026-04-30T12:00:00Z';
    const r = appendHistory(dir, ts, opps);
    assert(r.written === 2, `wrote 2 lines (got ${r.written})`);

    const loaded = loadHistory(dir, 14);
    assert(loaded.size === 2, `loaded 2 ids (got ${loaded.size})`);
    assert(loaded.get('op-1').length === 1, 'op-1 has 1 sample');
    assert(loaded.get('op-1')[0].edge_gross_pct === 5.0, 'edge_gross_pct preserved');
    assert(loaded.get('op-1')[0].flags.includes('curated_pair'), 'flags preserved');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

console.log('\nTest 14: appendHistory — multiple appends to same day file');
{
  const dir = tmpDir();
  try {
    appendHistory(dir, '2026-04-30T12:00:00Z', [{ id: 'a', tier: 1, edge_gross_pct: 5 }]);
    appendHistory(dir, '2026-04-30T12:15:00Z', [{ id: 'a', tier: 1, edge_gross_pct: 5.2 }]);
    appendHistory(dir, '2026-04-30T12:30:00Z', [{ id: 'a', tier: 1, edge_gross_pct: 5.4 }]);
    const loaded = loadHistory(dir, 14);
    assert(loaded.get('a').length === 3, `3 samples (got ${loaded.get('a').length})`);
    const grosses = loaded.get('a').map(s => s.edge_gross_pct);
    assert(JSON.stringify(grosses) === JSON.stringify([5, 5.2, 5.4]), 'samples sorted oldest→newest');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

console.log('\nTest 15: loadHistory — sinceDays cutoff');
{
  const dir = tmpDir();
  try {
    const old = new Date(Date.now() - 30 * 86400_000).toISOString();
    const recent = new Date().toISOString();
    appendHistory(dir, old, [{ id: 'a', tier: 1, edge_gross_pct: 1 }]);
    appendHistory(dir, recent, [{ id: 'a', tier: 1, edge_gross_pct: 5 }]);
    const loaded = loadHistory(dir, 7);
    assert(loaded.get('a')?.length === 1, '7-day cutoff drops 30d-old sample');
    assert(loaded.get('a')[0].edge_gross_pct === 5, 'kept recent sample');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

console.log('\nTest 16: loadHistory — corrupt line skipped, not thrown');
{
  const dir = tmpDir();
  try {
    appendHistory(dir, new Date().toISOString(), [{ id: 'a', tier: 1, edge_gross_pct: 5 }]);
    // Inject a bad line
    const fs = await import('node:fs');
    const files = readdirSync(dir);
    fs.appendFileSync(join(dir, files[0]), '{not json\n', 'utf8');
    const loaded = loadHistory(dir, 14);
    assert(loaded.get('a')?.length === 1, '1 valid sample, bad line skipped');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

console.log('\nTest 17: pruneHistory — old day file deleted');
{
  const dir = tmpDir();
  try {
    const old = new Date(Date.now() - 60 * 86400_000).toISOString();
    const recent = new Date().toISOString();
    appendHistory(dir, old, [{ id: 'a', tier: 1, edge_gross_pct: 1 }]);
    appendHistory(dir, recent, [{ id: 'a', tier: 1, edge_gross_pct: 5 }]);
    const before = readdirSync(dir).length;
    const r = pruneHistory(dir, 30, log);
    const after = readdirSync(dir).length;
    assert(r.deleted === 1, `pruned 1 (got ${r.deleted})`);
    assert(after === before - 1, 'one file removed');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

console.log('\nTest 18: end-to-end — history → loadHistory → computePersistence');
{
  const dir = tmpDir();
  try {
    // Simulate 5 prior scans, all ~15min apart, with gross drifting downward.
    const baseMs = Date.parse('2026-04-30T10:00:00Z');
    for (let i = 0; i < 5; i++) {
      const ts = new Date(baseMs + i * 15 * 60_000).toISOString();
      appendHistory(dir, ts, [{ id: 'op-x', tier: 2, edge_gross_pct: 6 - i * 0.5 }]);
    }
    const prior = (loadHistory(dir, 14)).get('op-x') || [];
    const cur = { ts: '2026-04-30T11:15:00Z', edge_gross_pct: 3.5 };
    const p = computePersistence(prior, cur);
    assert(p.scans_seen === 6, `scans_seen 6 (got ${p.scans_seen})`);
    assert(p.trend === 'tightening', `trend tightening (got ${p.trend})`);
    assert(Math.abs(p.hours_persisted - 1.25) < 0.01, `hours ≈ 1.25 (got ${p.hours_persisted})`);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

console.log(`\n${pass}/${pass + fail} tests passed`);
process.exit(fail > 0 ? 1 : 0);
