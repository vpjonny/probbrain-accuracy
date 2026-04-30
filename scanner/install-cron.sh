#!/usr/bin/env bash
# scanner/install-cron.sh — idempotent crontab installer.
#
# Adds (or refreshes) a single line that runs the scanner every 15 minutes,
# logging to scanner/cron.log. Safe to re-run: existing line gets replaced.
#
# Usage:
#   bash scanner/install-cron.sh           # install / refresh the crontab line
#   bash scanner/install-cron.sh --remove  # remove the crontab line
#   bash scanner/install-cron.sh --print   # print the line that would be installed (no-op)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NODE_BIN="$(command -v node || true)"

if [[ -z "$NODE_BIN" ]]; then
  echo "error: 'node' not found in PATH. install Node 20+ first." >&2
  exit 1
fi

# A unique tag so we can find / replace our line without touching unrelated
# crontab entries. cron strips comments at exec time so this is safe.
TAG="# probbrain-arbitrage-scanner"
CRON_LINE="*/15 * * * * cd $REPO_ROOT && $NODE_BIN scanner/scan.js >> scanner/cron.log 2>&1 $TAG"

action="${1:-install}"

case "$action" in
  --print|-p)
    echo "$CRON_LINE"
    exit 0
    ;;
  --remove|-r)
    if ! crontab -l 2>/dev/null | grep -qF "$TAG"; then
      echo "no probbrain-arbitrage-scanner cron line found — nothing to remove."
      exit 0
    fi
    crontab -l 2>/dev/null | grep -vF "$TAG" | crontab -
    echo "removed probbrain-arbitrage-scanner cron line."
    exit 0
    ;;
  install|"")
    # Strip any existing tagged line, then append the fresh one.
    {
      crontab -l 2>/dev/null | grep -vF "$TAG" || true
      echo "$CRON_LINE"
    } | crontab -
    echo "installed (every 15 min):"
    echo "  $CRON_LINE"
    echo
    echo "logs: $REPO_ROOT/scanner/cron.log"
    echo "remove with: bash scanner/install-cron.sh --remove"
    ;;
  *)
    echo "usage: bash scanner/install-cron.sh [install|--remove|--print]" >&2
    exit 2
    ;;
esac
