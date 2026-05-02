#!/usr/bin/env bash
# news-fetcher/install-systemd.sh — idempotent systemd user-timer installer.
#
# Mirrors scanner/install-systemd.sh. Schedules news-fetch.js every 15 min.
# Logs go to journalctl --user.
#
# Usage:
#   bash news-fetcher/install-systemd.sh                # install + enable + start
#   bash news-fetcher/install-systemd.sh --install-only # write units, daemon-reload, no enable
#   bash news-fetcher/install-systemd.sh --remove       # disable + delete units
#   bash news-fetcher/install-systemd.sh --status       # show timer state + last 12 log lines

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NODE_BIN="$(command -v node || true)"

UNIT_NAME="probbrain-news-fetcher"
UNIT_DIR="$HOME/.config/systemd/user"
SERVICE_PATH="$UNIT_DIR/$UNIT_NAME.service"
TIMER_PATH="$UNIT_DIR/$UNIT_NAME.timer"

if ! command -v systemctl >/dev/null 2>&1; then
  echo "error: systemctl not found." >&2
  exit 1
fi
if [[ -z "$NODE_BIN" ]]; then
  echo "error: 'node' not found in PATH. install Node 20+ first." >&2
  exit 1
fi

action="${1:-install}"

write_units() {
  mkdir -p "$UNIT_DIR"
  cat > "$SERVICE_PATH" <<EOF
[Unit]
Description=ProbBrain news fetcher
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$SCRIPT_DIR
Environment=PATH=$HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/bin
ExecStart=$NODE_BIN $SCRIPT_DIR/news-fetch.js
StandardOutput=journal
StandardError=journal
TimeoutStartSec=15min

[Install]
WantedBy=default.target
EOF

  cat > "$TIMER_PATH" <<EOF
[Unit]
Description=ProbBrain news fetcher — every 15 minutes

[Timer]
OnBootSec=3min
OnUnitActiveSec=15min
Unit=$UNIT_NAME.service
Persistent=true

[Install]
WantedBy=timers.target
EOF

  systemctl --user daemon-reload
}

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
  --install-only)
    write_units
    echo "wrote units (timer NOT enabled):"
    echo "  service: $SERVICE_PATH"
    echo "  timer:   $TIMER_PATH"
    echo
    echo "to enable: systemctl --user enable --now $UNIT_NAME.timer"
    exit 0
    ;;
  install|"")
    write_units
    systemctl --user enable --now "$UNIT_NAME.timer"
    echo "installed $UNIT_NAME timer (every 15 min)."
    echo "  service: $SERVICE_PATH"
    echo "  timer:   $TIMER_PATH"
    echo
    echo "tail logs:   journalctl --user -fu $UNIT_NAME.service"
    echo "next runs:   bash news-fetcher/install-systemd.sh --status"
    echo "remove:      bash news-fetcher/install-systemd.sh --remove"
    echo
    if ! loginctl show-user "$USER" --property=Linger 2>/dev/null | grep -q "Linger=yes"; then
      echo "note: 'sudo loginctl enable-linger $USER' makes the timer survive logout."
    fi
    ;;
  *)
    echo "usage: bash news-fetcher/install-systemd.sh [install|--install-only|--remove|--status]" >&2
    exit 2
    ;;
esac
