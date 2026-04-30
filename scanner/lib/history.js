// scanner/lib/history.js — local persistence layer for the scanner's own
// memory across runs. Daily JSONL files (one line per opportunity per scan)
// stored locally and gitignored. We do NOT commit history to git: it'd
// generate a noisy diff every 15min, and the persistence summary embedded in
// opportunities.json is the only public artifact.
//
// File shape: history/YYYY-MM-DD.jsonl
// Line shape: {"ts":"2026-04-30T12:15:00Z","id":"pass4-curated-...","tier":3,
//              "edge_gross_pct":5.0,"edge_net_estimate_pct":-4.2,
//              "max_size":2000,"flags":["curated_pair"]}
//
// Append-only. Reads concatenate the last N daily files. No locking — the
// scanner is single-process per machine via systemd timer.

import { readdirSync, readFileSync, appendFileSync, mkdirSync, existsSync, unlinkSync } from 'node:fs';
import { join } from 'node:path';

function dayKeyFromIso(iso) {
  return String(iso).slice(0, 10);
}
function todayDayKey() {
  return new Date().toISOString().slice(0, 10);
}

// Compact projection — full opportunities are heavy, we only need the
// changing fields to reconstruct trend + the bare minimum to diagnose why an
// opp left the feed (leg_ids + resolution_date). Keep this stable; both
// persistence.js and track-record.js read what's written here. Old samples
// missing leg_ids/resolution_date stay loadable — downstream classifiers
// fall back to "unknown" rather than crashing.
function compactSample(generatedAtIso, opp) {
  const legIds = Array.isArray(opp.legs)
    ? opp.legs.map(l => ({ platform: l.platform, market_id: String(l.market_id ?? '') }))
    : [];
  return {
    ts: generatedAtIso,
    id: opp.id,
    tier: opp.tier,
    edge_gross_pct: opp.edge_gross_pct ?? null,
    edge_net_estimate_pct: opp.edge_net_estimate_pct ?? null,
    max_size: opp.max_executable_size_per_leg_usd ?? null,
    flags: Array.isArray(opp.confidence_flags) ? opp.confidence_flags : [],
    leg_ids: legIds,
    resolution_date: opp.resolution_date || null,
  };
}

// Append a batch of compacted samples to today's JSONL file. Creates the dir
// + file if missing. One fs.appendFileSync call per scan (not per sample) —
// concatenate first.
export function appendHistory(historyDir, generatedAtIso, opportunities) {
  if (!existsSync(historyDir)) mkdirSync(historyDir, { recursive: true });
  const day = dayKeyFromIso(generatedAtIso) || todayDayKey();
  const path = join(historyDir, `${day}.jsonl`);
  const lines = [];
  for (const o of opportunities) {
    if (!o || !o.id) continue;
    lines.push(JSON.stringify(compactSample(generatedAtIso, o)));
  }
  if (lines.length === 0) return { written: 0, path };
  appendFileSync(path, lines.join('\n') + '\n', 'utf8');
  return { written: lines.length, path };
}

// Load all samples from the last `sinceDays` daily files, grouped by id.
// Returns Map<id, samples[]> with samples sorted oldest-first per id.
// Robust to corrupt lines — bad JSON is skipped, not thrown.
export function loadHistory(historyDir, sinceDays = 14) {
  const out = new Map();
  if (!existsSync(historyDir)) return out;

  const cutoffMs = Date.now() - sinceDays * 86400_000;
  let files;
  try {
    files = readdirSync(historyDir).filter(f => f.endsWith('.jsonl')).sort();
  } catch {
    return out;
  }

  for (const fname of files) {
    const day = fname.slice(0, 10);
    const t = Date.parse(`${day}T00:00:00Z`);
    if (Number.isFinite(t) && t < cutoffMs - 86400_000) continue; // -1d slack

    let raw;
    try { raw = readFileSync(join(historyDir, fname), 'utf8'); }
    catch { continue; }

    for (const line of raw.split('\n')) {
      if (!line) continue;
      let s;
      try { s = JSON.parse(line); } catch { continue; }
      if (!s || !s.id) continue;
      const sampleMs = Date.parse(s.ts);
      if (!Number.isFinite(sampleMs) || sampleMs < cutoffMs) continue;
      if (!out.has(s.id)) out.set(s.id, []);
      out.get(s.id).push(s);
    }
  }

  for (const arr of out.values()) {
    arr.sort((a, b) => Date.parse(a.ts) - Date.parse(b.ts));
  }
  return out;
}

// Delete daily files older than retentionDays. Best-effort — failures are
// logged-but-non-fatal so a permission glitch doesn't tank a scan.
export function pruneHistory(historyDir, retentionDays = 30, log = null) {
  if (!existsSync(historyDir)) return { deleted: 0 };
  const cutoffMs = Date.now() - retentionDays * 86400_000;
  let deleted = 0;
  let files;
  try {
    files = readdirSync(historyDir).filter(f => f.endsWith('.jsonl'));
  } catch {
    return { deleted: 0 };
  }
  for (const fname of files) {
    const day = fname.slice(0, 10);
    const t = Date.parse(`${day}T00:00:00Z`);
    if (!Number.isFinite(t) || t >= cutoffMs) continue;
    try {
      unlinkSync(join(historyDir, fname));
      deleted++;
    } catch (e) {
      if (log) log.warn(`history: prune failed for ${fname}: ${e.message}`);
    }
  }
  return { deleted };
}
