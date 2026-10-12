#!/bin/zsh
# Locate only this package's files; no repository or Node dependency.
time_tool_dir="${0:A:h}"
time_tool_target=cli.py
time_tool_pause=0
if (( $# == 0 )); then
  time_tool_pause=1
elif [[ "$1" == --no-pause ]]; then
  shift
elif [[ "$1" == --install ]]; then
  time_tool_target=install.py
  time_tool_pause=1
  shift
fi

time_tool_exit=0
if ! command -v python3 >/dev/null 2>&1; then
  print -u2 -- '需要 Python 3.10 或更新版本；安装后再打开此工具。'
  time_tool_exit=2
elif ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
  print -u2 -- '当前 python3 版本过低，需要 Python 3.10 或更新版本。'
  time_tool_exit=2
else
  python3 "$time_tool_dir/$time_tool_target" "$@"
  time_tool_exit=$?
fi

if (( time_tool_pause )) && [[ -t 0 && -t 1 ]]; then
  read -r '?按回车关闭…'
fi
exit "$time_tool_exit"
