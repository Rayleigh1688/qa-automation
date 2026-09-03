# FAT Member List A-line internal operation report

## Outcome

- Page: Member → Member List (`/member-center/list`), FAT only.
- 30 explicit controls/actions assessed: 22 executed read-only queries/pagination actions, 2 read-only row entries opened, 5 write controls blocked by data scope, and 1 Export control clicked without request/response evidence.
- Captured 135 sanitized same-origin XHR/fetch events and 12 unique method+path endpoints; no HTTP/business failures occurred in captured Network.
- Writes executed: 0. Business-data side effects: 0. No export file, raw member row, UID, phone, token, cookie, device ID, password, OTP, or TOTP was retained.

## Member-list query coverage

Individual UI-driven probes covered Phone Number, Registration IP, Superior Agent Phone, Creation Time, First Deposit Time, Last Deposit Time, Last Withdrawal Time, Deposit Count, Member Status, Agent Qualification, Account Type, Member Level, KYC Status, Restricted Status, Referrer Information, inviter presence, invitation level, and Lead Source. One text+enum combination was also submitted.

Batch query used the visible `Batch query members` overlay and its `Apply filter` button with a synthetic non-match value. It produced `POST /admin/member/list` with Body fields `page,page_size,phone,uid`, HTTP 200, business `true`, and zero records.

Pagination changed the visible page-size control from 20/page to 10/page and then opened page 2. Both actions produced successful `POST /admin/member/list` calls; page 2 returned three rows in the bounded current date window.

## Row entries and write controls

- `XP Growth Log` opened the member-detail route and triggered its read endpoints.
- `View Details` opened `/member-center/detail/{uid}`. The selected UID remained in browser memory and was not persisted.
- `Transfer`, `Risk Control`, `Reset Password`, `Convert to Agent`, and `Unblock` were not clicked: A-line had no dedicated write member, so each remains `BLOCKED_DATA_SCOPE`.

## Export

The visible Export control received one semantic click in the preceding shared-session run, but no request/response or Playwright download event was captured. It is therefore recorded as `CLICKED_NO_INTERFACE_EVIDENCE`, `trigger_status=NOT_OBSERVED`, `save_confirmation=NOT_REQUIRED_NOT_ATTEMPTED`, classification `DOCUMENTED_UNVERIFIED`. It was not retried in the final evidence run, and no native save workflow or member-data file was used.

## Method drift

The FAT UI consistently uses `POST /admin/member/list` with a CBOR Body. The inventory documents the same path as `GET /admin/member/list` with query parameters (`后台/会员列表/会员列表 - seven-double.bru`). The active UI method is therefore `MISCLASSIFIED`, not undocumented and not stale.

## Unique captured endpoints

| Method | Path | Captured result | Classification |
| --- | --- | --- | --- |
| `GET` | `/admin/channel/manage/dict` | HTTP 200/business true | `ACTIVE` |
| `GET` | `/admin/finance/member/wallet` | HTTP 200/business true | `ACTIVE` |
| `GET` | `/admin/kyc/detail` | HTTP 200/business true | `ACTIVE` |
| `GET` | `/admin/me/detail` | HTTP 200/business true | `ACTIVE` |
| `GET` | `/admin/member/detail` | HTTP 200/business true | `ACTIVE` |
| `GET` | `/admin/notify/audit/alarm` | HTTP 200/business true | `ACTIVE` |
| `GET` | `/admin/priv/check` | HTTP 200/business true | `ACTIVE` |
| `GET` | `/admin/sys/config/compliance/status` | HTTP 200/business true | `UNDOCUMENTED_ACTIVE` |
| `GET` | `/admin/vip/xp/list` | HTTP 200/business true | `ACTIVE` |
| `POST` | `/admin/game/search` | HTTP 200/business true | `ACTIVE` |
| `POST` | `/admin/gameclass/list` | HTTP 200/business true | `ACTIVE` |
| `POST` | `/admin/member/list` | HTTP 200/business true | `MISCLASSIFIED` |

## Evidence files

- `member-list-a-internal-read-scan.json`: sanitized DOM, operation ranges, Network structure, and safety assertions.
- `member-list-a-action-endpoint.csv`: one row per explicit action, including parameter origin, response structure, document mapping, current classification, evidence, and blockers.
