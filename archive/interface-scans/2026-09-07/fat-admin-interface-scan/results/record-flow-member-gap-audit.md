# FAT Member list / Member Detail gap audit

> 2026-09-03 completion update: the Member-list Batch/filter/pagination/row-entry pass and all 17 detail-tab internal read operations are now complete. Turnover adjustment completed `0 → 1 → 0`; `add` and `sub` are `ACTIVE`, while `clear` remains `DOCUMENTED_UNVERIFIED`. Use `member-list-a-report.md`, `record-flow-member-tab-readonly-deep-scan.md`, `record-flow-member-write-summary.json`, and `member-gap-merged-report.md` as the newer truth for completed items below.

This is a read-only audit of existing repository evidence. It did not log in to any backend, send business requests, or modify business data, shared inventory, catalog, README, or AI-HANDOFF.

## Outcome

- All 17 Member Detail tabs have been opened, but that proves only tab initialization. Secondary buttons, exports, filter combinations, and pagination inside those tabs are not fully covered.
- All 11 registered safe detail-page entry actions have been opened.
- The current record-flow read asset has 48 mappings and 30 unique endpoints. The write asset has 24 mappings and 11 unique triggered endpoints.
- The largest remaining value is not opening more top-level tabs. It is executing the nested controls already visible inside those tabs and completing bounded reversible write pairs.

## Classification corrections needed at final merge

| Actual request | Current label | Recommended label | Reason |
| --- | --- | --- | --- |
| `POST /admin/member/list` | `UNDOCUMENTED_ACTIVE` | `MISCLASSIFIED` | Inventory has the same path as GET; FAT UI uses POST with a CBOR body. |
| `POST /admin/finance/tokens/transaction/list` | `UNDOCUMENTED_ACTIVE` | `MISCLASSIFIED` | Inventory has the same path as GET; Member Detail uses POST. |
| Old member control/prerequisite matrices | several blocked states | internal stale evidence | Newer assets prove Risk Control was restored and Convert to Agent was executed. |

Use `record-flow-member-write-action-endpoint.csv` as the newer write-state truth. Do not delete the older files during scanning; simply avoid deriving current status from them.

## Recommended next execution order

1. Complete Member-list Batch query, representative filter values, page 2/page-size change, and Export. Expected data endpoint is `POST /admin/member/list`; export candidate is `GET /admin/member/export`.
2. Submit Add Member once with a newly allocated synthetic account to create one more dedicated state lane. Candidate: `POST /admin/member/insert`.
3. Execute a small Credit followed by the same Debit, checking wallet and adjustment ledger after both. Candidates: `POST /admin/finance/adjust/insert`, `POST /admin/finance/adjust/list`, `GET /admin/finance/member/wallet`.
4. Execute a small Token Top-Up followed by the same Token Withdrawal. Candidates: `POST /admin/finance/tokens/adjust` and `POST /admin/finance/tokens/transaction/list`.
5. On one explicitly selected game, increase turnover by a small amount, verify, deduct the same amount, and verify restoration. Candidates: `POST /admin/finance/turnover/add`, `/sub`, plus `GET /admin/finance/turnover/list`.
6. Open Turnover Detail → 异动记录 after step 5. Candidates: `GET /admin/finance/turnover/change/types` and `/change/list`.
7. For the Withdraw limitation whose saved baseline is Forbidden, run Unlock → verify Allowed → Lock → verify the original Forbidden baseline through `/admin/member/limitation/state/update` and `/state/info`.
8. Map and, only if reversible, execute Risk Control Log → Risk Control Adjustment. Candidate write endpoint is `POST /admin/member/risk/update`; it is distinct from Details-page Risk Control, which already used `POST /admin/member/update`.
9. Execute exports from Deposit, Withdrawal, Bonus, XP, Token Wallet, Daily Statistics, Login Logs (New), and Login Logs. Keep a bounded current-run UID/date filter and do not preserve downloaded member rows.
10. Treat Manual Adjust VIP and Reset Password as terminal member actions. Defer inviter/agent transfer until ordinary Member coverage is finished, because the user has identified that subsystem as needing repair and the recovery relationship is not yet proven.
11. Execute Clear/Reset operations last and only on turnover or token requirements created by this flow.

## Visible nested controls still missing Network proof

| Page / tab | Visible control | Candidate endpoint(s) | Gate |
| --- | --- | --- | --- |
| Member list | Export | `GET /admin/member/export` | Bounded synthetic filter; discard downloaded data after structure check |
| Member list | Batch query / filter families / pagination | `POST /admin/member/list` | Use only current-run identifiers and UI-provided enum values |
| Member list | Add Member | `POST /admin/member/insert` | Dedicated synthetic identity and captured created target reference |
| Balance | Credit or Debit | `POST /admin/finance/adjust/insert` | Small Credit→Debit pair, approval TOTP, wallet/ledger reconciliation |
| Token Wallet Transaction | Token Top-Up and Withdrawal | `POST /admin/finance/tokens/adjust` | Small top-up→withdraw pair; avoid Reset/Clear until last |
| Remaining Turnover Requirement | 增加 / 扣除 / 清零 | `/admin/finance/turnover/add`, `/sub`, `/clear` | One current-run game requirement; add→sub first, clear last |
| Turnover Detail | 异动记录 | `/admin/finance/turnover/change/types`, `/change/list` | Prefer non-empty current-run turnover changes |
| Risk Control Log | Risk Control Adjustment | `POST /admin/member/risk/update` | Exact before value and deterministic restore option |
| VIP Level Log | Manual Adjust VIP | `POST /admin/member/vip/level/manual/upgrade` | Upgrade-only candidate; use a terminal lane unless downgrade is proven |
| Bonus Log | Approved Order Count | likely `GET /admin/bonus/list` with a preset | Click once to learn semantics; do not invent a count endpoint |
| Security / Member row | Reset Password | `POST /admin/member/update/password` | Terminal lane and legal member verification code |
| Member row | Transfer | `POST /admin/promo/invite/friends/transfer` | Valid current-run inviter relationship |
| Detail Referrer ID | changed / 转移代理线 | `GET /admin/superior/one`, `POST /admin/superior/update` | Capture and restore original upline if the UI supports it |
| Free-spin record modal | Conditional row state control | `POST /admin/member/buyfeature/state/set` | Only if a current-run free-spin purchase exists |
| Wallet Transaction Change | Clear Turnover Requirement | `/admin/member/turnover/clear` or `/admin/finance/turnover/clear` | Control was absent on current lane; selected source data must be current-run-owned |
| Detail field pencil icons | Contextual field edit | likely `POST /admin/member/update` | Locate by surrounding label, not ordinal/coordinates; restore immediately |

## Export candidates

- Deposit Record: `POST /admin/finance/deposit/export`
- Withdrawal Record: `POST /admin/finance/withdraw/export`
- Bonus Log: `GET /admin/bonus/export`
- XP Growth Log: `GET /admin/vip/xp/export`
- Token Wallet Transaction: `GET /admin/finance/tokens/transaction/export`
- Daily Statistics: `GET /admin/reports/member/export`
- Login Logs: bundle candidate `GET /admin/log/export`; mark active only after actual Network proof because it is absent from inventory.

## Parameter-coverage gap

The initialization endpoints for transaction, bet, deposit, withdrawal, bonus, turnover, VIP, XP, risk, login, token, daily-statistics, and game-statistics tabs are already active. Their Query/Reset/filter/pagination paths still need one meaningful UI-driven combination each. This work enriches parameter origin and response-shape evidence; it should not inflate the unique-interface count.

## Already complete; do not repeat for appearance

- Member Detail visible data composition: `/admin/member/detail`, `/admin/kyc/detail`, `/admin/finance/member/wallet`.
- 17/17 tab initialization and 11/11 safe detail entries.
- Bet and Login limitation reversible branches.
- Details-page Risk Control and restoration.
- Convert to Agent on the terminal lane.
- Recharge-rate operation log; the Custom update is already correctly recorded as HTTP 200 / business failure with no side effect.
- Turnover game tree: 7 categories, 72 category/provider combinations, 5,731 games.

No UID, phone number, credential, token, cookie, or OTP is stored in this audit.
