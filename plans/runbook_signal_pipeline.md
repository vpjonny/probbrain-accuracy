# Runbook: Signal Pipeline

**Owner:** Signal Publisher Agent
**Ops Guardian:** Studio Operations Agent
**Trigger:** New entry in `data/pending_signals.json`
**Last Updated:** 2026-03-24

---

## Purpose

Define the end-to-end flow from a Research Agent signal candidate to a published, logged signal. Ensures format compliance, human approval (for first 10 signals), and correct logging.

---

## Pipeline Stages

```
Research Agent
  → data/pending_signals.json
      → [Studio Ops format check]
          → CEO approval (signals 1–10)
              → Signal Publisher
                  → Telegram + X publish
                      → data/published_signals.json
                          → data/signals.json (Analytics)
```

---

## Stage 1 — Signal Candidate (Research Agent)

Research Agent appends to `data/pending_signals.json`. Required fields:

| Field | Type | Description |
|-------|------|-------------|
| `signal_number` | int | Sequential, e.g. 1, 2, 3 |
| `market_id` | string | Polymarket market ID |
| `question` | string | Market question verbatim |
| `direction` | string | `YES_UNDERPRICED` or `NO_UNDERPRICED` |
| `confidence` | string | `HIGH`, `MEDIUM`, or `LOW` |
| `our_calibrated_estimate` | float | 0.0–1.0 |
| `gap_pct` | float | Absolute gap in percentage points |
| `evidence` | array | Min 1 citation string |
| `close_date` | string | ISO date `YYYY-MM-DD` |

Studio Ops validates this before the signal proceeds.

---

## Stage 2 — Studio Ops Format Check

Before any signal is submitted for approval, Studio Ops verifies:

- [ ] All required fields present and correctly typed
- [ ] `evidence` array is non-empty
- [ ] `direction` is valid enum value
- [ ] `confidence` is valid enum value
- [ ] `signal_number` is sequential (no gaps, no duplicates)

**If compliant:** Signal proceeds to CEO approval.
**If non-compliant:** Studio Ops flags to Research Agent via Paperclip comment. Signal stays in `pending_signals.json`.

---

## Stage 3 — CEO Approval (Signals 1–10)

**Rule:** The first 10 signals **must** have human approval before publishing. The `approval_required` flag must be honored.

1. Signal Publisher creates a Paperclip approval request with the signal JSON.
2. CEO reviews and approves/rejects via Paperclip.
3. On approval: `approved_by` and `approval_comment_id` set in record.
4. On rejection: signal removed from pending, reason logged.

**Kill switch trigger:** If any signal is published without approval before signal #11 → immediate pause of Signal Publisher, high-priority CEO alert.

---

## Stage 4 — Publication (Signal Publisher)

Signal Publisher posts to platforms specified in `platforms` field.

### Publication Limits (enforced strictly)
- Max **5 signals/day** on Telegram
- Max **3 signals/day** on X
- Min **30 minutes** between any two signals on any platform

Before publishing, Signal Publisher checks:
1. Today's published count per platform (from `data/published_signals.json`)
2. Timestamp of most recent publication
3. If either limit is breached → hold signal, comment on task, alert Studio Ops

### After Publishing
Signal Publisher appends to `data/published_signals.json`:

| Field | Added by Publisher |
|-------|--------------------|
| `published_at` | Timestamp of publication |
| `platforms` | Actual platforms published to |
| `telegram_link` | Dub short link |
| `x_link` | Dub short link |
| `market_yes_price` | Market price at time of publish |
| `volume_usdc` | Market volume at time of publish |
| `paperclip_issue` | Issuing Paperclip task ID |

---

## Stage 5 — Analytics Sync (Analytics Agent)

After each publication, Analytics Agent syncs to `data/signals.json` (canonical kill-switch record):

Required fields in `signals.json`:

| Field | Description |
|-------|-------------|
| `signal_number` | Sequential |
| `market_id` | Polymarket ID |
| `question` | Market question |
| `direction` | Direction called |
| `confidence` | Confidence level |
| `our_calibrated_estimate` | Our probability estimate |
| `gap_pct` | Edge size |
| `published_at` | Publication timestamp |
| `approved_by` | Approval source |
| `platforms` | Where published |
| `close_date` | Market close date |
| `evidence` | Evidence citations |
| `resolved` | Boolean |
| `outcome` | `WIN`, `LOSS`, or `null` |
| `brier_score` | Float or `null` |

Studio Ops checks `signals.json` every heartbeat. If a published signal is missing from this file → flag to Analytics Agent.

---

## Handoff Verification Table

| Handoff | Check | Owner |
|---------|-------|-------|
| Research → pending_signals | Format valid, evidence present | Studio Ops |
| pending_signals → approval | `approval_required` flag honored | Studio Ops |
| approval → publish | Approval confirmed before publish | Signal Publisher |
| publish → published_signals | Entry appended within 1 heartbeat | Studio Ops |
| published_signals → signals.json | Synced within 1 heartbeat | Studio Ops |

---

## Kill Switch Triggers

| Condition | Threshold | Action |
|-----------|-----------|--------|
| Accuracy | <50% over last 20 resolved | Create CEO issue (critical) |
| Streak loss | 3 consecutive in same category | Create CEO issue (critical) |
| Daily X volume | >15/day for 3 consecutive days | Create CEO issue (critical) |
| No evidence | Any signal without evidence | Create CEO issue (critical) |
| Brier score | >0.35 over last 20 signals | Create CEO issue (critical) |
| Approval bypass | Any of first 10 without approval | Create CEO issue (critical) |
