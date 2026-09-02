# API 接口资产入口

接口资产按“唯一数据源 + 自动生成视图 + 唯一 P0 用例索引”管理：

```text
Bruno collection
  → api/inventory/interfaces.csv
  → api/p0/interface-shortlist.csv
  → api/p0/test-cases.csv
  → runner / report

api/inventory/interfaces.csv
  → api/catalog/（按 surface/module 检索）
```

## 文件职责

- `interfaces.csv`：全量接口唯一清单；包含 `surface`、`module`、归一化 URL 和风险标记。
- `interfaces.md`：全量扫描摘要。
- `api/catalog/`：按 client/admin/agency 和后台业务模块自动生成的只读视图。
- `api/p0/interface-shortlist.csv`：P0 候选池，不决定最终范围。
- `api/p0/test-cases.csv`：唯一 P0 用例索引，按业务主流程排序，不按前端拆分。

## 分类维度

- `surface`：client、admin、agency、unknown。
- `module`：auth、member、kyc、finance、game、permission、report、promo、other。
- `domain`：P0 业务领域；用于主流程和优先级，不代替调用端分类。

“管理后台-会员管理”表示 `surface=admin,module=member`，不是一套独立测试用例文件。

## 重新生成

```bash
python3 scripts/scan-bruno-interfaces.py
python3 scripts/build-p0-shortlist.py
python3 scripts/build-p0-test-cases.py
python3 scripts/build-api-catalog.py
python3 scripts/check-api-assets.py
```

扫描器会脱敏 URL 中的密码、token、OTP、手机号、UID、session、hash 等环境值。生成资产不得重新引入真实凭据或个人数据。
