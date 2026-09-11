# 跨项目运行核心

这份说明随源码导出，可独立用于新项目。核心要求 Python 3.10+，仅使用标准库；Node 启动器需要本机 Node，Playwright 由目标项目自行安装。推荐团队统一 Python 3.12。导出是源码快照，不是已发布的 pip/npm 包，也不会自动同步后续修复。

## 能力与边界

| 能力 | 入口 | 新项目需要提供 |
| --- | --- | --- |
| 环境文件分层 | `qa_core.environment.load_environment` | 基础文件路径；可选 QA_ENV_LOCAL 和 ENV_FILE_PRECEDENCE |
| Python 解释器选择 | `scripts/python-launcher.mjs` | 本机 .venv 或 QA_PYTHON_EXECUTABLE；不复制其他电脑的 venv |
| 跨平台命令 | `qa_core.process.run_process` | argv 数组；可显式传 project_root、cwd、env |
| 串行工作流 | `qa_core.workflow.run_stages` | 阶段 argv 数组、project_root、项目锁 namespace |
| 同机互斥 | `qa_core.local_lock.local_run_lock` | 项目 namespace，或显式锁文件路径 |
| CBOR/JSON | `qa_core.codec` | 请求/响应字节；只支持现有协议子集，需核对新服务契约 |
| 终端样式 | `qa_core.terminal` | 状态和文字；TTY/NO_COLOR 行为保留 |
| HTML/Markdown 展示 | `qa_core.reporting` | 标题、状态、条目、输出文件及证据；默认中文/UTC+8 展示约定需核对 |
| 日志脱敏 | `qa_core.redaction` | 调用者提供环境值或敏感参数集合，不自动加载凭据 |
| 嵌套字段 | `qa_core.values` | 字典路径读取与存在性判断，区分缺失字段和显式null |

导出不包含 FILBET 业务包、接口路由/时间契约、账号、环境文件、Jira 需求、页面定位器、图像识别阈值、资金恢复逻辑、业务清理器或当前报告。doctor 的账号与环境检查、CI 凭据、用例标签和报告判定必须由新项目实现；不能把现有业务 PASS 规则当作新项目验收规则。报告函数负责展示，调用者负责状态可信、脱敏及证据关联。资金链默认文案留在源仓库的 filbet/reporting.py，不进入导出核心；新项目可传 evidence 的 images_title/image_note/checks_title，layout（default/ui/gallery）和 generated_at 字符串选择展示。

## 从当前仓库导出

在源仓库运行下面命令，目标必须是尚不存在的新目录：

```bash
node scripts/python-launcher.mjs scripts/export-runtime.py --out ../new-project-runtime
```

只复制显式白名单中的公共 Python 文件、两个 Node 启动文件与本说明，同时生成 `runtime-manifest.json` 的逐文件 SHA256。不会遍历或复制配置、node_modules、测试结果或归档，不安装依赖、不运行测试、不触发业务。已存在目标会拒绝覆盖；导出中途遇文件系统错误应检查并移除该次不完整目标后重新导出到新目录。

导出工具留在源仓库，更新时从源仓库重新导出、核对清单及差异，在目标项目回归后采用；不要直接覆盖目标项目的修改。

## 新项目接入

保留 `scripts/qa_core/` 与两个 `.mjs` 文件的相对位置。每台电脑重新创建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
$env:QA_PYTHON_EXECUTABLE = (Resolve-Path .\.venv\Scripts\python.exe).Path
```

新建 `scripts/run-checks.py`，下面示例仅打印本地解释器版本，不联网：

```python
from pathlib import Path
import sys
from qa_core.workflow import run_stages

ROOT = Path(__file__).resolve().parents[1]

if __name__ == '__main__':
    sys.exit(run_stages(
        [['python', '-c', 'import sys; print(sys.version)']],
        project_root=ROOT,
        namespace='new-project',
    ))
```

运行：

```bash
node scripts/python-launcher.mjs scripts/run-checks.py
```

随后在新项目 package.json 中将该 Node 命令映射成项目自己的 npm 入口。不要复制 FILBET 的 package.json 或业务命令清单。脚本中的配置文件路径、报告路径均由新项目自己定义；核心不会自动清理业务产物。

## 参数与兼容约定

- `run_stages` 在执行任何阶段前验证全部命令结构，获取一个锁覆盖全部阶段；非零退出立即停止，返回实际退出码。`extra_args` 只追加到最后阶段，输入列表不被修改。开头的 `NAME=value` 仅覆盖该阶段环境，不执行 shell 插值。
- Python 子进程使用当前 `sys.executable`，并传递 QA_PYTHON_EXECUTABLE 给 Node 子流程。新项目需使用本机路径，不在变量值中放引号或额外参数。
- `project_root` 决定本地 Playwright CLI 位置；`run_stages` 同时使用它作为 cwd。独立 `run_process` 的 project_root 只影响命令解析，cwd 需自行传入。不指定 root 时保留 scripts/qa_core 布局推导，若改安装布局必须显式传入。
- Windows npm 使用有效的 npm_execpath 或 Node 旁的 npm CLI；Playwright 使用目标项目本地 CLI，不通过 npx 下载。目标 env 中的 PATH/npm_execpath 用于解析。
- namespace 为 1–64 个字母、数字、下划线或连字符，首字符为字母或数字；不含路径。不同项目用不同 namespace，同项目多个 checkout 用同一 namespace。同机、同用户、同临时目录才共享锁，不提供跨机器隔离。原 FILBET 默认仍为 qa-automation，旧锁路径及 token 兼容。
- 运行环境与锁 token 使用进程环境，因此工作流用于主线程串行执行，不承诺同一 Python 进程内多线程调度。QA_LOCAL_LOCK_TOKEN 为内部变量，不手工设置。
- Windows 使用 Job Object，POSIX 使用独立进程组；正常退出、失败和可捕获中断都清理所启动的后代。强杀/系统崩溃及清理异常的边界仍需目标项目核验，不能仅靠锁可用判断无残留。

## 接入验收

先做离线验证：本机虚拟环境选择、中文/空格路径、参数字面值、第二阶段失败停止、同项目锁竞争和嵌套、不同项目锁隔离、退出/中断后的后代清理。再按新项目的明确环境和授权验证 API/UI，不通过导出脚本自动执行。

当前导出核心在 macOS 以独立临时项目测试。原项目已有用户反馈 Windows 正常跑通；新封装及新项目 Windows/Linux 仍需各自回归，不能由旧反馈或模拟测试代替实机验收。

新需求通用导出另包含`case_report.py`、`execution_plan.py`和`plan_runner.py`：调用者提供服务/账号元数据和固定方法注册表，公共层不登录、不导入FILBET。实际业务adapter自行提供，导出不包含ISOP用例或本机证据。

`qa_core/case_catalogue.py`提供离线业务总表/API数据视图，包含在公共导出中；调用者传入设计文件、Story和执行资产。它只生成审阅CSV并验证Case引用，不执行业务、不修改源JSON或人工执行结果。项目CLI不随公共核心导出。
