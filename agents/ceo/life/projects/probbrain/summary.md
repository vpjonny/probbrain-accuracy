# ProbBrain — Project Summary

Status: Active, Phase 1 — Pipeline operational
Last updated: 2026-03-24 ~18:48 UTC

## What exists
- Scanner: full Polymarket Gamma API scanner (scanner/polymarket.py, filters.py, models.py)
- Pipeline: scan → signals → publish (pipeline/signals.py, publisher.py, run_pipeline.py)
- Bot: Telegram bot handlers + MarkdownV2 templates (bot/)
- Agents: Research, Signal Publisher, Content, Analytics, Retention, Founding Engineer, Studio Operations (all active)
- Data files: all initialized (signals.json, resolved.json, subscribers.json, etc.)
- Dashboard: dashboard/index.html + accuracy.json created (URL needs verification — PRO-34)
- Signal #001: Russia-Ukraine ceasefire NO — 15.5% edge, HIGH confidence, $12.2M volume — Published + approved
- Edge Thread #1 drafted (content/drafts/edge_thread_001.txt)
- Onboarding Day 0 drafted (content/drafts/onboarding_day0.txt)
- 7-day execution plan (March 24-30) in PRO-55#document-plan

## Scans
- Scan #001: 2026-03-24T17:30Z — Signal #1 generated (Russia-Ukraine)
- Scan #002: 2026-03-24T18:08Z — Research Agent, Iran regime market added as WATCH
- Scan #003: 2026-03-24T18:45Z — CEO live scan, 0 signals, Eurovision markets flagged as WATCH

## Telegram channel — VERIFIED WORKING
- Channel: @ProbBrain (ProbBrain - Polymarket Signals)
- Bot: @ProbBrain_Lbot — administrator, can_post_messages=true
- TELEGRAM_CHANNEL_ID: set, correct format (-100xxxxxxxxxx)

## Credentials in .env (all set as of 2026-03-24)
- TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID: set and verified
- DUB_API_KEY, DUB_WORKSPACE_ID: set — Dub links pb-tg, pb-x live
- POLYMARKET_BUILDERS_API_KEY, POLYMARKET_REFERRAL_CODE: set
- X/Twitter OAuth 1.0a: all 4 credentials provided by board

## Open Blockers
- PRO-43: Automated 2h cron not confirmed (depends on PRO-53 — Founding Engineer)
- PRO-34: Public accuracy dashboard URL not verified live
- PRO-45: Signal #001 engagement check (depends on X setup PRO-26)
- PRO-53: Founding Engineer must set up cron trigger today

## Board Actions Outstanding
1. Approve Finance Overseer hire — [approval 607871bf](/PRO/approvals/607871bf-35c8-4c42-be48-ab0d1670648d)
2. Approve Strategy Optimizer hire — [approval 588c47d5](/PRO/approvals/588c47d5-7639-441b-9655-882946280b7a)
3. Approve Signal #2 (China-Taiwan before GTA VI) — PRO-64
4. Approve Signal #3 (OKC Thunder Western Conference Finals) — PRO-64
5. Confirm dashboard URL (PRO-34 / PRO-39)
6. Verify @ProbBrain is claimed on X (manual)
7. Optional: rename bot @ProbBrain_Lbot → @ProbBrain_bot via @BotFather

## Kill Switches
- #4 triggered and cleared 2026-03-24 (false alarm — evidence field was present)
- All others: no triggers to date

## Agent IDs
- CEO: 2d160bf5-a806-4be2-b03e-1bb95e1e0b15
- Research: c3411b1b-341e-4d07-92a1-c752e3bbfb53
- Signal Publisher: 1664c38b-a21d-4c73-9507-0467c9d88c1e
- Content: f59d6cba-a9f8-410b-8b9a-296714d9683a
- Analytics: ba0aebe6-929c-411f-9962-e9e8d5f0214f
- Retention: 02882703-068a-4237-a9ea-da3e38cf5c85
- Founding Engineer: 3859025f-c061-4c45-9564-79e399d563c6
- Studio Operations: eff602dd-fea8-4f43-94b0-e61c721f22df
- Finance Overseer (CFO): 61cb524a-b3a8-4ebc-8c0d-5caa711e1a53 — PENDING APPROVAL (607871bf)
- Strategy Optimizer (CSO): 043685c0-e4e0-472e-812e-9bc8b85a4692 — PENDING APPROVAL (588c47d5)

## Company
- Prefix: PRO
- Company ID: 34e5323e-41df-4405-b316-6ea05dc61956
- Goal ID: e2d373a8-364e-4a22-8d34-086ced3a0caf
