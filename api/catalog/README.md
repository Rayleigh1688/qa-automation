# API 分类目录

本目录由 `scripts/build-api-catalog.py` 从 `api/inventory/interfaces.csv` 自动生成，只用于检索；不要手工维护，也不替代 `api/p0/test-cases.csv`。

## 调用端

| 调用端 | 接口数 | 文件 |
|---|---:|---|
| admin | 587 | [`admin.csv`](admin.csv) |
| client | 176 | [`client.csv`](client.csv) |
| unknown | 93 | [`unknown.csv`](unknown.csv) |
| agency | 55 | [`agency.csv`](agency.csv) |

## 管理后台模块

| 模块 | 接口数 | 文件 |
|---|---:|---|
| other | 205 | [`admin/other.csv`](admin/other.csv) |
| game | 91 | [`admin/game.csv`](admin/game.csv) |
| finance | 89 | [`admin/finance.csv`](admin/finance.csv) |
| promo | 56 | [`admin/promo.csv`](admin/promo.csv) |
| report | 43 | [`admin/report.csv`](admin/report.csv) |
| auth | 34 | [`admin/auth.csv`](admin/auth.csv) |
| member | 26 | [`admin/member.csv`](admin/member.csv) |
| kyc | 23 | [`admin/kyc.csv`](admin/kyc.csv) |
| permission | 20 | [`admin/permission.csv`](admin/permission.csv) |

## 维护规则

- `surface` 表示调用端：client、admin、agency 或 unknown。
- `module` 表示业务模块：auth、member、kyc、finance、game、permission、report、promo 或 other。
- P0 执行顺序仍由 `api/p0/test-cases.csv` 与 `main-flow-scenarios.csv` 决定。
- 重新扫描 Bruno 后依次运行 `build-p0-shortlist.py`、`build-p0-test-cases.py` 和本脚本。
