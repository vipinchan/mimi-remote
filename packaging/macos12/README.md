# Mimi Remote macOS 12 CLI Host

This package is a personal compatibility host for macOS Monterey. It keeps the upstream Go `agentd` protocol and replaces the normal Homebrew/macOS 15 menu-bar service path with a user LaunchAgent.

## Release channel

This branch publishes a separate Personal Beta for Monterey and does not modify the normal macOS 15+ application release path. Release assets are split by Mac architecture and include SHA-256 checksums.

## Requirements

- macOS 12.0 or later.
- Codex CLI installed, authenticated, and able to run `codex app-server --help`.
- For the macOS shared App Server transport, Remote Login enabled and `ssh 127.0.0.1 true` working without an interactive password prompt.
- iPhone/iPad and Mac on the same trusted LAN, or another private network path supported by Mimi Remote.

## Choose the package

```bash
uname -m
```

- `x86_64`: use `MimiRemote-AgentHost-macOS12.6-x86_64.tar.gz`.
- `arm64`: use `MimiRemote-AgentHost-macOS12.6-arm64.tar.gz`.

Both release binaries are validated by CI as Mach-O executables with minimum macOS version 12.0.

## Install

```bash
bash ./install.sh
~/.local/bin/agentd up
```

`agentd up` prepares the normal Mimi Remote configuration, starts the user LaunchAgent, waits for readiness, and prints a short-lived pairing QR code. Without Tailscale, macOS setup automatically uses an available private LAN IPv4 address when one is detected.

If macOS blocks the personal unsigned binary after downloading it through a browser, inspect the downloaded archive and remove quarantine only after confirming it came from your own GitHub Release:

```bash
xattr -dr com.apple.quarantine ./MimiRemote-AgentHost-macOS12.6-*
```

Useful commands:

```bash
~/.local/bin/agentd status
~/.local/bin/agentd pair --qr-only
~/.local/bin/agentd doctor --fix
~/.local/bin/agentd logs -n 200
~/.local/bin/agentd restart --no-pair
~/.local/bin/agentd stop
```

## Uninstall

```bash
bash ./uninstall.sh
```

The uninstaller removes only the compatibility binary and LaunchAgent. Existing Mimi Remote configuration and logs are preserved.

## Compatibility boundary

This package does not install or downgrade `Mimi Remote Mac.app`. Visual menu-bar features that require macOS 15 are intentionally excluded. The mobile protocol, pairing, project/session APIs, approvals, and Codex App Server routing remain provided by upstream `agentd`.
