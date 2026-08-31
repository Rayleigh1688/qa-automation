---
name: filbet-p0-automation
description: Maintain, execute, or diagnose this repository's FILBET P0 API/UI automation, controlled fund flow, KYC, betting, withdrawal, admin checks, and front/back data reconciliation. Do not use for unrelated generic testing advice or P1/P2 expansion.
---

# FILBET P0 Automation

Start with the repository's current truth, then load only the branch needed for the task.

## Always establish context

1. Read `../../../AI-HANDOFF.md` for current evidence, accepted environment exceptions, blockers, and the next checkpoint.
2. Read `../../../README.md` only as far as needed for global commands, safety boundaries, and artifact locations.
3. Run `git status --short`; preserve unrelated or user-owned changes.

Do not treat generated files under `api/results/`, `ui/results/`, or `ui/reports/` as long-term rules. They are only the latest execution evidence.

## Route by task

- API cases, runners, or assertions: read `../../../skills/api-testing.md`, then `../../../api/p0/README.md`. Read `../../../api/runbooks/API.md` before execution and `../../../api/runbooks/ADMIN.md` for admin APIs or approvals.
- UI or Playwright work: read `../../../skills/ui-testing.md`, then `../../../ui/README.md`. Keep selectors and click points in `ui/data/`, not test orchestration.
- Business ordering, KYC, deposit, turnover, betting, reconciliation, or withdrawal decisions: read `../../../skills/business-rules.md` and `../../../api/p0/README.md`.
- Failures or environment anomalies: open `../../../harness/README.md` and follow its router to exactly the relevant debug or known-error page.
- Scope, priority, or release-gate changes: read `../../../testing-plan/00-测试自动化总体规划.md` and the relevant numbered phase plan before editing assets.

## P0 invariants

- `api/p0/test-cases.csv` is the complete case index; `main-flow-scenarios.csv` is the eight-stage business map; `interface-shortlist.csv` is discovery input only.
- Stateful steps follow register/login → minimal KYC → deposit → UI bet → bet/payout evidence → wallet/transaction reconciliation → withdrawal → admin/report reconciliation.
- API and UI provide different evidence. Do not duplicate stable API checks in UI or claim an API-only run proves the third-party game interaction.
- Database access is read-only and diagnostic. Never change business state directly in MySQL.
- Controlled writes must use the designated lane and only act on records created by the current flow. Stop when a stage's business result is false; never call a later success endpoint to manufacture a pass.
- A positive API case requires a decodable response, expected HTTP result, business success, stable data shape, and required fields. A negative case also requires no prohibited side effect.
- Secrets, OTP/TOTP seeds, tokens, cookies, device IDs, passwords, and raw personal data belong only in ignored local configuration or CI credentials.

## Keep documentation linked

When a decision changes:

- current evidence or next action → `AI-HANDOFF.md`;
- global scope/command/safety rule → `README.md` or `testing-plan/`;
- executable P0 coverage/order → `api/p0/` assets and its README;
- execution procedure → `api/runbooks/` or `ui/README.md`;
- durable method → `skills/`;
- observed failure/environment behavior → `harness/`.

Update the narrowest authoritative file. Link to it from higher-level navigation instead of copying the same live status into multiple documents.
