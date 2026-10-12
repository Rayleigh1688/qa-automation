"""Offline checks for the standalone Mac Time sharing package and installer."""

from support import ROOT

import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile


SOURCE = ROOT / "tools/time"
SHARE_FILES = {
    "Time/cli.py",
    "Time/ranges.py",
    "Time/Time.command",
    "Time/Install.command",
    "Time/install.py",
    "Time/README.txt",
}


class TimeSharingTest(unittest.TestCase):
    def run_python(self, entry, *arguments, cwd, environment=None):
        return subprocess.run(
            [sys.executable, str(entry), *arguments],
            cwd=cwd,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            check=False,
        )

    def test_share_zip_contains_only_standalone_files_with_executable_launchers(self):
        with tempfile.TemporaryDirectory(prefix="Time share ") as directory:
            archive = Path(directory) / "Time-mac.zip"
            result = self.run_python(SOURCE / "package.py", "--out", str(archive), cwd=directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(archive) as package:
                self.assertEqual(set(package.namelist()), SHARE_FILES)
                self.assertEqual(len(package.namelist()), len(SHARE_FILES))
                for name in SHARE_FILES:
                    self.assertEqual(package.read(name), (SOURCE / Path(name).name).read_bytes())
                for name in ("Time/Time.command", "Time/Install.command"):
                    entry = package.getinfo(name)
                    self.assertEqual(entry.create_system, 3, name)
                    self.assertEqual(stat.S_IMODE(entry.external_attr >> 16), 0o755, name)

    def test_installer_preserves_config_is_idempotent_and_runs_outside_tool_directory(self):
        with tempfile.TemporaryDirectory(prefix="Time install ") as directory:
            base = Path(directory)
            tool = base / "中文 Time ' $ folder"
            tool.mkdir()
            for name in ("cli.py", "ranges.py", "Time.command", "install.py"):
                shutil.copy2(SOURCE / name, tool / name)
            shell_config = base / "shell config"
            shell_config.mkdir()
            rc = shell_config / ".zshrc"
            original = "# existing user configuration\nexport TIME_TEST_EXISTING=preserved\n"
            rc.write_text(original, encoding="utf-8")
            elsewhere = base / "other working directory"
            elsewhere.mkdir()
            environment = {**os.environ, "ZDOTDIR": str(shell_config)}
            environment.pop("PYTHONPATH", None)
            result = self.run_python(tool / "install.py", cwd=elsewhere, environment=environment)
            self.assertEqual(result.returncode, 0, result.stderr)
            installed = rc.read_text(encoding="utf-8")
            self.assertTrue(installed.startswith(original))
            self.assertEqual(installed.count("# BEGIN standalone Time"), 1)
            self.assertEqual(installed.count("# END standalone Time"), 1)
            repeat = self.run_python(tool / "install.py", cwd=elsewhere, environment=environment)
            self.assertEqual(repeat.returncode, 0, repeat.stderr)
            self.assertEqual(rc.read_text(encoding="utf-8"), installed)

            zsh = shutil.which("zsh")
            with self.subTest(shell="zsh"):
                if zsh is None:
                    self.skipTest("zsh is unavailable; installer checks still ran")
                # Use the same Python as the test runner, independent of system PATH order.
                binaries = base / "test bin"
                binaries.mkdir()
                (binaries / "python3").symlink_to(sys.executable)
                shell_environment = {
                    **environment,
                    "PATH": str(binaries) + os.pathsep + os.environ.get("PATH", ""),
                }
                invocation = "source " + shlex.quote(str(rc)) + "; Time --date 2026-10-09 --json"
                command = subprocess.run(
                    [zsh, "-f", "-c", invocation],
                    cwd=elsewhere,
                    env=shell_environment,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    timeout=10,
                    check=False,
                )
                self.assertEqual(command.returncode, 0, command.stderr)
                data = json.loads(command.stdout)
                self.assertEqual(data["date"], "2026-10-09")
                self.assertEqual(data["timezone"], "GMT+8")
                self.assertEqual(len(data["ranges"]), 5)
                self.assertEqual(data["ranges"][0]["start_ms"], 1791475200000)
                self.assertEqual(data["ranges"][0]["end_ms"], 1791561599999)

            for existing in (
                "Time() { print -r -- existing; }\n",
                "alias Time='print -r -- existing'\n",
            ):
                with self.subTest(existing=existing):
                    conflict = base / ("conflict function" if "()" in existing else "conflict alias")
                    conflict.mkdir()
                    conflicting_rc = conflict / ".zshrc"
                    conflicting_rc.write_text(original + existing, encoding="utf-8")
                    previous = conflicting_rc.read_bytes()
                    rejected = self.run_python(
                        tool / "install.py",
                        cwd=elsewhere,
                        environment={**environment, "ZDOTDIR": str(conflict)},
                    )
                    self.assertNotEqual(rejected.returncode, 0)
                    self.assertEqual(conflicting_rc.read_bytes(), previous)


if __name__ == "__main__":
    unittest.main()
