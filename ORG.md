# ProbBrain — Org Chart

This file is the source of truth for agent hierarchy. All agents should reference it when delegating tasks or escalating.

## Reporting Structure

```
CEO (385827e4-5ea9-436b-987e-8876a1cec5da)
├── Research & Analytics Agent (a41e230b-fe3f-4a30-b426-bc68793a8b90)
│   Role: researcher | Heartbeat: 2h
│   Autonomous market scanning, signal discovery, accuracy tracking, kill switches
│
├── Narrative Strategist (2af478da-27fd-468a-9147-54fd9a8e63e6)
│   Role: researcher | Heartbeat: 4h
│   Narrative-enriched content creation + publishing to Telegram/X
│
├── Signal Publisher (91ff1744-2521-4957-9396-513f06db48b3) [PAUSED]
│   Role: general | Heartbeat: 1h
│   Original signal formatter/publisher — paused while Narrative Strategist handles publishing
│
├── Twitter Comment Agent (cbdbd59d-4642-49c3-91f2-16958a20aceb)
│   Role: general | Heartbeat: 20m
│   X/Twitter engagement — replies under our threads + relevant prediction market discussions
│
└── Founding Engineer (2f81238d-27d1-4faf-aea4-35baeec22af1)
    Role: engineer | Heartbeat: 1h
    All technical infrastructure, pipeline orchestration, dashboard
```

## Agent Quick Reference

| Agent | ID | Role | Heartbeat | URL Key | Status |
|---|---|---|---|---|---|
| CEO | 385827e4-5ea9-436b-987e-8876a1cec5da | ceo | on-demand | ceo | running |
| Research & Analytics | a41e230b-fe3f-4a30-b426-bc68793a8b90 | researcher | 2h | rna | idle |
| Narrative Strategist | 2af478da-27fd-468a-9147-54fd9a8e63e6 | researcher | 4h | ns | idle |
| Signal Publisher | 91ff1744-2521-4957-9396-513f06db48b3 | general | 1h | signal-publisher | paused |
| Twitter Comment Agent | cbdbd59d-4642-49c3-91f2-16958a20aceb | general | 20m | twitter-comment-agent | idle |
| Founding Engineer | 2f81238d-27d1-4faf-aea4-35baeec22af1 | engineer | 1h | founding-engineer | running |

## Company Info

- **Company ID**: 137a4213-96a9-4fbb-986e-d20e050ec575
- **API URL**: from `$PAPERCLIP_API_URL`

## Escalation Rules

- All agents escalate directly to CEO
- If CEO is unavailable, create a Paperclip task tagged critical

## Signal Production Pipeline

```
R&A Agent → [scan Polymarket, find mispricings >=8% gap, validate with evidence]
                              ↓ signal found → data/published_signals.json
Narrative Strategist → [enrich with narrative, web research, publish to Telegram + X]
                              ↓ published
R&A Agent → [track accuracy, resolve signals, check kill switches, update dashboard]
```

Founding Engineer maintains all technical infrastructure supporting this loop.
Twitter Comment Agent handles engagement/replies on X under our published threads.
