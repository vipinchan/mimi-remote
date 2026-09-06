//go:build darwin

package main

import (
	"io"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestMacOS12LaunchAgentLifecycle(t *testing.T) {
	home := filepath.Join(t.TempDir(), "home")
	launchAgents := filepath.Join(home, "Library", "LaunchAgents")
	if err := os.MkdirAll(launchAgents, 0o755); err != nil {
		t.Fatal(err)
	}
	plist := filepath.Join(launchAgents, macos12LaunchAgentLabel+".plist")
	if err := os.WriteFile(plist, []byte("<?xml version=\"1.0\"?><plist version=\"1.0\"><dict/></plist>"), 0o644); err != nil {
		t.Fatal(err)
	}

	fakeBin := filepath.Join(t.TempDir(), "bin")
	if err := os.MkdirAll(fakeBin, 0o755); err != nil {
		t.Fatal(err)
	}
	logPath := filepath.Join(t.TempDir(), "launchctl.log")
	idScript := "#!/bin/sh\nif [ \"${1:-}\" = \"-u\" ]; then echo 501; exit 0; fi\nexit 1\n"
	launchctlScript := `#!/bin/sh
printf '%s\n' "$*" >> "$MIMI_TEST_LAUNCHCTL_LOG"
if [ "${1:-}" = "print" ]; then
  if [ "${MIMI_TEST_LAUNCHCTL_LOADED:-0}" = "1" ]; then
    exit 0
  fi
  exit 1
fi
exit 0
`
	for name, content := range map[string]string{"id": idScript, "launchctl": launchctlScript} {
		if err := os.WriteFile(filepath.Join(fakeBin, name), []byte(content), 0o755); err != nil {
			t.Fatal(err)
		}
	}

	t.Setenv("HOME", home)
	t.Setenv("PATH", fakeBin+":/usr/bin:/bin")
	t.Setenv("MIMI_TEST_LAUNCHCTL_LOG", logPath)

	if err := runMacOS12LaunchdService("start", io.Discard, io.Discard); err != nil {
		t.Fatalf("unloaded Monterey LaunchAgent start failed: %v", err)
	}
	log := readMacOS12TestLog(t, logPath)
	if !strings.Contains(log, "print gui/501/"+macos12LaunchAgentLabel) {
		t.Fatalf("start must inspect the user LaunchAgent first: %q", log)
	}
	if !strings.Contains(log, "bootstrap gui/501 "+plist) {
		t.Fatalf("unloaded start must bootstrap the compatibility plist: %q", log)
	}

	if err := os.WriteFile(logPath, nil, 0o600); err != nil {
		t.Fatal(err)
	}
	t.Setenv("MIMI_TEST_LAUNCHCTL_LOADED", "1")
	if err := runMacOS12LaunchdService("restart", io.Discard, io.Discard); err != nil {
		t.Fatalf("loaded Monterey LaunchAgent restart failed: %v", err)
	}
	log = readMacOS12TestLog(t, logPath)
	if !strings.Contains(log, "kickstart -k gui/501/"+macos12LaunchAgentLabel) {
		t.Fatalf("loaded restart must use one launchctl kickstart: %q", log)
	}

	if err := os.WriteFile(logPath, nil, 0o600); err != nil {
		t.Fatal(err)
	}
	if err := runMacOS12LaunchdService("stop", io.Discard, io.Discard); err != nil {
		t.Fatalf("loaded Monterey LaunchAgent stop failed: %v", err)
	}
	log = readMacOS12TestLog(t, logPath)
	if !strings.Contains(log, "bootout gui/501/"+macos12LaunchAgentLabel) {
		t.Fatalf("loaded stop must boot out the compatibility LaunchAgent: %q", log)
	}
}

func readMacOS12TestLog(t *testing.T, path string) string {
	t.Helper()
	raw, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return string(raw)
}
