# Heartbeat Git Workflow

Proper git workflow for Paperclip heartbeat work in ProbBrain.

## Pre-Work: Sync with Origin

Before making any changes, ensure the local branch is in sync with origin:

```bash
git pull origin main --rebase
```

This prevents merge conflicts when pushing later. `--rebase` keeps the commit history clean.

## Making Changes

Edit files as needed. Check status before committing:

```bash
git status
```

Stage and commit with proper message format:

```bash
git commit -m "$(cat <<'EOF'
<subject line (imperative, ~50 chars)>

<detailed explanation of changes>

Co-Authored-By: Paperclip <noreply@paperclip.ing>
EOF
)"
```

**Rules:**
- Subject is imperative: "fix", "add", "update", not "fixed", "added"
- Body explains _why_ not just _what_
- Always include `Co-Authored-By: Paperclip <noreply@paperclip.ing>` trailer
- Use HEREDOC to preserve formatting and trailing newlines

## Pushing Changes

Push to origin after each commit:

```bash
git push origin main
```

**If push fails:**

1. **"rejected ... non-fast-forward"** → Someone pushed while you were working
   - Pull and rebase: `git pull origin main --rebase`
   - Resolve any merge conflicts
   - Push again: `git push origin main`

2. **"permission denied" or network error** → Check connection, API key, or permissions
   - Verify: `git remote -v`
   - Try again after checking logs

## Verify Success

After pushing, verify the commit is live:

```bash
git log --oneline -1
git rev-parse HEAD
git rev-parse origin/main
# Both should show the same commit hash
```

## Why This Matters

- **Pre-pull prevents conflicts**: Sync early to avoid work-blocking merge conflicts
- **Proper commits track intent**: Co-authored-by links work to Paperclip runs
- **Push immediately after commit**: Don't batch commits — each commit should be pushable independently
- **Verify success**: Don't assume push worked — check that origin is updated

## Anti-Patterns to Avoid

- ❌ Committing multiple unrelated changes in one commit
- ❌ Pushing without pulling first (creates "needs merge" state)
- ❌ Attempting force-push (only use if explicitly instructed)
- ❌ Committing without `Co-Authored-By` trailer in Paperclip heartbeats
- ❌ Leaving uncommitted changes between heartbeats

## Example: Complete Workflow

```bash
# 1. Start: sync with origin
git pull origin main --rebase

# 2. Make changes
# [edit files]

# 3. Commit with proper message
git commit -m "$(cat <<'EOF'
Fix: resolve accuracy.json conflict

Local version reflects data cleanup from pending_signals.json sync.
This recomputed accuracy is authoritative.

Co-Authored-By: Paperclip <noreply@paperclip.ing>
EOF
)"

# 4. Push
git push origin main

# 5. Verify
git log --oneline -1
git rev-parse origin/main
```

---

Last updated: 2026-03-30
Heartbeat task: PRO-30 — "teach yourself to do git pushes the proper way"
