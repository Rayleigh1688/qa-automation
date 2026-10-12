"""Install only the portable Time zsh function; preserve existing configuration."""

import os
from pathlib import Path
import re
import shlex
import sys


def main() -> None:
    if len(sys.argv) != 1:
        raise SystemExit("安装入口不接受参数；直接打开 Install.command。")
    source = Path(__file__).resolve().parent
    for name in ("Time.command", "cli.py", "ranges.py"):
        if not (source / name).is_file():
            raise SystemExit(f"缺少 {name}，请先完整解压 Time 文件夹。")
    config = Path(os.environ.get("ZDOTDIR") or Path.home()) / ".zshrc"
    if not config.parent.is_dir():
        raise SystemExit("zsh 配置目录不存在，未修改配置。")
    block = (
        "# BEGIN standalone Time\n"
        "Time() {\n"
        f"  /bin/zsh {shlex.quote(str(source / 'Time.command'))} --no-pause \"$@\"\n"
        "}\n"
        "# END standalone Time\n"
    )
    original = config.read_bytes() if config.exists() else b""
    text = original.decode("utf-8")
    if "# BEGIN standalone Time" in text:
        if block not in text:
            raise SystemExit("已有 Time 安装指向另一位置，请先删除原标记块后重新安装；未修改配置。")
        print("Time 已安装，无需重复安装。")
    elif re.search(r"(?m)^\s*(?:function\s+Time\b|Time\s*\(\s*\)|alias\b[^\n]*\bTime\s*=)", text):
        raise SystemExit("已有 Time 函数或别名，为保留原配置，本次未安装。")
    else:
        addition = ("\n" if original and not original.endswith(b"\n") else "") + "\n" + block
        with config.open("ab") as output:
            output.write(addition.encode("utf-8"))
        print(f"已将 Time 命令添加到 {config}")
    print("重新打开终端，然后输入 Time 即可；也可使用 Time --json。")
    print("请保留当前文件夹；移动文件夹后需删除配置中的 standalone Time 标记块并重新安装。")


if __name__ == "__main__":
    main()
