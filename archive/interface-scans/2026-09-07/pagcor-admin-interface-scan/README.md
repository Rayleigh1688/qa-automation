# FAT PAGCOR compliance admin interface scan

This is an independent discovery workspace for `admin-pagcor-fat.filbet2025.com`. It does not update shared inventory/catalog or P0/P1 scope.

The live scanner creates a fresh Playwright browser context exclusively for this admin, completes and verifies login, inventories the permission/menu tree, visits rendered routes, records DOM controls and first-party Network structure, then attempts only semantically identified read/query/detail/export/overflow interactions. Downloads are cancelled and never saved. Credentials, token, cookie, OTP, device ID, storage state, response rows and raw personal data are never serialized.

Persistent writes require current-run-owned data, a pre-recorded recovery path and a real-time business TOTP. None are inferred from ordinary page data. The FAT fixed login code is never reused as a business verification code.

Final endpoint classifications use only the repository's nine states: `ACTIVE`, `ACTIVE_FAILED`, `UNDOCUMENTED_ACTIVE`, `DOCUMENTED_REACHABLE`, `DOCUMENTED_UNVERIFIED`, `STALE`, `REPLACED_BY`, `THIRD_PARTY`, and `MISCLASSIFIED`. A documented endpoint that was not observed remains `DOCUMENTED_UNVERIFIED`; absence alone is not stale evidence.

## Local run

Credentials and any environment-specific login code are supplied only through the current process environment:

```bash
PAGCOR_ADMIN_EMAIL=<runtime-only> PAGCOR_ADMIN_PASSWORD=<runtime-only> \
node pagcor-admin-interface-scan/pagcor-admin-live-scan.mjs
node pagcor-admin-interface-scan/build-report.mjs
```

Set `PAGCOR_SCAN_HEADED=true` when a visible browser is required. After each run, verify again that results contain no credentials, login codes, Token, Cookie, device ID, response rows, or raw personal data.
