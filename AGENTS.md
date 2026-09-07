# 仓库维护入口

- 开始前检查 `git status --short`，保留用户已有修改；当前证据与下一步见 [AI-HANDOFF.md](AI-HANDOFF.md)。
- 业务任务使用 [.agents/skills/filbet-p0-automation/SKILL.md](.agents/skills/filbet-p0-automation/SKILL.md) 按需加载资料。文档也需要核对；冲突应结合代码、已验证证据与用户最新决定修正。
- 文档职责与目录依赖见 [架构说明](docs/architecture.md)，命令范围见 [命令说明](docs/commands.md)。不要在多个入口复制实时通过率。
- 保持现有 npm/CLI 入口和报告路径兼容。共享能力抽取到可导入模块，CLI 负责参数和编排。
- 本地校验运行 `npm run check`；只改文档可先运行 `npm run check:docs`。联网 API/UI 门禁会登录系统，受控命令还会写业务数据，不作为文档修改的默认验证。
- 业务失败不能通过继续调用成功接口制造通过；数据库只读。凭据、证件、token 和未脱敏个人资料不提交。
- 完成后说明改动、实际验证及未验证边界，并同步当前交接；历史证据保持日期和来源。

- 新需求设计从 [requirements/README.md](requirements/README.md) 进入；扫描历史只从 [归档索引](archive/interface-scans/README.md) 按需查阅，不将历史专项脚本当作当前门禁。
