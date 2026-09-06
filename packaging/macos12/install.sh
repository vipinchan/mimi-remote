#!/bin/bash
set -euo pipefail

LABEL="com.vipinchan.mimi-remote.agentd"
BIN_DIR="$HOME/.local/bin"
BIN_PATH="$BIN_DIR/agentd"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/$LABEL.plist"
LOG_DIR="$HOME/Library/Logs/MimiRemote"
LOG_PATH="$LOG_DIR/agentd.log"
STDOUT_PATH="$LOG_DIR/launchd.stdout.log"
STDERR_PATH="$LOG_DIR/launchd.stderr.log"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOURCE_BIN="$SCRIPT_DIR/agentd"

fail() {
  echo "ERROR: $*" >&2
  exit 1
}

xml_escape() {
  printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
}

[[ "$(uname -s)" == "Darwin" ]] || fail "This package is for macOS only."
[[ -x "$SOURCE_BIN" ]] || fail "agentd binary not found next to install.sh"

MACOS_VERSION="$(sw_vers -productVersion)"
MACOS_MAJOR="${MACOS_VERSION%%.*}"
if [[ "$MACOS_MAJOR" -lt 12 ]]; then
  fail "macOS 12 or later is required; detected $MACOS_VERSION"
fi

case "$(uname -m)" in
  x86_64|arm64) ;;
  *) fail "Unsupported Mac architecture: $(uname -m)" ;;
esac

mkdir -p "$BIN_DIR" "$PLIST_DIR" "$LOG_DIR"
install -m 0755 "$SOURCE_BIN" "$BIN_PATH"

target="gui/$(id -u)/$LABEL"
if launchctl print "$target" >/dev/null 2>&1; then
  launchctl bootout "$target" >/dev/null 2>&1 || true
fi

BIN_XML="$(xml_escape "$BIN_PATH")"
HOME_XML="$(xml_escape "$HOME")"
LOG_XML="$(xml_escape "$LOG_PATH")"
STDOUT_XML="$(xml_escape "$STDOUT_PATH")"
STDERR_XML="$(xml_escape "$STDERR_PATH")"
PATH_XML="$(xml_escape "$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$BIN_XML</string>
    <string>serve</string>
    <string>--managed-service</string>
    <string>--log-file</string>
    <string>$LOG_XML</string>
  </array>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HOME</key>
    <string>$HOME_XML</string>
    <key>PATH</key>
    <string>$PATH_XML</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>ProcessType</key>
  <string>Background</string>
  <key>StandardOutPath</key>
  <string>$STDOUT_XML</string>
  <key>StandardErrorPath</key>
  <string>$STDERR_XML</string>
</dict>
</plist>
PLIST

chmod 0644 "$PLIST_PATH"
plutil -lint "$PLIST_PATH" >/dev/null

printf '\nInstalled Mimi Remote macOS 12 CLI Host\n'
printf '  macOS:      %s\n' "$MACOS_VERSION"
printf '  agentd:     %s\n' "$BIN_PATH"
printf '  LaunchAgent:%s\n' "$PLIST_PATH"
printf '\nThe service is intentionally left stopped until setup completes.\n'
printf 'Next:\n'
printf '  1. Ensure Codex works: codex --version && codex app-server --help\n'
printf '  2. Enable Remote Login and verify: ssh 127.0.0.1 true\n'
printf '  3. Start and create pairing QR: %s up\n' "$BIN_PATH"
printf '\nIf ~/.local/bin is not on PATH, use the full path above or add it to your shell PATH.\n'
