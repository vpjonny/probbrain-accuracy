# ProbBrain Arbitrage Scanner

Finds prediction-market arbitrage and pricing inconsistencies across **Polymarket** and **Kalshi**. Runs locally on a schedule, writes static `opportunities.json` to the repo root, GitHub Pages / Vercel serves it, the `arbitrage.html` frontend renders.

The scanner's defining property is **honesty**. Every card carries a `weakest_link_summary`. Tier 1 (true risk-free arbs) is rare — that's correct.

## Quickstart

```bash
# from the repo root (probbrain-accuracy)
node scanner/scan.js              # full scan + write opportunities.json + git push
node scanner/scan.js --dry-run    # no file write, no git, prints summary
node scanner/scan.js --no-push    # write but skip git commit/push
node scanner/scan.js --pass=1,2   # subset of detection passes
node scanner/scan.js --verbose    # full skip-reason logging
```

Tests:
```bash
node scanner/test-pass1.js                # 18 assertions — Pass 1 (Poly sum violations)
node scanner/test-pass2-pass3.js          # 29 assertions — within-platform monotonicity
node scanner/test-pass4.js                # 26 assertions — curated cross-platform pairs
node scanner/test-pass5.js                # 17 assertions — cross-platform matching
node scanner/test-history-persistence.js  # 36 assertions — history + persistence rollup
node scanner/test-track-record.js         # 50 assertions — track-record aggregate
```

Audit (debug normalizer output for a given underlying):
```bash
node scanner/audit-canonical.js BTC
```

## Architecture

```
scan.js → fetches Poly + Kalshi APIs → runs detection passes →
writes opportunities.json → git commit + push → Pages serves the static site →
arbitrage.html fetches ./opportunities.json → renders
```

No backend hosting. No CORS issues (server-side `fetch` in Node). No live polling from the browser. Updates as often as the cron runs.

### Detection passes

| Pass | Type | What it finds |
|------|------|---------------|
| 1 | `poly_sum_violation` | Polymarket negRisk events whose YES prices sum to anything other than 1.0 (within 1.5pp). Buy-all-YES if sum < 1, buy-all-NO if sum > 1. |
| 2 | `poly_monotonicity` | Within a Polymarket event with multiple strikes, "above" prices should drop as strike rises (and vice versa for "below"). Adjacent-strike pairs only. |
| 3 | `kalshi_monotonicity` | Same drill on Kalshi using `yes_bid_dollars` / `yes_ask_dollars` mid. |
| 4 | `cross_platform` (curated) | Hand-validated (Poly bucket, Kalshi bucket) entries from `dicts/curated-pairs.js`. Bridges the calendar mismatch Pass 5 misses (Poly uses round strikes + endDate-1, Kalshi uses $X,XXX.99 strikes + month-after expiry). Tagged with `curated_pair` flag and `curated_pair_id` field. Runs before Pass 5; emitted pairs are deduped from Pass 5. |
| 5 | `cross_platform` | Same canonical key (underlying, direction, strike, date, type) on both venues priced differently. Buy YES on the cheaper venue, NO on the more expensive. |

Passes 6, 7 are deferred to v1.5+.

#### Adding a curated pair (Pass 4)

Edit `scanner/dicts/curated-pairs.js`. Each entry asserts: "this Polymarket bucket and this Kalshi bucket ask the same question." Read both venues' market pages, confirm the resolution rules describe the same observable event, then write the entry. Schema:

```js
{
  id: 'btc-year-end-2026',                              // stable, used in opportunity ID
  underlying: 'BTC',                                    // sanity check
  polyFilter: (event, market) => /* predicate */,       // returns true for Poly markets in the bucket
  kalshiFilter: (market) => /* predicate */,            // returns true for Kalshi markets in the bucket
  match: {
    strikeTolerancePct: 0.5,                            // relative tolerance ($150k vs $149,999.99 → 0.0007%)
    requireSameDirection: true,                         // almost always true
  },
  sameResolutionWindow: true,                           // operator-asserted: settlement windows resolve identically
  notes: 'why these two buckets are equivalent — date verified',
}
```

When `sameResolutionWindow: true`, the offset filter and `resolution_mismatch` flag are skipped — the curator is taking responsibility for the match. When `false`, behaves like Pass 5's strike-only fallback (capped at Tier 2 with `resolution_mismatch`).

### Persistence (spread history)

Every scan appends a compact sample (`tier`, `edge_gross_pct`, `edge_net_estimate_pct`, `max_size`, `flags`) for each emitted opportunity to a daily JSONL file under `history/YYYY-MM-DD.jsonl`. `history/` is **gitignored** — it's the scanner's own per-machine memory, not a public artifact.

On each run, the scanner loads the last 14 days of history, groups by opportunity ID, and embeds a rolled-up summary on each opportunity:

```json
"persistence": {
  "first_seen_at": "2026-04-30T12:15:00Z",
  "scans_seen": 24,
  "hours_persisted": 6.0,
  "gross_pct_history": [5.0, 4.8, 5.2, 5.0, 5.0],
  "trend": "stable"
}
```

`trend` comes from a least-squares slope over the last 10 samples of `edge_gross_pct`:

| Slope | Classification |
|-------|---------------|
| ≥ +0.3pp/scan | `widening` |
| ≤ -0.3pp/scan | `tightening` |
| `\|slope\| < 0.3` | `stable` |
| <3 samples | `new` |

The frontend renders this as a pill on each card (e.g. `2.3h ↘ tightening`). Persistence ticks every scan but is stripped from the no-op detector — the scanner still skips git pushes when only persistence + timestamps changed.

History retention: 30 days (older daily files are auto-pruned each scan).

### Track record (P&L proxy)

Each scan also rolls history into a top-level `track_record` field on `opportunities.json`:

```json
"track_record": {
  "lookback_days": 14,
  "total_observed": 141,
  "active": 100,        // still in latest scan
  "left_feed": 41,      // gone from latest scan
  "among_active": { "closed_substantially": 0, "tightened": 5, "stable": 88, "widened": 7 },
  "among_active_pct": { "closed_substantially": 0.0, "tightened": 5.0, "stable": 88.0, "widened": 7.0 },
  "median_lifetime_hours": 0.24,
  "by_tier": { "1": {...}, "2": {...}, "3": {...} }
}
```

For each opportunity in the lookback window: if it's still in the latest scan, classify the spread evolution from `first_gross` → `last_gross`:

| Ratio (last/first) | State |
|--------------------|-------|
| < 0.5 | `closed_substantially` |
| 0.5 – 0.8 | `tightened` |
| 0.8 – 1.2 | `stable` |
| > 1.2 | `widened` |

If the opp is *not* in the latest scan, it's classified as `left_feed` — could mean resolved, leg delisted, or spread fell below the 2pp emit threshold. We do **not** call it "closed" because that would conflate observation with reality. Realized P&L (cross-referencing settled markets) is a separate v1.5 layer.

The frontend renders this above the tier sections as a horizontal distribution bar.

### Tier assignment

Each opportunity gets `tier ∈ {1, 2, 3}`. Filter pipeline:

1. **Recency** — any leg older than the acceptable threshold for its `resolution_type` → Tier 3 with `stale_price`.
2. **Settlement-time offset** (cross-platform only) — over tolerance → downgrade with `offset_warning`. Over 4× tolerance → skip entirely.
3. **Depth** — at the user's max position (default $1,000); cap executable size, downgrade if cap is severe.
4. **Fee/edge** — `gross_edge ≥ 8%` AND survives all guards → Tier 1; `4% < gross ≤ 8%` → Tier 2 with `fee_tight`; `< 4%` → Tier 3.

Final tier = the worst tier produced by any filter (each filter can only worsen).

## Adding a new underlying

Edit `scanner/dicts/underlyings.js`. **No fuzzy matching** — adding a new entry is intentionally a manual code change. Fuzzy matching at this layer would silently produce wrong matches (ETH ↔ ETHE, BTC ↔ BCH) and the scanner would output fake arbs.

Each entry needs:

```js
ASSET_KEY: {
  aliases:        ['name1', 'symbol'],         // case-insensitive substrings, word-boundary aware
  category_hints: ['polymarket-category-1'],   // event.category / event.tags labels
  kalshi_series:  ['KX_PREFIX_1'],             // Kalshi series_ticker prefixes
}
```

Then add hand-crafted tests in `test-pass2-pass3.js` covering the new underlying.

## Output schema (`opportunities.json`)

`schema_version` is checked by the frontend; mismatch shows a clear error and stops rendering. Bump it on any breaking shape change.

```json
{
  "schema_version": 1,
  "generated_at": "2026-04-30T12:30:00Z",
  "scan_duration_ms": 8541,
  "errors": [{ "source": "kalshi", "msg": "rate limited" }],
  "stats": {
    "poly_markets_scanned": 76310,
    "kalshi_markets_scanned": 1350,
    "candidates_pre_filter": 520,
    "tier1_count": 1,
    "tier2_count": 50,
    "tier3_count": 50,
    "pre_cap_tier1": 1,
    "pre_cap_tier2": 75,
    "pre_cap_tier3": 462,
    "per_tier_cap": 50
  },
  "opportunities": [
    {
      "id": "stable-deterministic-hash",
      "tier": 1,
      "type": "cross_platform",
      "summary": "BTC ≥ $100k by May 1 — 4.2% gap",
      "underlying": "BTC",
      "resolution_date": "2026-05-01",
      "resolution_type": "daily",
      "legs": [
        { "platform": "polymarket", "market_id": "...", "market_url": "...",
          "side": "YES", "price": 0.62, "depth_usd_at_price": 1450,
          "last_trade_at": "2026-04-30T12:18:11Z", "volume_24h_usd": 38200 }
      ],
      "edge_gross_pct": 4.2,
      "edge_net_estimate_pct": -3.1,
      "max_executable_size_per_leg_usd": 980,
      "edge_net_per_dollar": -0.031,
      "weakest_link_summary": "Kalshi leg depth limits fill to $980. Net edge negative after fees at any size.",
      "confidence_flags": ["fee_tight", "depth_limited"]
    }
  ]
}
```

The frontend computes `executable_dollar_profit_at_user_size = min(user_max_position, max_executable_size_per_leg_usd) × edge_net_per_dollar` live as the user drags the bankroll slider.

`id` is a stable hash — the same opportunity keeps its id across scans so the UI can dedupe.

## Output cap

Each tier is capped at **50 opportunities** (sorted by `edge_net_estimate_pct` desc) before write. Pre-cap counts are preserved in `stats.pre_cap_tier{1,2,3}` so you can see how many were filtered. The cap keeps the JSON small (~300 KB on a typical scan, gzipped to ~50 KB on Vercel CDN) and keeps the dashboard signal-dense.

## Cron / scheduling

Recommended: every 15 minutes, direct node invocation.

```cron
*/15 * * * * cd /path/to/probbrain-accuracy && /usr/bin/node scanner/scan.js >> scanner/cron.log 2>&1
```

The scanner already:
- skips `git push` when the diff is only `generated_at` and `scan_duration_ms` (no real opportunity changes),
- preserves the previous `opportunities.json` on a full fetch failure (page never goes blank),
- exits non-zero if both API fetches fail so a watchdog can notice.

There's a helper that installs/refreshes this crontab line idempotently:

```bash
bash scanner/install-cron.sh
```

It detects the repo root from its own location, so it works regardless of where the repo lives.

### systemd alternative (Arch / cron-less systems)

If `crontab` isn't installed (Arch's default — uses systemd timers natively), use the equivalent installer that creates a user-level systemd timer:

```bash
bash scanner/install-systemd.sh           # install + enable + start
bash scanner/install-systemd.sh --status  # show next/last run + recent logs
bash scanner/install-systemd.sh --remove  # disable + remove
```

Same 15-minute cadence, output goes to the journal (`journalctl --user -fu probbrain-arb-scanner.service`). For the timer to keep firing after logout, run `sudo loginctl enable-linger $USER` once.

### Spec-style alternative (Claude-orchestrated)

The original build spec proposed running scans through `claude -p` to get LLM-summarized commit messages. Direct `node scan.js` is cheaper, deterministic, and equivalent — the script already produces a stat-summarized commit message (`scan: <ts>, T1=N T2=N T3=N`).

```cron
*/15 * * * * cd /path/to/probbrain-accuracy && claude -p "run node scanner/scan.js, summarize results, push if any tier-1 or tier-2 changes" >> scanner/cron.log 2>&1
```

Use this only if you want the LLM to apply judgment on whether to push (e.g., suppressing tier-3-only churn).

## Failure handling

- **Either API fails entirely**: previous `opportunities.json` is preserved with `errors[]` populated, all legs flagged `stale_price`, all opportunities forced to Tier 3, scanner exits non-zero. Page never goes blank because of a transient outage.
- **Single market fails to normalize**: skip + log the reason, continue. One bad market never sinks the scan.
- **API retries**: 3 attempts with exponential backoff (1s, 3s, 9s) per request. After that the error surfaces.
- **Schema-version mismatch**: the frontend renders a red banner ("Scanner / frontend out of sync. opportunities.json schema_version=N, frontend expects M.") instead of a broken layout.

## Troubleshooting

**Scanner runs but Pass 5 finds 0 cross-platform matches.** Expected, much of the time. Polymarket and Kalshi schedule their BTC ladders on different calendars — they offer the same strikes but rarely on the same exact date. Run `node scanner/audit-canonical.js BTC` to see which canonical keys each venue is producing; near-misses (same strike, different date) tell you what's almost matching. Real cross-platform arbs surface only when both venues happen to list the same question. **For known equivalent buckets that don't match by canonical key, add a Pass 4 curated entry** (see "Adding a curated pair" above).

**Tons of `pass2_underlying_not_in_dict` skips in `--verbose`.** Working as intended. The underlying dict is intentionally narrow — it covers BTC/ETH/SOL/FED_RATE/CPI/NFP. The scanner skips everything else loudly with that reason. To support more underlyings, see "Adding a new underlying" above.

**Lots of `pass2_pair_low_volume` skips.** Most of Polymarket's long-tail negRisk events have one or both legs with under $100 of 24h volume. We skip those because reporting them as opportunities would bury real signal under thousands of zombies. Adjust the floor in `passes/pass2-poly-monotonicity.js` if you want them.

**Scan finishes in seconds but commits show the same opportunities each time.** That's the no-op detector working correctly — the scanner writes the file but skips `git push` when the only diff is timestamps. Look for `scanner: no opportunity changes since last scan` in the log.

**Frontend shows "Scanner / frontend out of sync."** The `schema_version` in `opportunities.json` doesn't match `EXPECTED_SCHEMA_VERSION` in `arbitrage.html`. Either bump one to match, or you have a stale cache (`Cache-Control: max-age=300, stale-while-revalidate=600` on the JSON; refresh after 10 min for full freshness).

## Files

```
scanner/
  scan.js                              # entrypoint
  package.json
  README.md                            # this file
  install-cron.sh                      # idempotent crontab installer
  install-systemd.sh                   # idempotent systemd user-timer installer (Arch)
  test-pass1.js                        # 18 unit tests
  test-pass2-pass3.js                  # 29 unit tests
  test-pass4.js                        # 26 unit tests
  test-pass5.js                        # 17 unit tests
  test-history-persistence.js          # 36 unit tests
  test-track-record.js                 # 50 unit tests
  audit-canonical.js                   # debug tool: dump canonical keys per asset
  dicts/
    underlyings.js                     # hardcoded BTC/ETH/SOL/FED_RATE/CPI/NFP
    curated-pairs.js                   # hand-validated cross-platform buckets (Pass 4)
  lib/
    fetch.js                           # built-in fetch + retries + paginators
    log.js                             # skip-with-reason tracker
    schema.js                          # SCHEMA_VERSION + validators
    canonical.js                       # canonical key serialization + grouping
    tiering.js                         # fee model + recency + tier assignment
    history.js                         # local JSONL: append/load/prune per-scan samples
    persistence.js                     # rollup → first_seen, hours_persisted, trend
    track-record.js                    # aggregate → spread evolution + lifetime stats
  normalize/
    polymarket.js                      # field hierarchy: underlying → ... → resolution_type
    kalshi.js                          # series_ticker prefix + subtitle parser
  passes/
    pass1-poly-sum.js                  # negRisk sum violations
    pass2-poly-monotonicity.js         # within-Polymarket strike monotonicity
    pass3-kalshi-monotonicity.js       # within-Kalshi strike monotonicity
    pass4-curated-cross.js             # operator-curated cross-platform pairs
    pass5-cross-platform.js            # canonical-key matching across venues
```

## Out of scope (deliberate)

- Pass 6 bracket arbs across mismatched strike granularities
- Pass 7 conditional consistency within Polymarket
- Auto-execution of any kind
- P&L / track-record of detected arbs
- LLM-based market matching (fuzzy = fake arbs)
- Watchlist with spread history charts
- Wallet integration / position tracking
- Notifications (Discord, Telegram, email)
- Multi-user accounts

These are deliberate omissions for v1. Adding any of them risks compromising the honest-by-default property.
