# Runbook: Content Schedule

**Owner:** Content Agent
**Ops Guardian:** Studio Operations Agent
**Cadence:** Weekly recurring + event-triggered
**Last Updated:** 2026-03-24

---

## Purpose

Define the weekly content cadence for ProbBrain across X and Telegram. Ensures consistent publishing rhythm regardless of signal activity.

---

## Weekly Calendar

| Day | Platform | Content Type | Owner | Required |
|-----|----------|--------------|-------|----------|
| Monday | X | Edge Thread — methodology/education | Content Agent | Yes |
| Tuesday | Telegram | Signal (if available) or silence | Signal Publisher | If approved |
| Wednesday | X | Edge Thread — market analysis or forecasting | Content Agent | Yes |
| Wednesday | Telegram | Signal (if available) | Signal Publisher | If approved |
| Thursday | X/Telegram | EOD accountability post (if no signal) | Content Agent | If no signal |
| Friday | X | EOD accountability post or signal recap | Content Agent | Yes |
| Sunday | X + Telegram | Weekly digest | Content Agent + Analytics Agent | Yes |

---

## Content Types

### Edge Thread (Mon/Wed — X)
**Purpose:** Educational content. Builds credibility and follower trust.
**Format:** 4–7 tweet thread
**Approved themes:**
- How we think about base rates
- What Polymarket gets right — and where it fails
- How to read a ProbBrain signal
- Calibration vs. prediction: why they're different
- Case study of a resolved market (when available)

**Delivery:** Content Agent drafts → posts directly (no approval required for educational content)

### Signal Post (Telegram + X, when signal available)
**Format:** Telegram: structured text with market link. X: 3–5 tweet thread.
**Approval:** Required for signals 1–10. See Signal Pipeline Runbook.
**Limits:** No daily cap on Telegram; max 15/day on X; 30-min gap enforced.

### EOD Accountability Post
**Trigger:** Day ends with no published signal and no educational thread already posted.
**Format:** Single X post, ~280 chars.
**Template:** "No new signals today. Here's what we're watching: [1–2 markets]. Signal published when edge is clear."
**Purpose:** Maintains posting rhythm, builds trust via transparency.

### Weekly Digest (Sunday)
**Trigger:** Every Sunday.
**Inputs from Analytics Agent:** `data/weekly_report.json` (delivered by Saturday EOD)
**Content:**
- Signals published this week (W/L/pending)
- Accuracy % on resolved signals
- Brier score (if any resolved)
- What we're watching for next week

**Delivery:** Content Agent publishes to X + Telegram.
**Prerequisite:** Analytics Agent must deliver `data/weekly_report.json` by Saturday EOD.

---

## Onboarding Drip (Retention Agent Coordination)

When a new subscriber joins Telegram, Retention Agent triggers the drip sequence:

| Day | Message |
|-----|---------|
| Day 0 | Welcome message + what ProbBrain is |
| Day 3 | "How to read a signal" educational message |
| Day 7 | "How we scored last week" (links to Sunday digest) |

**Trigger alignment:** Retention Agent listens for new subscriber events. Studio Ops verifies drip is activated after each subscriber growth report.

---

## Handoff: Analytics → Content (Weekly Report)

| Step | Owner | Deadline |
|------|-------|----------|
| Generate `data/weekly_report.json` | Analytics Agent | Saturday EOD |
| Confirm delivery to Content Agent | Studio Ops | Saturday EOD |
| Publish Sunday digest | Content Agent | Sunday, any time |

`data/weekly_report.json` required fields:

```json
{
  "week_ending": "YYYY-MM-DD",
  "signals_published": <int>,
  "signals_resolved": <int>,
  "wins": <int>,
  "losses": <int>,
  "accuracy_pct": <float or null>,
  "brier_score_avg": <float or null>,
  "pending_signals": [],
  "markets_watching": []
}
```

If `weekly_report.json` is missing by Saturday EOD → Studio Ops flags to Analytics Agent (high priority).

---

## Compliance Monitoring (Studio Ops)

Every heartbeat, Studio Ops checks:

- [ ] No more than 5 Telegram signals published today
- [ ] No more than 3 X signals published today
- [ ] 30-minute gap maintained between publications
- [ ] EOD post published if no other content that day (verify by 21:00 UTC)
- [ ] Sunday digest published by 23:59 UTC Sunday

**Deviation response:** Create Paperclip task assigned to Content Agent with specific miss flagged.

---

## Content Agent Replacement Protocol

If Content Agent is unavailable:

1. Studio Ops creates Paperclip task for CEO: "Manual content required — Content Agent unavailable"
2. EOD accountability post template can be posted manually by board.
3. Weekly digest is highest priority — must not be skipped.
4. Edge Threads can be deferred up to 1 week without brand impact.
