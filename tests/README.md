# 离线单元测试

`unit/` 集中公共运行能力、FILBET 业务断言及开户工具的单元测试。

```bash
npm run test:unit
npm run check
```

两条命令均不执行联网业务。统一入口 `scripts/run-unit-tests.py` 使用当前 Python 解释器，从仓库根目录发现测试；`unit/support.py` 用 pathlib 计算路径，兼容 Windows、macOS 和 Linux。临时环境和锁使用系统临时目录，不读写团队业务账号或当前业务报告。

测试导入规范模块（`qa_core`、`filbet`）；CLI 参数与退出行为另外用离线 help 或模拟失败验证。Windows 内核专属测试只在 Windows 真实执行，其他平台的模拟分支不计作 Windows 实机验收。历史 CLI/模块兼容导出保留，新增代码不依赖它们。
