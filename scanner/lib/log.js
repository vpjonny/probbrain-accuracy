// scanner/lib/log.js — minimal logger with skip-with-reason tracking.
// The skip log is the debugging surface when matches don't appear.

export function createLogger({ verbose = false } = {}) {
  const skips = [];
  const counts = new Map();

  const bump = (reason) => counts.set(reason, (counts.get(reason) || 0) + 1);

  return {
    info: (...a) => console.log(...a),
    warn: (...a) => console.warn(...a),
    error: (...a) => console.error(...a),
    skip(reason, context = {}) {
      skips.push({ reason, context });
      bump(reason);
      if (verbose) console.log(`[skip] ${reason} ${JSON.stringify(context)}`);
    },
    skipSummary() {
      return Array.from(counts.entries())
        .sort((a, b) => b[1] - a[1])
        .map(([reason, count]) => ({ reason, count }));
    },
    skipsRaw: () => skips,
    skipCount: () => skips.length,
  };
}
