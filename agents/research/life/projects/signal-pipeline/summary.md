# Signal Pipeline — Research Agent

Active market scanning operation for ProbBrain.

## Current State (2026-03-24)
- Scanner: OPERATIONAL — fetching from gamma-api.polymarket.com
- Scan interval: 2h between 7am-11pm UTC
- Markets scanned today: ~16,869
- Signals surfaced: 5 (2 approved for board: China-Taiwan, OKC Thunder)
- Kill switches: all clear

## Watch Queue
- Iran regime fall by June 30 (ID 958443) — YES 20.5%, vol $21M
- US forces enter Iran by Mar31 — YES 25.5%, vol $18.5M, closes in 7 days
- Colorado Avalanche Stanley Cup — YES 20.1%, vol $13M

## Rules
- Liquidity filter: vol ≥$50k
- Misfire threshold: ≥8% gap
- Evidence required: specific source (article, base rate, Manifold, expert data)
- First 10 signals: approval_required=true
