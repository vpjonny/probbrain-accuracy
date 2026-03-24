# ProbBrain Analytics Schema

Initialized: 2026-03-24 (Day 2)
Owner: Analytics Agent

---

## Signal Schema (`data/signals.json`)

Each entry in `signals.json` represents one published prediction signal.

```json
{
  "signal_id": "SIG-001",
  "signal_number": 1,
  "market_id": "string — Polymarket market ID",
  "question": "string — full market question text",
  "category": "politics | crypto | sports | entertainment | science | other",
  "direction": "YES_UNDERPRICED | NO_UNDERPRICED",
  "confidence": "HIGH | MEDIUM",
  "market_yes_price": 0.0,
  "our_calibrated_estimate": 0.0,
  "gap_pct": 0.0,
  "evidence": ["string", "..."],
  "reasoning": "string — full written reasoning",
  "volume_usdc": 0,
  "close_date": "YYYY-MM-DD",
  "published_at": "ISO 8601 UTC",
  "approved_by": "string — approver identifier",
  "platforms": ["telegram", "x"],
  "resolved": false,
  "outcome": null,
  "brier_score": null
}
```

### Field Definitions

| Field | Type | Description |
|---|---|---|
| `signal_id` | string | Canonical ID, format `SIG-NNN` (zero-padded to 3 digits) |
| `signal_number` | integer | Sequential counter, 1-indexed |
| `market_id` | string | Polymarket market ID (from API or URL) |
| `question` | string | Verbatim market question |
| `category` | enum | One of: `geopolitics`, `crypto`, `sports`, `entertainment`, `science`, `other` |
| `direction` | enum | `YES_UNDERPRICED` or `NO_UNDERPRICED` — the edge we are claiming |
| `confidence` | enum | `HIGH` (gap ≥15%) or `MEDIUM` (gap 8–14%) |
| `market_yes_price` | float [0,1] | Polymarket YES price at time of signal |
| `our_calibrated_estimate` | float [0,1] | Our probability estimate for YES |
| `gap_pct` | float | Absolute difference × 100. `|market_yes_price - our_calibrated_estimate| × 100` |
| `evidence` | array[string] | Cited sources backing the call. Min 3 required. |
| `reasoning` | string | Full written reasoning paragraph |
| `volume_usdc` | integer | Market liquidity in USDC at time of signal |
| `close_date` | string | Market resolution deadline (YYYY-MM-DD) |
| `published_at` | string | ISO 8601 UTC timestamp of publication |
| `approved_by` | string | Who approved the signal (e.g., `local-board`, agent ID) |
| `platforms` | array[string] | Where published: `telegram`, `x` |
| `resolved` | boolean | `false` until market resolves |
| `outcome` | float or null | `1.0` if YES resolved, `0.0` if NO resolved, `null` if pending |
| `brier_score` | float or null | `(our_calibrated_estimate - outcome)²`, null until resolved |

---

## Resolved Signal Schema (`data/resolved.json`)

Each entry mirrors the signal but adds resolution fields. Append-only — never modify existing records.

```json
{
  "signal_id": "SIG-001",
  "signal_number": 1,
  "market_id": "string",
  "question": "string",
  "category": "string",
  "direction": "YES_UNDERPRICED | NO_UNDERPRICED",
  "confidence": "HIGH | MEDIUM",
  "our_calibrated_estimate": 0.0,
  "resolved_at": "ISO 8601 UTC",
  "resolution": "YES | NO",
  "outcome": 1.0,
  "correct": true,
  "brier_contribution": 0.0,
  "disputed": false
}
```

### Resolution Field Definitions

| Field | Type | Description |
|---|---|---|
| `resolved_at` | string | ISO 8601 UTC — when Polymarket marked the market resolved |
| `resolution` | enum | `YES` or `NO` — Polymarket's final resolution |
| `outcome` | float | `1.0` for YES, `0.0` for NO |
| `correct` | boolean | `true` if our direction was correct (YES_UNDERPRICED + YES, or NO_UNDERPRICED + NO) |
| `brier_contribution` | float | `(our_calibrated_estimate - outcome)²` |
| `disputed` | boolean | `true` if resolution is contested — do NOT score until human clears it |

---

## Scoring Logic

```
correct = (direction == "YES_UNDERPRICED" AND resolution == "YES")
       OR (direction == "NO_UNDERPRICED"  AND resolution == "NO")

brier_contribution = (our_calibrated_estimate - outcome)²

overall_accuracy_pct = (correct_count / resolved_count) * 100

brier_score = mean(brier_contribution for last N resolved signals)
```

---

## Kill Switch Thresholds

| # | Condition | Action |
|---|---|---|
| 1 | Overall accuracy <50% over last 20 resolved | Alert CEO, pause Research Agent |
| 2 | 3 consecutive losses in same category | Alert CEO, pause Research Agent |
| 3 | Volume >150/day Telegram or >40/day X for 3 consecutive days without CEO approval | Alert CEO |
| 4 | Any published signal missing `evidence` field | Alert CEO immediately |
| 5 | Brier score >0.35 over last 20 resolved signals | Alert CEO, pause Research Agent |
| 6 | Any signal published with `approval_required: true` before CEO approval | Alert CEO immediately |

---

## Dashboard Files

| File | Purpose |
|---|---|
| `dashboard/accuracy.json` | Machine-readable live stats, updated within 1 hour of any resolution |
| `dashboard/index.html` | Public accuracy page, reads from `accuracy.json` |

### `dashboard/accuracy.json` Schema

```json
{
  "updated_at": "ISO 8601 UTC",
  "signals_published": 0,
  "signals_resolved": 0,
  "correct": 0,
  "accuracy_pct": null,
  "brier_score": null,
  "current_streak": 0,
  "streak_type": null,
  "by_category": {
    "politics": { "published": 0, "resolved": 0, "correct": 0, "accuracy_pct": null }
  },
  "by_confidence": {
    "HIGH":   { "published": 0, "resolved": 0, "correct": 0, "accuracy_pct": null },
    "MEDIUM": { "published": 0, "resolved": 0, "correct": 0, "accuracy_pct": null }
  },
  "kill_switches_active": [],
  "last_resolved_signal": null
}
```

---

## Hard Rules

1. **Never modify historical data.** `data/resolved.json` is append-only.
2. **Every resolution verified against Polymarket API.** Never assumed from secondary sources.
3. **Disputed resolutions:** set `disputed: true`, do not score, flag for human review.
4. **No rounding up.** If accuracy is 47.3%, report 47.3%.
5. **Evidence required.** Every signal must have at least 3 evidence citations before publication.
