#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAIN = ROOT / "cmd" / "agentd" / "main.go"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


text = MAIN.read_text()

text = replace_once(
    text,
    '''\t\tif managedServicePlatform == "darwin" {\n\t\t\treturn fmt.Errorf("%w\\n\\n安装 Homebrew 后请重新运行：agentd up\\n排查环境可以运行：agentd doctor --fix", err)\n\t\t}''',
    '''\t\tif managedServicePlatform == "darwin" {\n\t\t\treturn fmt.Errorf("%w\\n\\n请确认已从 macOS 12 CLI Host 包运行 install.sh，然后重新执行：agentd up\\n排查环境可以运行：agentd doctor --fix", err)\n\t\t}''',
    "darwin up error",
)

text = replace_once(
    text,
    '''\tcase "darwin":\n\t\tif action == "restart" {\n\t\t\treturn restartHomebrewService(stdout, stderr)\n\t\t}\n\t\t// start/stop 继续复用 Homebrew；restart 必须保持为上面的 launchd 单次操作。\n\t\treturn runBrewService(action, stdout, stderr)''',
    '''\tcase "darwin":\n\t\treturn runMacOS12LaunchdService(action, stdout, stderr)''',
    "darwin service manager",
)

text = replace_once(
    text,
    '''\tcase "darwin":\n\t\treturn runHomebrewLogs(lineCount, follow, stdout, stderr)''',
    '''\tcase "darwin":\n\t\treturn runMacOS12LaunchdLogs(lineCount, follow, stdout, stderr)''',
    "darwin logs",
)

text = replace_once(
    text,
    '''\tcase "darwin":\n\t\treturn nil\n\tcase "linux":\n\t\tunitPath, err := linuxUserServiceUnitPath()''',
    '''\tcase "darwin":\n\t\treturn ensureMacOS12LaunchAgentInstalled()\n\tcase "linux":\n\t\tunitPath, err := linuxUserServiceUnitPath()''',
    "darwin service installation check",
)

MAIN.write_text(text)
print("Applied macOS 12 CLI Host compatibility patch")
