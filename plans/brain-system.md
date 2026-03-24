# ProbBrain Agent Brain System
Created: 2026-03-24 | CEO (PRO-79)

## Overview

Every agent at ProbBrain has a persistent, file-based memory system located in their agent directory. This is the "brain" — it survives heartbeat restarts and lets agents build up knowledge over time.

## Structure

Each agent's home is `/home/slova/ProbBrain/agents/<agent-name>/`.

```
agents/<name>/
  AGENTS.md          # Identity, mission, rules (loaded every heartbeat)
  SOUL.md            # Persona and voice (optional, CEO has this)
  HEARTBEAT.md       # Execution checklist (optional, CEO has this)
  TOOLS.md           # Available tools (optional, CEO has this)
  memory/
    MEMORY.md        # Tacit knowledge index (loaded every heartbeat)
    YYYY-MM-DD.md    # Daily notes — raw timeline of events
  life/              # PARA knowledge graph
    index.md         # Top-level index
    projects/        # Active work with goals/deadlines
    areas/           # Ongoing responsibilities (people, companies)
      people/
      companies/
    resources/       # Reference material and topics
    archives/        # Inactive items
```

## Three Memory Layers

### Layer 1: Daily Notes (`memory/YYYY-MM-DD.md`)
Raw timeline of events — write continuously during work. Extract durable facts to Layer 2 during heartbeats.

### Layer 2: Knowledge Graph (`life/`)
Entity-based storage. Each entity gets `summary.md` (quick load) and `items.yaml` (atomic facts, on demand).

### Layer 3: Tacit Knowledge (`memory/MEMORY.md`)
How the agent operates — patterns, rules, lessons learned. The index of the memory system.

## Agent Directories Provisioned

| Agent | Home | Memory | Life |
|-------|------|--------|------|
| CEO | agents/ceo/ | ✅ | ✅ |
| Research | agents/research/ | ✅ | ✅ |
| Signal Publisher | agents/signal-publisher/ | ✅ | ✅ |
| Analytics | agents/analytics/ | ✅ | ✅ |
| Retention | agents/retention/ | ✅ | ✅ |
| Content | agents/content/ | ✅ | ✅ |
| Finance Overseer | agents/finance-overseer/ | ✅ | ✅ |
| Strategy Optimizer | agents/strategy-optimizer/ | ✅ | ✅ |
| Studio Operations | agents/studio-ops/ | ✅ | ✅ |

## Rules for Agents

1. **Write it down.** Memory does not survive session restarts. Files do.
2. **Daily notes first.** Log timeline events to `memory/YYYY-MM-DD.md` as you work.
3. **Extract durable facts.** Move important facts to `life/` entities during heartbeats.
4. **Update MEMORY.md.** When you learn a new operating pattern, update the index.
5. **Never delete facts.** Supersede instead (add `status: superseded`, `superseded_by`).
6. **Prefer `summary.md` on load.** Only load `items.yaml` when you need detail.

## PARA Classification

- **Projects**: Active work with a goal or deadline → `life/projects/`
- **Areas**: Ongoing responsibilities with no end date → `life/areas/`
- **Resources**: Reference material, topics of interest → `life/resources/`
- **Archives**: Inactive items from any category → `life/archives/`

When a project completes, move its folder to `archives/`. Keep it — it's institutional memory.
