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
DASHBOARD_INDEX = ROOT / "dashboard" / "index.html"
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
        (["git", "push", "origin", "main"], "push origin"),
    ]

    for cmd, label in steps:
        rc, out = _run(cmd)
        if rc != 0:
            logger.error("git_push_dashboard: %s failed: %s", label, out)
            return False
        logger.info("git_push_dashboard: %s OK — %s", label, out[:120])

    # Also sync accuracy.json to probbrain-accuracy (the public-facing dashboard URL).
    # That repo serves files from its root, so we push accuracy.json there directly.
    _sync_accuracy_repo(commit_msg)

    logger.info("git_push_dashboard: dashboard + published_signals pushed to GitHub — deploy-pages.yml triggered")
    return True


def _sync_accuracy_repo(commit_msg: str) -> None:
    """
    Push updated accuracy.json to the probbrain-accuracy repo root.
    That repo's GitHub Pages serves from its root, so accuracy.json at root
    is what vpjonny.github.io/probbrain-accuracy/ fetches.
    Non-fatal — logs warnings on failure.
    """
    # Ensure the remote is configured
    rc, remotes = _run(["git", "remote"])
    if "accuracy" not in remotes.split():
        _run(["git", "remote", "add", "accuracy", "https://github.com/vpjonny/probbrain-accuracy.git"])

    # Fetch the current accuracy/main
    rc, out = _run(["git", "fetch", "accuracy", "main"])
    if rc != 0:
        logger.warning("git_push_dashboard: accuracy fetch failed: %s", out[:120])
        return

    # Check out accuracy/main in a temporary worktree
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        rc, out = _run(["git", "worktree", "add", str(tmppath), "accuracy/main"])
        if rc != 0:
            logger.warning("git_push_dashboard: accuracy worktree failed: %s", out[:120])
            return
        try:
            import shutil
            shutil.copy(str(DASHBOARD_ACCURACY), str(tmppath / "accuracy.json"))
            if DASHBOARD_INDEX.exists():
                shutil.copy(str(DASHBOARD_INDEX), str(tmppath / "index.html"))
            rc, out = _run(["git", "add", "accuracy.json", "index.html"], cwd=tmppath)
            if rc != 0:
                logger.warning("git_push_dashboard: accuracy add failed: %s", out)
                return
            rc, diff = _run(["git", "diff", "--cached", "--name-only"], cwd=tmppath)
            if not diff.strip():
                logger.info("git_push_dashboard: accuracy repo already up to date, skip")
                return
            rc, out = _run(["git", "commit", "-m", commit_msg], cwd=tmppath)
            if rc != 0:
                logger.warning("git_push_dashboard: accuracy commit failed: %s", out)
                return
            rc, out = _run(["git", "push", "accuracy", "HEAD:main"], cwd=tmppath)
            if rc != 0:
                logger.warning("git_push_dashboard: accuracy push failed: %s", out[:120])
            else:
                logger.info("git_push_dashboard: accuracy repo synced OK")
        finally:
            _run(["git", "worktree", "remove", "--force", str(tmppath)])
