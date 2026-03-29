# Signal Pipeline — Analytics Agent

Active market scanning operation for ProbBrain. Inherited from Research Agent (terminated 2026-03-29).

## Current State (2026-03-29)
- Scanner: OPERATIONAL — fetching from gamma-api.polymarket.com
- Scan interval: 2h between 7am-11pm UTC
- Liquidity filter: vol ≥$50k
- Misfire threshold: ≥8% gap

## Watch Queue (carried over from Research Agent, 2026-03-24)
- Iran regime fall by June 30 (ID 958443) — YES 20.5%, vol $21M
- US forces enter Iran by Mar31 — YES 25.5%, vol $18.5M, closes in 7 days
- Colorado Avalanche Stanley Cup — YES 20.1%, vol $13M

## Rules
- Liquidity filter: vol ≥$50k
- Misfire threshold: ≥8% gap
- Evidence required: specific source (article, base rate, Manifold, expert data)
- Signals with gap <20pp: approval_required=false (auto-publish)
- Signals with gap ≥20pp: approval_required=true (CEO gate)
