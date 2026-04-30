#!/usr/bin/env bash
# scanner/install-systemd.sh — idempotent systemd user-timer installer.
#
# Native scheduling on systemd-only distros (Arch, Fedora minimal, etc.) where
# `crontab` isn't available. Equivalent to install-cron.sh but uses
# ~/.config/systemd/user/ units.
#
# Usage:
#   bash scanner/install-systemd.sh           # install / refresh
#   bash scanner/install-systemd.sh --remove  # disable + delete units
#   bash scanner/install-systemd.sh --status  # show timer state + last run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NODE_BIN="$(command -v node || true)"

UNIT_NAME="probbrain-arb-scanner"
UNIT_DIR="$HOME/.config/systemd/user"
SERVICE_PATH="$UNIT_DIR/$UNIT_NAME.service"
TIMER_PATH="$UNIT_DIR/$UNIT_NAME.timer"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "error: systemctl not found. on cron-based systems use install-cron.sh instead." >&2
  exit 1
fi
if [[ -z "$NODE_BIN" ]]; then
  echo "error: 'node' not found in PATH. install Node 20+ first." >&2
  exit 1
fi

action="${1:-install}"

case "$action" in
  --status|-s|status)
    systemctl --user list-timers "$UNIT_NAME.timer" --all --no-pager 2>&1 || true
    echo
    journalctl --user -u "$UNIT_NAME.service" -n 12 --no-pager 2>&1 || true
    exit 0
    ;;
  --remove|-r|remove)
    systemctl --user disable --now "$UNIT_NAME.timer" 2>/dev/null || true
    rm -f "$SERVICE_PATH" "$TIMER_PATH"
    systemctl --user daemon-reload
    echo "removed $UNIT_NAME timer + service."
    exit 0
    ;;
  install|"")
    mkdir -p "$UNIT_DIR"
    cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=ProbBrain Polymarket × Kalshi arbitrage scanner
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$REPO_ROOT
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/bin
ExecStart=$NODE_BIN scanner/scan.js
StandardOutput=journal
StandardError=journal
TimeoutStartSec=10min

[Install]
WantedBy=default.target
EOF

    cat > "$TIMER_PATH" <<EOF
[Unit]
Description=ProbBrain arb scanner — every 15 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=15min
Unit=$UNIT_NAME.service
Persistent=true

[Install]
WantedBy=timers.target
EOF

    systemctl --user daemon-reload
    systemctl --user enable --now "$UNIT_NAME.timer"

    echo "installed $UNIT_NAME timer (every 15 min)."
    echo "  service: $SERVICE_PATH"
    echo "  timer:   $TIMER_PATH"
    echo
    echo "tail logs:    journalctl --user -fu $UNIT_NAME.service"
    echo "next runs:    bash scanner/install-systemd.sh --status"
    echo "remove:       bash scanner/install-systemd.sh --remove"
    echo
    if ! loginctl show-user "$USER" --property=Linger 2>/dev/null | grep -q "Linger=yes"; then
      echo "note: 'loginctl enable-linger $USER' (with sudo) makes the timer survive logout."
    fi
    ;;
  *)
    echo "usage: bash scanner/install-systemd.sh [install|--remove|--status]" >&2
    exit 2
    ;;
esac
