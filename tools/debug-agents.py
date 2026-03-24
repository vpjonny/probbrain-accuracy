#!/usr/bin/env python3
"""
ProbBrain Agents Debugger
=========================
Queries the Paperclip API and prints a live status snapshot of every agent,
their current tasks, last comments, and any blockers.

Usage:
    python3 tools/debug-agents.py

Requires env vars: PAPERCLIP_API_URL, PAPERCLIP_API_KEY, PAPERCLIP_COMPANY_ID
You can also pass --json to get raw JSON output for piping.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_URL = os.environ.get("PAPERCLIP_API_URL", "http://127.0.0.1:3100")
API_KEY = os.environ.get("PAPERCLIP_API_KEY", "")
COMPANY_ID = os.environ.get("PAPERCLIP_COMPANY_ID", "")
JSON_MODE = "--json" in sys.argv
VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv

if not API_KEY or not COMPANY_ID:
    print("ERROR: PAPERCLIP_API_KEY and PAPERCLIP_COMPANY_ID must be set.")
    sys.exit(1)

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
def get(path: str) -> dict | list:
    url = f"{API_URL}{path}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "msg": e.reason}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Time helpers
# ---------------------------------------------------------------------------
def ago(iso: str | None) -> str:
    if not iso:
        return "never"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        secs = int((datetime.now(timezone.utc) - dt).total_seconds())
        if secs < 60:
            return f"{secs}s ago"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            return f"{secs // 3600}h ago"
        return f"{secs // 86400}d ago"
    except Exception:
        return iso


def is_stale(iso: str | None, threshold_sec: int = 7200) -> bool:
    """True if the timestamp is older than threshold_sec seconds."""
    if not iso:
        return True
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - dt).total_seconds() > threshold_sec
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[31m"
YELLOW = "\033[33m"
GREEN = "\033[32m"
CYAN = "\033[36m"
GRAY = "\033[90m"
MAGENTA = "\033[35m"


def c(text, *codes):
    if sys.stdout.isatty():
        return "".join(codes) + str(text) + RESET
    return str(text)


def hr(char="-", width=80):
    print(c(char * width, GRAY))


def section(title):
    hr("=")
    print(c(f"  {title}", BOLD, CYAN))
    hr("=")


# ---------------------------------------------------------------------------
# Main debug logic
# ---------------------------------------------------------------------------
def build_snapshot():
    snapshot = {}

    # Agents
    agents = get(f"/api/companies/{COMPANY_ID}/agents")
    snapshot["agents"] = agents if isinstance(agents, list) else []

    # Dashboard
    snapshot["dashboard"] = get(f"/api/companies/{COMPANY_ID}/dashboard")

    # All active issues (in_progress + blocked + todo)
    issues_raw = get(
        f"/api/companies/{COMPANY_ID}/issues?status=in_progress,blocked,todo"
    )
    snapshot["active_issues"] = issues_raw if isinstance(issues_raw, list) else []

    # Last comment per in-progress/blocked issue
    snapshot["last_comments"] = {}
    for issue in snapshot["active_issues"]:
        if issue.get("status") in ("in_progress", "blocked"):
            iid = issue["id"]
            comments = get(f"/api/issues/{iid}/comments")
            if isinstance(comments, list) and comments:
                snapshot["last_comments"][iid] = comments[-1]

    # Recent activity (last 30 events)
    activity = get(f"/api/companies/{COMPANY_ID}/activity?limit=30")
    snapshot["activity"] = activity if isinstance(activity, list) else []

    return snapshot


def build_agent_task_map(snapshot):
    """Map agentId -> list of active issues."""
    agent_tasks: dict[str, list] = {}
    for issue in snapshot["active_issues"]:
        aid = issue.get("assigneeAgentId")
        if aid:
            agent_tasks.setdefault(aid, []).append(issue)
    return agent_tasks


def print_agents_section(snapshot, agent_tasks):
    section("AGENTS")
    agents = sorted(snapshot["agents"], key=lambda a: a.get("name", ""))
    for agent in agents:
        aid = agent["id"]
        name = agent.get("name", "?")
        role = agent.get("role", "?")
        status = agent.get("status", "?")
        last_hb = agent.get("lastHeartbeatAt")
        stale = is_stale(last_hb, threshold_sec=7200)

        status_color = GREEN if status == "running" else (RED if status == "paused" else YELLOW)
        hb_color = RED if stale else GRAY

        print(
            f"  {c(name, BOLD):<30} {c(role, GRAY):<15} "
            f"{c(status, status_color):<10} "
            f"heartbeat: {c(ago(last_hb), hb_color)}"
        )

        tasks = agent_tasks.get(aid, [])
        if tasks:
            for t in tasks:
                ts = t.get("status", "?")
                ts_color = RED if ts == "blocked" else (CYAN if ts == "in_progress" else GRAY)
                title = t.get("title", "?")[:55]
                ident = t.get("identifier", "?")
                started = t.get("startedAt")
                print(
                    f"    {c('└', GRAY)} [{c(ts, ts_color)}] "
                    f"{c(ident, MAGENTA)} {title} "
                    f"{c('('+ago(started)+')', GRAY)}"
                )
                # Last comment
                last_comment = snapshot["last_comments"].get(t["id"])
                if last_comment:
                    body = last_comment.get("body", "").replace("\n", " ")[:120]
                    ca = last_comment.get("createdAt")
                    print(
                        f"      {c('msg:', GRAY)} {c(body+'...', GRAY)} "
                        f"{c(ago(ca), GRAY)}"
                    )
        else:
            print(f"    {c('(no active tasks)', GRAY)}")
        print()


def print_blockers_section(snapshot):
    blocked = [i for i in snapshot["active_issues"] if i.get("status") == "blocked"]
    if not blocked:
        print(c("  No blocked tasks.", GREEN))
        return

    for issue in blocked:
        ident = issue.get("identifier", "?")
        title = issue.get("title", "?")
        assignee = issue.get("executionAgentNameKey") or issue.get("assigneeAgentId", "?")
        print(f"  {c(ident, MAGENTA)} {c(title[:60], BOLD)} — {c(assignee, YELLOW)}")
        last_comment = snapshot["last_comments"].get(issue["id"])
        if last_comment:
            body = last_comment.get("body", "").replace("\n", " ")[:150]
            ca = last_comment.get("createdAt")
            print(f"    {c('Reason:', GRAY)} {body} {c(ago(ca), GRAY)}")
        else:
            print(f"    {c('No comments — reason unknown', RED)}")
        print()


def print_stale_section(snapshot):
    stale_issues = []
    for issue in snapshot["active_issues"]:
        if issue.get("status") == "in_progress":
            started = issue.get("startedAt")
            if is_stale(started, threshold_sec=3600):
                last_comment = snapshot["last_comments"].get(issue["id"])
                last_comment_at = last_comment.get("createdAt") if last_comment else None
                if is_stale(last_comment_at, threshold_sec=3600):
                    stale_issues.append((issue, last_comment))

    if not stale_issues:
        print(c("  No stale in-progress tasks.", GREEN))
        return

    for issue, last_comment in stale_issues:
        ident = issue.get("identifier", "?")
        title = issue.get("title", "?")
        assignee = issue.get("executionAgentNameKey") or issue.get("assigneeAgentId", "?")
        started = issue.get("startedAt")
        print(
            f"  {c(ident, MAGENTA)} {c(title[:55], BOLD)}"
            f" — {c(assignee, YELLOW)}"
            f" {c('started '+ago(started), RED)}"
        )
        if last_comment:
            body = last_comment.get("body", "").replace("\n", " ")[:120]
            ca = last_comment.get("createdAt")
            print(f"    {c('Last update:', GRAY)} {body} {c(ago(ca), GRAY)}")
        else:
            print(f"    {c('No updates posted', RED)}")
        print()


def print_activity_section(snapshot):
    activity = snapshot["activity"][:15]
    for event in activity:
        actor = event.get("actorId", "?")[:8]
        action = event.get("action", "?")
        details = event.get("details", {})
        ident = details.get("identifier", "")
        snippet = details.get("bodySnippet", "")[:80] if details.get("bodySnippet") else ""
        title = details.get("issueTitle", "")[:50] if details.get("issueTitle") else ""
        ts = event.get("createdAt")
        label = ident or title or ""
        desc = snippet or ""
        print(
            f"  {c(ago(ts), GRAY):<12} {c(action, CYAN):<30} "
            f"{c(label, MAGENTA)} {c(desc, GRAY)}"
        )


def print_dashboard_section(snapshot):
    d = snapshot.get("dashboard", {})
    agents_d = d.get("agents", {})
    tasks_d = d.get("tasks", {})
    costs_d = d.get("costs", {})
    print(
        f"  Agents:  running={c(agents_d.get('running',0), GREEN)}  "
        f"paused={c(agents_d.get('paused',0), YELLOW)}  "
        f"error={c(agents_d.get('error',0), RED)}"
    )
    print(
        f"  Tasks:   open={tasks_d.get('open',0)}  "
        f"in_progress={c(tasks_d.get('inProgress',0), CYAN)}  "
        f"blocked={c(tasks_d.get('blocked',0), RED)}  "
        f"done={c(tasks_d.get('done',0), GREEN)}"
    )
    spend = costs_d.get("monthSpendCents", 0)
    budget = costs_d.get("monthBudgetCents", 0)
    util = costs_d.get("monthUtilizationPercent", 0)
    print(
        f"  Budget:  spent=${spend/100:.2f}  budget=${budget/100:.2f}  "
        f"utilization={c(str(util)+'%', RED if util > 80 else GREEN)}"
    )
    pending = d.get("pendingApprovals", 0)
    if pending:
        print(f"  {c('Pending approvals: '+str(pending), YELLOW)}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print()
    print(c(f"  ProbBrain Agents Debugger — {now}", BOLD))
    print()

    snapshot = build_snapshot()
    agent_tasks = build_agent_task_map(snapshot)

    if JSON_MODE:
        print(json.dumps(snapshot, indent=2, default=str))
        return

    section("DASHBOARD")
    print_dashboard_section(snapshot)
    print()

    print_agents_section(snapshot, agent_tasks)

    section("BLOCKERS")
    print_blockers_section(snapshot)

    section("STALE IN-PROGRESS (>1h without update)")
    print_stale_section(snapshot)

    if VERBOSE:
        section("RECENT ACTIVITY")
        print_activity_section(snapshot)
        print()

    hr()
    print(
        c(
            f"  Tip: run with --verbose for activity log, --json for raw data.",
            GRAY,
        )
    )
    print()


if __name__ == "__main__":
    main()
