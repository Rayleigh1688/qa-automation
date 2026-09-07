# FAT PAGCOR compliance admin scan report

- Login gate: **PASS**. Actual origin `https://admin-pagcor-fat.filbet2025.com`; authenticated hash route `/#/reportCenter/pagcor`.
- Evidence: successful `POST /cmpl/login`, successful `GET /cmpl/me/detail`, authenticated business-page initialization, and rendered navigation.
- Session isolation: a fresh PAGCOR-only Playwright context was used; storage state was not exported and the token remained in memory only.
- Navigation: one rendered top-navigation entry (报表中心 → `/#/reportCenter/pagcor`). This application has no traditional sidebar menu items; none are claimed as verified.
- Permission tree: 63 PIDs queried, 63/63 successful responses, 62 returned permission nodes. `GET /cmpl/priv/list` is `DOCUMENTED_REACHABLE`, not UI-active.
- Page coverage: 1/1 rendered route; 32 DOM control/table snapshots; 15 safe actions; 33 first-party Network events.
- Dynamic endpoints: 5 unique, all ACTIVE. Static comparison: ACTIVE 5, DOCUMENTED_REACHABLE 1, DOCUMENTED_UNVERIFIED 65.
- Filters/query: five visible selectors each selected its first legal option; Search, Today, Yesterday, This Week, This Month, Last Month, Reset, and a final Search were exercised. Date before/after values are retained as non-personal state evidence.
- Export: clicked once; no Network or download event occurred, so the action is `CLICKED_NO_INTERFACE_EVIDENCE`. No file was saved.
- Not visible in the current DOM: second page, detail entry, modal, drawer, and Overflow. These are not reported as failed or stale.
- Persistent writes: 0. No current-run-owned target or real-time business TOTP was available; fixed login codes were not used for business operations.
- Privacy audit: credentials, token, cookies, OTP/TOTP, device ID, response rows, and raw personal data are not serialized.

Unobserved documented endpoints remain `DOCUMENTED_UNVERIFIED`; absence is not treated as `STALE`.
