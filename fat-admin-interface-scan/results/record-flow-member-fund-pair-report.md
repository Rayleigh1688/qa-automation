# FAT Member Detail Fund Pair Result

- Target: `FAT-KYC-REJECT-01` / `FAT-UID-KYC-REJECT-01` (repository-safe references only)
- Wallet Credit/Debit: **EXECUTED_RESTORED**; `0 → 0.01 → 0`; two confirmed successful UI writes.
- Wallet endpoint: `POST /admin/finance/adjust/insert`; verification: `POST /admin/finance/adjust/list` plus detail/wallet reread.
- Token Top-Up/Withdrawal: **BLOCKED_UPSTREAM_BUSINESS_FAILURE**; `POST /admin/finance/tokens/transaction/list` returned HTTP 200 / business false. No token adjustment request or side effect occurred.
- Final state: wallet restored to the original value; token balance unchanged.

The first Credit attempt was stopped by a front-end validation requiring **Turnover Venue/Game Restrictions**. A read-only form probe identified the dynamic tree and its `所有游戏` (All Games) option. The single permitted retry selected it and succeeded. The matching Debit form omitted Credit-only turnover fields; after correcting that UI-field assumption, the recovery request succeeded.
