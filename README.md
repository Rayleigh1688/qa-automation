# QA Automation

这是一个用于逐步建设测试自动化体系的工作区。

## 目录结构

```text
testing-plan/    测试自动化建设规划
skills/          测试方法、规范、业务规则沉淀
harness/         调试经验、已知问题、失败分析沉淀
api/             API 自动化测试
ui/              UI 自动化测试
performance/     性能测试
scripts/         辅助脚本
```

## 当前状态

当前阶段：P0 核心自动化准备中

## 使用原则

- 先完善规划，再分阶段落地。
- 先做 P0 核心链路，再扩展 P1、P2。
- 敏感信息不提交到 Git。
- 测试账号、Token、Cookie、环境变量使用本地配置或 CI 凭据管理。
