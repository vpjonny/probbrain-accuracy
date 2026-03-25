# ProbBrain — Org Chart

This file is the source of truth for agent hierarchy. All agents should reference it when delegating tasks or escalating.

## Reporting Structure

```
CEO (2d160bf5-a806-4be2-b03e-1bb95e1e0b15)
├── Research Agent (c3411b1b-341e-4d07-92a1-c752e3bbfb53)
│   Role: researcher | Heartbeat: 2h | Scans Polymarket for mispricings
│
├── Analytics Agent (ba0aebe6-929c-411f-9962-e9e8d5f0214f)
│   Role: researcher | Heartbeat: 1h | Accuracy tracking, kill switches, dashboard
│
├── Signal Publisher (1664c38b-a21d-4c73-9507-0467c9d88c1e)
│   Role: general | Heartbeat: 1h | Formats + posts signals to Telegram/X
│   ├── Content Creator (23abe5e7-1785-4533-99e4-b862fd0df38c)
│   │   Role: general | Heartbeat: 1h | Reviews/refines signal post drafts before publish
│   └── Twitter Engager (68326df8-fbfa-48db-886e-cf6f6d5fb5de)
│       Role: general | Heartbeat: 1h | Reviews X threads, handles engagement post-publish
│
├── Content Agent (f59d6cba-a9f8-410b-8b9a-296714d9683a)
│   Role: cmo | Heartbeat: 1h | Edge threads, EOD posts, Sunday digest
│
├── Pipeline Overseer (1740dce2-ab02-4a30-b876-99b64658d998)
│   Role: pm | Heartbeat: 30min | Orchestrates Research→Analytics→Signal→Content loop
│
├── Founding Engineer (3859025f-c061-4c45-9564-79e399d563c6)
│   Role: engineer | Heartbeat: 1h | All technical infrastructure
│
├── Strategy Optimizer (043685c0-e4e0-472e-812e-9bc8b85a4692)
│   Role: researcher | Heartbeat: weekly | Strategy review + proposals
│
└── Finance Overseer (61cb524a-b3a8-4ebc-8c0d-5caa711e1a53)
    Role: cfo | Heartbeat: weekly | P&L, costs, revenue tracking
```

## Agent Quick Reference

| Agent | ID | Role | Heartbeat | URL Key |
|---|---|---|---|---|
| CEO | 2d160bf5-a806-4be2-b03e-1bb95e1e0b15 | ceo | 1h | ceo |
| Research Agent | c3411b1b-341e-4d07-92a1-c752e3bbfb53 | researcher | 2h | research-agent |
| Analytics Agent | ba0aebe6-929c-411f-9962-e9e8d5f0214f | researcher | 1h | analytics-agent |
| Signal Publisher | 1664c38b-a21d-4c73-9507-0467c9d88c1e | general | 1h | signal-publisher |
| Content Agent | f59d6cba-a9f8-410b-8b9a-296714d9683a | cmo | 1h | content-agent |
| Content Creator | 23abe5e7-1785-4533-99e4-b862fd0df38c | general | 1h | content-creator |
| Twitter Engager | 68326df8-fbfa-48db-886e-cf6f6d5fb5de | general | 1h | twitter-engager |
| Pipeline Overseer | 1740dce2-ab02-4a30-b876-99b64658d998 | pm | 30min | pipeline-overseer |
| Founding Engineer | 3859025f-c061-4c45-9564-79e399d563c6 | engineer | 1h | founding-engineer |
| Strategy Optimizer | 043685c0-e4e0-472e-812e-9bc8b85a4692 | researcher | weekly | strategy-optimizer |
| Finance Overseer | 61cb524a-b3a8-4ebc-8c0d-5caa711e1a53 | cfo | weekly | finance-overseer |

## Company Info

- **Company ID**: 34e5323e-41df-4405-b316-6ea05dc61956
- **Company Goal ID (ProbBrain)**: e2d373a8-364e-4a22-8d34-086ced3a0caf
- **API URL**: from `$PAPERCLIP_API_URL`

## Escalation Rules

- Any agent stuck/blocked → escalate to direct manager (see reportsTo above)
- Pipeline agents (Research, Analytics, Signal Publisher) → escalate to Pipeline Overseer first
- Pipeline Overseer, Founding Engineer, Strategy Optimizer, Finance Overseer → escalate to CEO
- Content Creator, Twitter Engager → escalate to Signal Publisher

## Pipeline Overseer Scope

The Pipeline Overseer (30-min heartbeat) owns the signal production loop:

```
Research Agent → [scan] → signals found?
                              ↓ YES
                         Signal Publisher → Content Creator → (draft review)
                                         → Twitter Engager → (X thread review)
                                         → Signal Publisher → POST (Telegram + X)
                              ↓ NO
                         (wait for next cycle)
Analytics Agent → [update accuracy metrics] (every cycle, parallel)
```
