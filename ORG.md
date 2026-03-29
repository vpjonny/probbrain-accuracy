# ProbBrain — Org Chart

This file is the source of truth for agent hierarchy. All agents should reference it when delegating tasks or escalating.

## Reporting Structure

```
CEO (2d160bf5-a806-4be2-b03e-1bb95e1e0b15)
├── Analytics Agent (ba0aebe6-929c-411f-9962-e9e8d5f0214f)
│   Role: researcher | Heartbeat: 1h
│   Accuracy tracking, kill switches, dashboard, market scanning
│
├── Signal Publisher (1664c38b-a21d-4c73-9507-0467c9d88c1e)
│   Role: general | Heartbeat: 1h
│   Formats + posts signals to Telegram/X, handles content review and engagement
│
├── Twitter Comment Agent (3d7548a5-5d31-492f-a1b7-ef1931255bbf)
│   Role: general | Heartbeat: 20m
│   X/Twitter engagement — replies under our threads + relevant prediction market discussions
│
└── Founding Engineer (3859025f-c061-4c45-9564-79e399d563c6)
    Role: engineer | Heartbeat: 1h
    All technical infrastructure, pipeline orchestration
```

## Agent Quick Reference

| Agent | ID | Role | Heartbeat | URL Key |
|---|---|---|---|---|
| CEO | 2d160bf5-a806-4be2-b03e-1bb95e1e0b15 | ceo | 1h | ceo |
| Analytics Agent | ba0aebe6-929c-411f-9962-e9e8d5f0214f | researcher | 1h | analytics-agent |
| Signal Publisher | 1664c38b-a21d-4c73-9507-0467c9d88c1e | general | 1h | signal-publisher |
| Twitter Comment Agent | 3d7548a5-5d31-492f-a1b7-ef1931255bbf | general | 20m | twitter-comment-agent |
| Founding Engineer | 3859025f-c061-4c45-9564-79e399d563c6 | engineer | 1h | founding-engineer |

## Company Info

- **Company ID**: 34e5323e-41df-4405-b316-6ea05dc61956
- **Company Goal ID (ProbBrain)**: e2d373a8-364e-4a22-8d34-086ced3a0caf
- **API URL**: from `$PAPERCLIP_API_URL`

## Escalation Rules

- All agents escalate directly to CEO
- If CEO is unavailable, create a Paperclip task tagged critical

## Signal Production Pipeline

```
Analytics Agent → [scan markets + track accuracy]
                              ↓ signal found
Signal Publisher → [format, review, post to Telegram + X]
                              ↓ published
Analytics Agent → [update dashboard, check kill switches]
```

Founding Engineer maintains all technical infrastructure supporting this loop.
