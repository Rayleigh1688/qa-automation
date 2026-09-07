# FAT Client Interface Scan

This directory contains the independent evidence for the FAT client interface-discovery thread.

## Purpose

- Treat the real FAT UI and Network traffic as the source of truth for current usage.
- Map `page -> control/action -> normalized endpoint` before assigning P0/P1/P2 levels.
- Compare observed endpoints with `api/inventory/interfaces.csv` and `api/catalog/` without modifying those shared assets during discovery.

The page/control source list is [`../client-button-map/README.md`](../client-button-map/README.md). The cross-surface plan and classification rules are in [`../interface-discovery/README.md`](../interface-discovery/README.md).

## Outputs

- `results/fat-client-network.json`: sanitized request/response metadata. It contains field names and response shapes, not credentials or personal values.
- `results/fat-client-page-action-interface.csv`: deduplicated page/action/endpoint mapping.
- `results/fat-client-endpoint-summary.csv`: one row per unique method/origin/normalized path with linked pages and actions.
- `results/fat-client-page-progress.csv`: page and action progress, errors, and blocked scope.
- `results/fat-client-inventory-comparison.csv`: observed status for documented client endpoints; unobserved items remain `DOCUMENTED_UNVERIFIED` until reachability/staleness is separately proven.
- `results/fat-client-summary.json`: counts and classification summary.

Ordinary page screenshots, HAR files, traces, storage state, tokens, cookies, passwords, OTPs, phone numbers, device identifiers, and raw member data are not stored here.

## Execution boundaries

- FAT only; never UAT or production.
- UI interactions are used to discover actual calls, not to expand P0/P1 cases.
- FAT reads and writes are both in discovery scope. A write may only affect data created by this scan flow or explicitly designated test data.
- Before/after state and target identifiers are required for a write. Database access, if needed, is read-only.
- A failed business operation remains failed evidence; no later endpoint is called to manufacture a pass.
- Third-party game, payment, support, and download calls are classified separately.

## Run

```bash
node fat-client-interface-scan/client-playwright-scan.mjs
```

The scanner launches one Playwright Chromium process, logs in once, reuses that browser context, and walks pages in the order defined by the discovery plan.

## Known discovery anomaly

An initial explicit click on the ninth `Earn Filcoins` task button, labeled `Go`, unexpectedly emitted `GET /promo/task/daily/claim` and returned business success while the page remained on `/s-points-v2`. Because the member existed before this scan, its before state was unavailable. The event is retained as real `ACTIVE` evidence with side effect `POTENTIAL_REWARD_CLAIM`, but no before/after closure is claimed and the scanner blocks this button on subsequent runs.

For any control whose wording does not reveal whether it claims, creates, updates, deletes, or submits, inspect its DOM/link/static handler evidence before clicking. If ownership of the affected data cannot be proven, record `BLOCKED_DATA_SCOPE`.

## Current valid FAT run

The current evidence was captured on 2026-09-03 after strict route validation replaced the navigation-polluted exploratory run.

- 19 page/logical-page entries and 84 explicit actions were visited.
- 68 actions completed, 8 explicit controls were not found in the current state, 8 were blocked by test-data ownership or sensitive-evidence policy, and 1 completed action was retained as a potential-side-effect anomaly.
- 1,285 XHR/fetch requests were captured; 1,059 were first-party business requests.
- 53 unique first-party business method/path pairs were observed.
- Unique endpoint classifications: 42 `ACTIVE`, 1 `ACTIVE_FAILED`, 10 `MISCLASSIFIED`, and 7 `THIRD_PARTY`.
- The only observed business failure was `GET /promo/turntable/detail`: HTTP 200 with business `status=false`.
- Of 170 documented client method/path pairs, 42 were observed in this interaction coverage and 128 remain `DOCUMENTED_UNVERIFIED`. Unobserved does not yet mean stale.

Remaining interaction gaps are recorded, rather than hidden, in `results/fat-client-page-progress.csv`. They include the unavailable A-Z/Z-A/Popular and provider Reset/Confirm controls in the reached Game state, unavailable Adjustment/All transaction controls, and state-changing actions that require scan-owned member/order/reward data. No database write or ordinary-page screenshot was used.

## Long-range history supplement

The read-only history supplement is kept separately so it does not overwrite or inflate the primary interface count:

- `results/long-range-network.json`: sanitized selected-range response metadata.
- `results/long-range-progress.json`: supported UI ranges and pagination attempts.
- `results/long-range-page-action-interface.csv`: four page/filter/interface mappings enriched from inventory.
- `results/long-range-summary.json`: compact result and pagination evidence.

Transaction Deposit, Transaction Withdraw, Bet History, and Bonus all returned non-empty data at `Last 7 days`, so the ordered range search stopped there. The actual request contract was `time_flag=7&page=1&page_size=10`; `time_flag` is measured in days as confirmed by the UI label, and the browser timezone was `Asia/Manila`.

The page exposes `Today`, `Yesterday`, `Last 7 days`, `Last 15 days`, and `Last 30 days`. Its maximum legal UI range is therefore 30 days; 90 days, 365 days, and All Time are not offered. Deposit returned 10 of 12 records and Bet History 10 of 102 on page 1; progressive viewport scrolling emitted real `page=2&page_size=10` requests, returning 2 and 10 records respectively. Withdraw returned 9 of 9 and Bonus 2 of 2, so a second page was not requested. This supplement adds no new endpoint; it strengthens range and pagination evidence for four existing `ACTIVE` endpoints.
