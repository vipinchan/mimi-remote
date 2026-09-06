package main

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

const macos12LaunchAgentLabel = "com.vipinchan.mimi-remote.agentd"

func macos12LaunchAgentPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(home, "Library", "LaunchAgents", macos12LaunchAgentLabel+".plist"), nil
}

func macos12LogPath() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	return filepath.Join(home, "Library", "Logs", "MimiRemote", "agentd.log"), nil
}

func macos12LaunchDomain() (string, error) {
	id, err := exec.LookPath("id")
	if err != nil {
		return "", fmt.Errorf("未找到 id 命令：%w", err)
	}
	out, err := exec.Command(id, "-u").Output()
	if err != nil {
		return "", fmt.Errorf("读取当前用户 UID 失败：%w", err)
	}
	uid := strings.TrimSpace(string(out))
	if uid == "" {
		return "", fmt.Errorf("当前用户 UID 为空")
	}
	return "gui/" + uid, nil
}

func macos12LaunchTarget() (string, error) {
	domain, err := macos12LaunchDomain()
	if err != nil {
		return "", err
	}
	return domain + "/" + macos12LaunchAgentLabel, nil
}

func macos12LaunchAgentInstalled() (bool, error) {
	path, err := macos12LaunchAgentPath()
	if err != nil {
		return false, err
	}
	info, err := os.Stat(path)
	if err == nil {
		return info.Mode().IsRegular(), nil
	}
	if os.IsNotExist(err) {
		return false, nil
	}
	return false, fmt.Errorf("检查 macOS 12 LaunchAgent 失败：%w", err)
}

func ensureMacOS12LaunchAgentInstalled() error {
	installed, err := macos12LaunchAgentInstalled()
	if err != nil {
		return err
	}
	if installed {
		return nil
	}
	if _, err := exec.LookPath("brew"); err == nil {
		return nil
	}
	path, _ := macos12LaunchAgentPath()
	return fmt.Errorf("尚未安装 macOS 12 CLI Host LaunchAgent：%s\n请从 Personal Beta 解压目录运行：\n  bash ./install.sh", path)
}

func runMacOS12LaunchdService(action string, stdout, stderr io.Writer) error {
	installed, err := macos12LaunchAgentInstalled()
	if err != nil {
		return err
	}
	if !installed {
		if _, lookupErr := exec.LookPath("brew"); lookupErr != nil {
			return ensureMacOS12LaunchAgentInstalled()
		}
		if action == "restart" {
			return restartHomebrewService(stdout, stderr)
		}
		return runBrewService(action, stdout, stderr)
	}

	launchctl, err := exec.LookPath("launchctl")
	if err != nil {
		return fmt.Errorf("未找到 launchctl：%w", err)
	}
	domain, err := macos12LaunchDomain()
	if err != nil {
		return err
	}
	target, err := macos12LaunchTarget()
	if err != nil {
		return err
	}
	plist, err := macos12LaunchAgentPath()
	if err != nil {
		return err
	}

	loaded := exec.Command(launchctl, "print", target).Run() == nil
	run := func(args ...string) error {
		cmd := exec.Command(launchctl, args...)
		cmd.Stdout = stdout
		cmd.Stderr = stderr
		if err := cmd.Run(); err != nil {
			return fmt.Errorf("执行 launchctl %s 失败：%w", strings.Join(args, " "), err)
		}
		return nil
	}

	switch action {
	case "start":
		if !loaded {
			return run("bootstrap", domain, plist)
		}
		return run("kickstart", "-k", target)
	case "restart":
		if !loaded {
			return run("bootstrap", domain, plist)
		}
		return run("kickstart", "-k", target)
	case "stop":
		if !loaded {
			return nil
		}
		return run("bootout", target)
	default:
		return fmt.Errorf("macOS 12 LaunchAgent 不支持服务动作 %q", action)
	}
}

func runMacOS12LaunchdLogs(lineCount int, follow bool, stdout, stderr io.Writer) error {
	installed, err := macos12LaunchAgentInstalled()
	if err != nil {
		return err
	}
	if !installed {
		return runHomebrewLogs(lineCount, follow, stdout, stderr)
	}
	path, err := macos12LogPath()
	if err != nil {
		return err
	}
	fmt.Fprintf(stdout, "日志文件：%s\n\n", path)
	if follow {
		tail, err := exec.LookPath("tail")
		if err != nil {
			return fmt.Errorf("未找到 tail 命令：%w", err)
		}
		cmd := exec.Command(tail, "-n", fmt.Sprint(lineCount), "-f", path)
		cmd.Stdout = stdout
		cmd.Stderr = stderr
		return cmd.Run()
	}
	lines, err := tailLines(path, lineCount)
	if err != nil {
		return err
	}
	for _, line := range lines {
		fmt.Fprintln(stdout, line)
	}
	return nil
}
