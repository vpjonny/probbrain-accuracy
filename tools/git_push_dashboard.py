"""
git_push_dashboard.py — commit and push dashboard/accuracy.json and data/published_signals.json
to GitHub after each signal.

Called by the pipeline immediately after recompute_accuracy() so GitHub Pages
reflects every signal in real time rather than waiting for the 2h cron.
"""
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD_ACCURACY = ROOT / "dashboard" / "accuracy.json"
PUBLISHED_SIGNALS = ROOT / "data" / "published_signals.json"


def _run(cmd: list[str], cwd: Path = ROOT) -> tuple[int, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, (result.stdout + result.stderr).strip()


def push(signal_id: str = "") -> bool:
    """
    Stage dashboard/accuracy.json and data/published_signals.json, commit, and push to origin/main.

    Returns True on success, False on failure (non-fatal — pipeline continues).
    """
    if not DASHBOARD_ACCURACY.exists():
        logger.warning("git_push_dashboard: accuracy.json not found, skipping push")
        return False

    # Check if there's anything to commit in either tracked file
    rc, diff = _run(["git", "diff", "--name-only", "dashboard/accuracy.json", "data/published_signals.json"])
    if rc != 0:
        logger.error("git diff failed: %s", diff)
        return False

    if not diff.strip():
        logger.info("git_push_dashboard: no changes to commit, nothing to push")
        return True

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    msg_parts = ["chore: live accuracy update"]
    if signal_id:
        msg_parts.append(f"after {signal_id}")
    msg_parts.append(f"[{ts}]")
    commit_msg = " ".join(msg_parts) + "\n\nCo-Authored-By: Paperclip <noreply@paperclip.ing>"

    files_to_stage = ["dashboard/accuracy.json"]
    if PUBLISHED_SIGNALS.exists():
        files_to_stage.append("data/published_signals.json")

    steps = [
        (["git", "add"] + files_to_stage, "stage"),
        (["git", "commit", "-m", commit_msg], "commit"),
        (["git", "push", "origin", "main"], "push"),
    ]

    for cmd, label in steps:
        rc, out = _run(cmd)
        if rc != 0:
            logger.error("git_push_dashboard: %s failed: %s", label, out)
            return False
        logger.info("git_push_dashboard: %s OK — %s", label, out[:120])

    logger.info("git_push_dashboard: dashboard + published_signals pushed to GitHub — deploy-pages.yml triggered")
    return True
