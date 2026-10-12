# Time 毫秒时间戳

`Time` 输出今天、昨天、本周、本月、上月的开始和结束毫秒时间戳。固定 GMT+8，与电脑系统时区无关；周一开周，结束包含最后一毫秒 `23:59:59.999`。本周、本月包含尚未到来的日期，均为完整日历范围，不截到当前时刻。

```bash
Time
Time --date 2026-10-09
Time --json
```

仓库入口可直接使用，不需安装全局命令：

```bash
npm run qa:time
npm run qa:time -- --date 2026-10-09 --json
```

使用 Python 标准库，沿用仓库 Node/Python 启动器选择本机解释器；不联网、不读取业务配置、不登录系统或写业务数据。`ranges.py` 提供可导入的 `calculate_ranges(reference)`，CLI 只负责日期参数和展示。非法日期／参数返回非零退出码。

## 发给 Mac 用户

```bash
npm run qa:time:package
```

生成`reports/tools/Time-mac.zip`，也可加`-- --out <目标.zip>`。只打包工具、启动／安装脚本与[独立使用说明](README.txt)，不打包业务配置、仓库启动器或缓存。ZIP保留`.command`的可执行权限。

对方需已有Python **3.10+**，无需Node、npm或本仓库。完整解压后双击`Time.command`直接查看；若需在终端任意目录输入`Time`，先把文件夹放到固定位置，再双击`Install.command`并重新打开终端。没有合适的Python时显示提示，不自动安装依赖。

可选安装只向`ZDOTDIR/.zshrc`（未设置时为`~/.zshrc`）追加带`standalone Time`标记的函数；安装前检查配置中常见的`Time`函数／别名直接声明，检测到时停止，不解析间接加载的外部配置。安装使用分享包自身的绝对路径，命令不暂停；直接无参数打开`Time.command`且连接交互终端时等待回车。文件夹移动后删除旧标记块再安装，卸载仅删除该标记块。无法双击启动时可在终端使用`/bin/zsh <Time.command的路径>`。

打包、启动、中文／空格路径与隔离配置安装已在本机验证；接收者设备、其他Python版本及Finder下载后的启动行为未实测。既有本机仓库版`Time`继续沿用下面的配置，不由分享包安装覆盖。

## zsh 的 Time 命令

在 `~/.zshrc` 中添加下面函数，把 `/absolute/path/qa-automation` 替换成实际仓库的绝对路径；重新打开终端后生效。macOS 文件路径可能不区分大小写，`Time` 函数可以精确区分 `Time` 与系统 `time`。

```bash
Time() {
  node '/absolute/path/qa-automation/scripts/python-launcher.mjs' '/absolute/path/qa-automation/tools/time/cli.py' "$@"
}
```

通过 `type Time` 确认解析为 shell function；函数使用绝对路径，可以在任意目录执行。仓库移动后更新函数中的路径；不再使用时只删除此函数。本机安装情况与实际验证范围记录在[当前交接](../../AI-HANDOFF.md)，不把本机配置视作其他设备已安装。
