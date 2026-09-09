# 团队本地运行

本手册负责个人配置、凭据交付、doctor 和本机互斥；业务环境差异见 [环境手册](../api/runbooks/ENVIRONMENTS.md)，执行范围见 [命令说明](commands.md)。本轮不接入 CI 或测试平台。

## Python 虚拟环境与 Windows

每台电脑自行创建 `.venv`（已被 Git 忽略），不要复制其他电脑的环境目录。团队建议统一 Python 3.12；代码要求 Python 3.10+。当前核心 runner 仅使用标准库，没有额外 pip 依赖；Node/Playwright 仍由 `npm ci` 根据 `package-lock.json` 安装，MySQL、ImageMagick、Tesseract 是独立系统工具。

Mac/Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
npm run check
```

Windows PowerShell：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
npm run check
```

若 PowerShell 策略禁止激活脚本，不必修改系统策略；在当前终端显式选择解释器即可：

```powershell
$env:QA_PYTHON_EXECUTABLE = (Resolve-Path .\.venv\Scripts\python.exe).Path
npm run check
```

Windows cmd 可用 `.venv\Scripts\activate.bat` 激活。npm 启动器依次使用显式 `QA_PYTHON_EXECUTABLE`、已激活的 `VIRTUAL_ENV`，否则探测系统 Python（Windows 为 `py -3` / `python` / `python3`，Mac/Linux 为 `python3` / `python`）。虚拟环境选择失败时停止，不静默切换到系统解释器。Python 子脚本使用 `sys.executable`；Python → Node → Python 通过内部解释器路径沿用同一环境。直接 CLI 应使用虚拟环境中的 `python`。

Windows 配置示例（模板只在文件尚不存在时复制，勿覆盖已有凭据）：

```powershell
Copy-Item config/environments/fat.env.example .env.fat
Copy-Item config/environments/personal.env.example .env.alice.fat.local
$env:QA_ENV_LOCAL = '.env.alice.fat.local'
$env:ENV_FILE = '.env.fat'
npm run doctor
```

其他手册的 `ENV_FILE=... npm run ...` 为 POSIX shell 写法；PowerShell 用 `$env:ENV_FILE = '...'`，cmd 用 `set "ENV_FILE=..."` 后再执行 npm。Windows 不执行 `chmod 600`，请在文件属性 → 安全中核对 ACL；doctor 检查可读性和 Git 跟踪状态，但不自动验证 Windows ACL，也不将 Unix 权限位当作 Windows 权限错误。

npm 的业务命令映射集中在 `config/local-commands.json`，使用参数数组串行执行，保留原命令、开关和报告路径；不依赖 `/bin/sh`、单引号 shell 包装或 cmd 的参数插值。Windows 嵌套 npm 通过 Node 执行 npm CLI，Playwright 通过 Node 执行已安装的本地 CLI，不调用 `.cmd` 或触发 npx 自动下载。旧 `run-local.py --shell` 仅兼容仓库原有的命令及 ` && ` 串联语法，不是通用 shell；带空格路径及任意参数优先使用 `run:local --`。

虚拟环境不替代平台适配：Windows 没有 `fcntl`、`/bin/sh` 或 POSIX 进程组。本次用户 Traceback 确认 `fcntl` 导入阻断入口；原 `stage=clean` 是否另有解释器故障尚未复现。

## 初始化与个人配置

```bash
npm ci
npx playwright install chromium
cp config/environments/fat.env.example .env.fat
cp config/environments/uat.env.example .env.uat
cp config/environments/personal.env.example .env.alice.fat.local
chmod 600 .env.fat .env.uat .env.alice.fat.local
```

只准备实际使用的环境即可。两份模板使用 [.env.example](../.env.example) 的同一组变量；URL 是不可执行的示例地址，须从团队环境登记处取得实际 FAT/UAT 地址，不能跨环境混用。FAT 默认密码登录；UAT 模板使用动态短信与后台 TOTP，不能复制 FAT 固定码到 UAT。个人配置示例中的 alice 换成执行者标识。

通过团队批准的凭据渠道领取测试账号及后台登录/审批凭据，在本地编辑被 Git 忽略的文件；不要通过 Git、截图、报告或终端参数传递密码、seed、OTP、token、证件或个人资料。`chmod 600` 限制当前系统用户读取；doctor 检查权限及配置是否已受版本控制，不输出值。KYC 仅用本地受控测试素材。

```bash
QA_ENV_LOCAL=.env.alice.fat.local npm run doctor -- --env .env.fat
QA_ENV_LOCAL=.env.alice.fat.local ENV_FILE=.env.fat npm run test:ui:p0
```

加载顺序：进程环境 → `--env` / `ENV_FILE` 指定的基础文件 → 显式 `QA_ENV_LOCAL` 个人文件，后者覆盖前者。设置 `ENV_FILE_PRECEDENCE=shell` 时，已有进程变量拥有最高优先级，供父流程传递本轮账号及专项开关。个人文件中的空值也会覆盖基础文件；不想覆盖就删除该行。文件只解析 `KEY=value`，不执行 shell、不展开变量，不支持用 `${WRITE_CLIENT_PHONE}` 引用其他变量。

不设置 `QA_ENV_LOCAL` 时保持原默认环境和报告路径；个人文件不存在则停止，不默默回退到共享账号。Python API/full/default UI 与公共 smoke loader、JS 公共 UI loader 使用一致分层。当前流水 runner、TOTP 检查与会话导入/导出也复用该加载器；归档脚本不承诺个人覆盖兼容。

旧 `test:ui:business:fat` 继续固定 `.env.ui-p0.fat` 和原写入参数；需要该命令时从 FAT 模板另复制 `.env.ui-p0.fat`，再叠加同环境个人配置。不根据个人文件名自动切换业务环境。

## 账号分配

| lane / 变量 | 用途与责任 |
| --- | --- |
| `QA_OPERATOR` | 本地执行者标识；不作为锁名，不影响默认旧配置运行。business doctor 要求填写。 |
| `CLIENT_*` | 成熟只读/默认页面账号；同号登录可能使其他会话失效，团队应避免并发使用。 |
| `WRITE_CLIENT_*`、`CLIENT_WALLET_PASSWORD` | 团队按执行者、按 FAT/UAT 分配专用资金号。BET/WITHDRAW 必须同步填写同一资金号及密码；旧底层命令的空值回退并不完全一致。不得通过个人文件偷偷更换他人资金号。 |
| `KYC_CLIENT_*`、`REGISTER_*` | 每轮独立新号。UI 业务新运行使用 `--new-kyc-account`；单独 KYC 或旧 full 命令前先准备并配置本轮新号。已经提交/审核的号不能当作下轮新号。受限同轮续跑遵循原检查点规则。 |
| `PRE_KYC_CLIENT_*` | 永久 BASIC，禁止提交 KYC、设置钱包密码或作为资金号。 |
| `ADMIN_*` | 执行者获授权的后台账号，登录码与审批 seed 分开配置；审批必须使用实时 TOTP。 |

团队在受限的账号登记处维护环境、执行者、资金 lane 和占用情况；仓库只保存变量与用途，不存实际账号清单。本地 doctor 比较 lane 冲突和别名，不能证明账号刚注册、BASIC 状态、后台权限、钱包余额、提款账户或跨机器分配唯一性。这些仍由实际执行前置及团队账号管理验证。

## doctor

```bash
npm run doctor -- --env .env.fat --target api
npm run doctor -- --env .env.uat --target ui
QA_ENV_LOCAL=.env.alice.fat.local npm run doctor -- --env .env.ui-p0.fat --target business
# 显式联网：仅无认证 HTTPS HEAD 连通性，不登录、不调用业务接口
npm run doctor -- --env .env.fat --network
```

默认 target 为 ui（包含 API safe 与默认 UI 的现有本地 preflight）。检查配置可读性、权限、占位符、URL/scope、认证来源、lane 冲突、执行器依赖、本地 Chromium 及锁；business 额外检查新号密码、资金/BASIC lane、钱包密码、素材路径、审批 seed、ImageMagick/Tesseract 英文数据。不会安装依赖、创建账号、发短信、登录或改写业务报告。失败退出码 1；按变量名和修复提示补齐后重跑。

只有 `--network` 且本地检查全部通过才探测三个配置地址；保留 TLS 验证、不跟随重定向，不传凭据或读取/输出正文。重定向、401/403/405 只视为 HTTPS 服务可达，不证明认证或业务可用。doctor PASS 不能代替 `npm run check` 或真实业务验收；`test:ui:business` 的默认前置会真实登录，不能当作离线 doctor。

## 本机运行锁

所有现有业务 `test:*` npm 命令（不含 `test:unit`）、结果清理命令和 `ui:p0-points` 在启动及清理前获取公共锁，整个父子流程结束才释放；原命令名、参数、退出码和结果路径保留。不同终端/checkout/环境也串行，以避免共用账号及结果清理冲突。锁冲突退出码 2，不排队、不清理结果、不进入业务。

Mac/Linux 使用 POSIX `flock`，锁文件位于当前系统用户临时目录的 `qa-automation-<uid>.lock`，0600。Windows 使用 `msvcrt.locking` 非阻塞字节锁，文件名使用系统登录用户名摘要，元数据与锁字节分开，以允许嵌套流程读取 token；文件权限依赖用户临时目录 ACL。嵌套 npm 子流程通过本轮随机内部 token 复用锁；不要复制或手工配置 `QA_LOCAL_LOCK_TOKEN`。锁文件存在不等于占用，内核锁才是依据；不要通过删除文件解锁。Mac/Linux 在 Ctrl+C/SIGTERM 时清理包装器创建的子进程组，最多等待 3 秒后 SIGKILL。Windows 在命令放行前先把等待进程加入独立的 kill-on-close Job Object，再启动命令及浏览器后代；加入失败则停止，正常结束、失败及可捕获的 Ctrl+C/Ctrl+Break 都终止该 Job 并等待其后代退出后释放锁，不按浏览器名称批量关闭。Windows 清理为强制终止，不能保证中断时业务报告完整写入；系统直接终止进程不等同于可捕获的 POSIX SIGTERM。SIGKILL/系统崩溃无法保证后代清理，须先检查残留测试进程，不能仅凭 doctor 锁可用判断没有浏览器。

这是同机、同系统用户、相同临时目录的协作锁；不同系统用户/自定义临时目录/未包装命令不共享该保护，也不提供跨机器或服务端账号锁。不同机器仍需按执行者分配资金号。

直接调用 Python/Node/Playwright 或重建报告时，用通用包装器主动纳入保护：

```bash
npm run run:local -- python scripts/run-api-tests.py p0 --env .env.fat --safe-only
npm run run:local -- python scripts/render-ui-business-report.py
```

直接运行未包装的底层命令不会自动获取锁；不要与团队 npm 入口并行。`npm run check` / 单元测试保持离线，不占业务长锁；其中锁回归测试会短暂探测本机锁，应在无业务运行时执行。

## 终端结果颜色

doctor、API/UI 主运行入口及独立 KYC 的最终结果保留状态文字，并在支持颜色的交互终端显示：PASS 绿色，失败/阻断红色，跳过黄色，报告/日志路径青色下划线。doctor 的固定边界文字以“说明”开头，不代表失败。UI 业务入口结束时分别显示 HTML 报告和运行日志位置。

重定向到文件、管道、`TERM=dumb` 或设置 `NO_COLOR` 时自动使用纯文本；即使 `NO_COLOR` 为空也关闭颜色。颜色不写入 JSON/HTML 结果，不改变退出码或业务判定。路径是否可点击由终端支持决定。

## Windows 验收边界

2026-09-09 用户反馈拉取最新代码后 Windows 已正常跑通；该反馈未附具体命令、版本或中断清理的专项证据。本次目录重构在 macOS 做离线检查，重构后的 Windows/Linux，以及 Ctrl+C/Ctrl+Break 和浏览器后代清理仍需分别回归，不能把重构前的成功反馈扩展为全平台矩阵验收。Windows 组员应先在本地 `.venv` 运行 `npm run check`（包含隔离临时锁、嵌套、崩溃释放、参数及子进程退出测试），再运行默认离线 doctor；先处理依赖/权限问题，另行授权后才运行联网业务门禁。

可用 `npm run run:local -- python -c "import time; time.sleep(30)"` 做无业务中断实验：另一终端运行同命令应立即 BLOCKED；原终端 Ctrl+C 后应允许再次运行。浏览器清理的 Windows 实机验收需用本地空白页验证正常/失败/中断及后代退出，不需要登录或资金操作。不能以 doctor PASS 声称真实业务或跨平台验收完成。

跨项目使用时按 [运行核心复用说明](runtime-reuse.md) 设置项目根目录和独立锁 namespace；本项目仍使用原 qa-automation 锁，不因导出新项目修改已有配置。
