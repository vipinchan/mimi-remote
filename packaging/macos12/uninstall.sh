#!/bin/bash
set -euo pipefail

LABEL="com.vipinchan.mimi-remote.agentd"
BIN_PATH="$HOME/.local/bin/agentd"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
target="gui/$(id -u)/$LABEL"

if launchctl print "$target" >/dev/null 2>&1; then
  launchctl bootout "$target" >/dev/null 2>&1 || true
fi

rm -f "$PLIST_PATH" "$BIN_PATH"

printf 'Removed Mimi Remote macOS 12 CLI Host binary and LaunchAgent.\n'
printf 'Configuration and logs were preserved.\n'
printf '  Config: ~/Library/Application Support/mimi-remote/\n'
printf '  Logs:   ~/Library/Logs/MimiRemote/\n'
