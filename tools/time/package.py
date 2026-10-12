"""Build the portable Mac package from an explicit, credential-free file list."""

import argparse
from pathlib import Path
import zipfile

FILES = ("cli.py", "ranges.py", "Time.command", "Install.command", "install.py", "README.txt")


def main() -> None:
    source = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="打包独立的 Mac Time 分享包")
    parser.add_argument("--out", type=Path, default=source.parents[1] / "reports/tools/Time-mac.zip")
    args = parser.parse_args()
    for name in FILES:
        if not (source / name).is_file():
            parser.error(f"缺少打包文件 {name}")
    output = args.out.resolve()
    if output.suffix.lower() != ".zip":
        parser.error("输出文件必须为 .zip")
    if output in {(source / name).resolve() for name in FILES}:
        parser.error("不能覆盖源码")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in FILES:
            entry = zipfile.ZipInfo(f"Time/{name}")
            entry.create_system = 3
            entry.external_attr = (0o100755 if name.endswith(".command") else 0o100644) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, (source / name).read_bytes())
    print(f"Mac 分享包：{output}")


if __name__ == "__main__":
    main()
