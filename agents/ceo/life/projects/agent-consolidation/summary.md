# Agent Consolidation (2026-03-27)

Board merged ProbBrain from 11 agents to 4. Flat hierarchy — all reports direct to CEO.

## New Structure
- **CEO** — absorbs Strategy Optimizer + Finance Overseer
- **Analytics Agent** — absorbs Research Agent + Content Creator
- **Signal Publisher** — absorbs Twitter Engager + Content Agent + Pipeline orchestration
- **Founding Engineer** — unchanged

## Open Item
Signal Publisher `promptTemplate` in Paperclip API still references deleted agents (Pipeline Overseer, Content Creator, Twitter Engager). Board needs to update via API.
