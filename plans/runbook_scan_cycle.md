# Runbook: Research Scan Cycle

**Owner:** Research Agent
**Ops Guardian:** Studio Operations Agent
**Cadence:** Every 2 hours (automated heartbeat)
**Last Updated:** 2026-03-24

---

## Purpose

Ensure Polymarket markets are scanned on a regular cycle to surface mispriced signals. This runbook defines how the cycle is triggered, what outputs are expected, and how to handle failures.

---

## Trigger

The Research Agent runs on a scheduled heartbeat every 2 hours. Each run should:

1. Fetch live Polymarket market data.
2. Save raw market snapshot to `data/markets_<timestamp>.json` and `data/scans/<date>-<hour>.json`.
3. Apply edge-detection logic (calibrated estimate vs. market price, gap threshold).
4. Output either:
   - **Signal candidate** → append to `data/pending_signals.json`
   - **No-signal report** → log reason in scan output

---

## Expected Outputs

| File | Description | Required |
|------|-------------|----------|
| `data/markets_<YYYYMMDDTHHMMSSZ>.json` | Raw market snapshot | Yes |
| `data/scans/<YYYY-MM-DD>-<HH>.json` | Processed scan output | Yes |
| `data/pending_signals.json` | New signal candidates (if any) | If signal found |

### Scan output schema (`data/scans/<date>-<hour>.json`)

```json
{
  "scanned_at": "<ISO8601>",
  "markets_checked": <int>,
  "signals_found": <int>,
  "no_signal_reason": "<string or null>",
  "candidates": []
}
```

---

## Compliance Check (Studio Ops monitors every heartbeat)

- Last scan must be within **2h15m** of current time.
- If gap > 2h15m → raise alert to CEO (Paperclip issue, high priority).
- If scan output file is missing or malformed → flag to Research Agent.

---

## Failure Scenarios

| Scenario | Action |
|----------|--------|
| Scan missed (>2h15m since last file) | Studio Ops creates Paperclip issue assigned to Research Agent, comments on parent task, alerts CEO |
| API fetch fails (no markets file) | Research Agent must retry in next heartbeat, log failure in scan file |
| No signal found | Expected — log `no_signal_reason` in scan output, no further action required |
| Signal found but `pending_signals.json` not updated | Flag to Research Agent as format deviation |

---

## Scan-to-Signal Handoff Trigger

When a new entry appears in `pending_signals.json`, Studio Ops verifies:

- [ ] All required signal fields present (see Signal Pipeline Runbook)
- [ ] Evidence citations ≥ 1
- [ ] Gap % meets threshold (typically >10%)
- [ ] Confidence level set (HIGH / MEDIUM / LOW)

If compliant → Signal Publisher picks up for CEO approval flow.
If non-compliant → Studio Ops flags to Research Agent, signal stays in pending.

---

## Recovery from Missed Cycle

1. Confirm Research Agent heartbeat is enabled in Paperclip.
2. Manually trigger a scan via Paperclip (create `todo` task for Research Agent: "Manual scan — missed cycle").
3. Verify output appears in `data/scans/`.
4. Log recovery in `plans/ops_log.md`.
