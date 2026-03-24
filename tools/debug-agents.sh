#!/usr/bin/env bash
# Convenience wrapper — sources Paperclip env if running outside a heartbeat.
# Usage: ./tools/debug-agents.sh [--json] [--verbose]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$SCRIPT_DIR/.."

# If running outside a Paperclip heartbeat, try to pull vars from local CLI.
if [[ -z "${PAPERCLIP_API_KEY:-}" ]]; then
  echo "[debug-agents] PAPERCLIP_API_KEY not set."
  echo "  Run: paperclipai agent local-cli <agent-id> --company-id <company-id>"
  echo "  Then re-export the printed vars and re-run this script."
  exit 1
fi

exec python3 "$SCRIPT_DIR/debug-agents.py" "$@"
