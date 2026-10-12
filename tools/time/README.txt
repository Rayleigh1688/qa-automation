Time — Mac 毫秒时间戳小工具

需要 Python 3.10 或更新版本。无需 Node、npm、FILBET 仓库或业务账号。

最快使用：
1. 完整解压 Time-mac.zip，保留 Time 文件夹内的全部文件。
2. 双击 Time.command，显示今天、昨天、本周、本月、上月的起止毫秒时间戳。
3. 按回车关闭窗口。

想在任意目录输入 Time：
1. 将 Time 文件夹放到准备长期保留的位置。
2. 双击 Install.command。它只在当前用户的 zsh 配置末尾追加 Time 函数。
3. 重新打开终端，输入 Time。

其他用法：
Time --date 2026-10-09
Time --json
Time --date 2026-10-09 --json

固定 GMT+8，周一开周；结束时间包含最后一毫秒 23:59:59.999。
本周、本月是完整日历范围，包含尚未到来的日期。
纯离线计算，不登录、不联网，不读取业务配置。

如果双击无法启动，可在终端输入 /bin/zsh 和一个空格，
将 Time.command 拖进终端，再按回车；安装入口同样可这样打开。
如果提示 Python 版本缺失或过低，需要先安装或升级 Python 3.10+。

Install.command 保留已有配置；检测到常见的 Time 函数/别名直接声明时停止安装。
配置位置为 ZDOTDIR/.zshrc（设置了 ZDOTDIR 时），否则 ~/.zshrc。
卸载：只删除配置中的 # BEGIN standalone Time 到 # END standalone Time 标记块。
移动文件夹：删除旧标记块后，从新位置重新运行 Install.command。
不安装也可一直直接打开 Time.command。
