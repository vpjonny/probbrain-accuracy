import { readFileSync, existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { resolve } from 'node:path';

function parseEnv(text) {
  const out = {};
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq < 0) continue;
    const key = line.slice(0, eq).trim();
    let val = line.slice(eq + 1).trim();
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    const hash = val.indexOf(' #');
    if (hash >= 0) val = val.slice(0, hash).trim();
    out[key] = val;
  }
  return out;
}

const DEFAULT_PATHS = [
  resolve(import.meta.dirname || '.', '..', '.env'),
  resolve(homedir(), 'Documents', 'ProbBrain', '.env'),
];

export function loadEnv(extraPaths = []) {
  const merged = {};
  const tried = [];
  for (const p of [...DEFAULT_PATHS, ...extraPaths]) {
    if (!existsSync(p)) continue;
    tried.push(p);
    Object.assign(merged, parseEnv(readFileSync(p, 'utf8')));
  }
  for (const k of Object.keys(merged)) {
    if (process.env[k] === undefined) process.env[k] = merged[k];
  }
  return { paths: tried, vars: merged };
}

export function require_(...keys) {
  const missing = keys.filter(k => !process.env[k]);
  if (missing.length) throw new Error(`missing required env: ${missing.join(', ')}`);
  return Object.fromEntries(keys.map(k => [k, process.env[k]]));
}
