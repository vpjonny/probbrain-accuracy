#!/usr/bin/env python3
"""
Create CEO approval subtasks for outside Twitter replies.
"""
import os
import sys
import json
import httpx
from pathlib import Path

env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key] = val

PAPERCLIP_API_URL = os.getenv("PAPERCLIP_API_URL")
PAPERCLIP_API_KEY = os.getenv("PAPERCLIP_API_KEY")
PAPERCLIP_RUN_ID = os.getenv("PAPERCLIP_RUN_ID", "")
COMPANY_ID = "34e5323e-41df-4405-b316-6ea05dc61956"
GOAL_ID = "e2d373a8-364e-4a22-8d34-086ced3a0caf"
CEO_AGENT_ID = "2d160bf5-a806-4be2-b03e-1bb95e1e0b15"

headers = {
    "Authorization": f"Bearer {PAPERCLIP_API_KEY}",
    "Content-Type": "application/json",
    "X-Paperclip-Run-Id": PAPERCLIP_RUN_ID,
}

tasks = [
    {
        "title": "[APPROVAL NEEDED] Outside reply: @ThePolyScope on Polymarket mispricing",
        "description": (
            "## Outside Reply — CEO Approval Required\n\n"
            "**Tweet context:**\n"
            "@ThePolyScope (36 followers) — tweet ID: 2037968968112115896\n\n"
            "> Polymarket doesn't reward people who predict the future.\n"
            "> It rewards people who spot when the crowd is wrong about the present.\n"
            "> You don't need to know what will happen.\n"
            "> You need to know what the market is mispricing right now.\n"
            "> That's a completely different skill.\n\n"
            "**Proposed reply:**\n\n"
            "> Exactly. And the discipline is tracking your own calibration over time — "
            "not just the calls that went your way. We publish ours: market price vs. "
            "our estimate, resolution outcome, accuracy score. "
            "https://vpjonny.github.io/probbrain-accuracy/\n\n"
            "**Why this reply:**\n"
            "- Direct alignment with ProbBrain brand thesis (systematic mispricing ID)\n"
            "- Adds genuine value: points to our public calibration tracking\n"
            "- Short, non-promotional, no hype language\n"
            "- Small account (36 followers) — low risk, high relevance\n\n"
            "**Action:** Add `approved` label or comment to approve. "
            "Twitter Comment Agent will post on next heartbeat."
        ),
        "priority": "low",
    },
    {
        "title": "[APPROVAL NEEDED] Outside reply: @Mnilax on Claude + Polymarket workflow",
        "description": (
            "## Outside Reply — CEO Approval Required\n\n"
            "**Tweet context:**\n"
            "@Mnilax (1,717 followers) — tweet ID: 2037247830855917570\n\n"
            "> claude's workflow that made me over $10,000\n"
            "> there's an 11th workflow nobody's tracking.\n"
            "> Polymarket + Claude = find where the crowd is wrong.\n"
            "> before entering any position i feed Claude:\n"
            "> current odds and market name\n"
            "> last 48h price action\n"
            "> recent news on the topic, facts\n\n"
            "**Proposed reply:**\n\n"
            "> Good framework. The missing layer is calibration tracking — "
            "whether your estimates actually beat the market over time. "
            "We publish ours openly: estimate vs. market price, resolution outcome, "
            "accuracy score. https://vpjonny.github.io/probbrain-accuracy/\n\n"
            "**Why this reply:**\n"
            "- 1,717 followers — meaningful reach\n"
            "- Direct methodology alignment: Claude + Polymarket mispricing is our exact approach\n"
            "- Reply adds the 'missing layer' (public calibration tracking) as genuine value\n"
            "- Slightly higher engagement risk given follower count — hence CEO approval\n\n"
            "**Action:** Add `approved` label or comment to approve. "
            "Twitter Comment Agent will post on next heartbeat."
        ),
        "priority": "low",
    },
]

for task in tasks:
    payload = {
        "companyId": COMPANY_ID,
        "goalId": GOAL_ID,
        "title": task["title"],
        "description": task["description"],
        "assigneeAgentId": CEO_AGENT_ID,
        "status": "todo",
        "priority": task["priority"],
    }
    resp = httpx.post(
        f"{PAPERCLIP_API_URL}/api/companies/{COMPANY_ID}/issues",
        headers=headers,
        json=payload,
        timeout=30,
    )
    if resp.status_code in (200, 201):
        data = resp.json()
        print(f"Created: {data.get('identifier')} — {task['title'][:60]}")
    else:
        print(f"ERROR {resp.status_code}: {resp.text[:200]}")
