# FAT Admin Interface Discovery Report

Generated: 2026-09-03

## Scope and validity

- Environment: FAT only.
- Live permission roots: 12.
- Rendered sidebar pages: 57, all routes resolved from sidebar `href`.
- The earlier 30/72 bundle-route probe is invalidated and excluded.
- No UAT, Jenkins, P0/P1, shared inventory, or catalog asset was modified by this scan.

## Page and action coverage

- Page initialization: 57/57 pages, 844 redacted Network events, 78 unique method/path pairs, 0 page errors.
- Explicit controls after cleanup: 679.
- Non-write actions attempted: 615.
- Actual input/click interactions: 425.
- Safely skipped due to strict selector, page state, or non-filter context: 184.
- Control interaction errors: 6; all were select-control handling errors and did not persist data.
- Write actions: 64 total — 3 `EXECUTED`, 1 `NO_CREATE_REQUEST`, 17 `BLOCKED_PREREQUISITE`, 43 `BLOCKED_DATA_SCOPE`.

## Endpoint classification

- Unique dynamically observed endpoints: 109.
- `ACTIVE`: 89.
- `UNDOCUMENTED_ACTIVE`: 18.
- `MISCLASSIFIED`: 2.
- Two otherwise active endpoints also have a captured failure event:
  - unauthenticated login-page `GET /admin/me/detail` returned business false before login;
  - `POST /admin/game/search` returned business false for the deliberately non-matching filter combination.
- Inventory comparison: 89 `ACTIVE`, 18 `UNDOCUMENTED_ACTIVE`, 2 `MISCLASSIFIED`, 1 `DOCUMENTED_REACHABLE`, and 471 `DOCUMENTED_UNVERIFIED`.
- No endpoint is labeled `STALE` or `REPLACED_BY` without direct replacement/non-use evidence.

## Controlled write evidence

A unique current-run Marquee was absent before execution, then created, located in its table row, edited, and deleted. The following UI-triggered requests all returned HTTP 200 and business success:

- `POST /admin/marquee/add`
- `POST /admin/marquee/update`
- `POST /admin/marquee/delete`
- the associated `GET /admin/marquee/list` refreshes

The target was absent/not visible after deletion. A generic long-number redaction rule over-redacted its numeric row ID; the unique test marker and complete row lifecycle remain in evidence. This limitation is explicit and is not treated as stronger ID evidence than it is.

The Channel “Add Promotion Group” attempt produced no create request. Delayed `/admin/game/search` initialization traffic was excluded, and the action is recorded as `NO_CREATE_REQUEST`, not a success.

## Primary artifacts

- `fat-admin-live-menu-pages.csv`: authoritative menu → page → route list.
- `fat-admin-page-initialization.json`: redacted raw initialization Network and DOM controls.
- `fat-admin-explicit-actions.csv`: cleaned explicit control inventory and selector/risk classification.
- `fat-admin-page-action-interface.csv`: consolidated page → action → endpoint mapping.
- `fat-admin-endpoint-summary.csv`: unique dynamic endpoint summary.
- `fat-admin-inventory-comparison.csv`: comparison against shared inventory without modifying it.
- `fat-admin-write-action-status.csv`: all 64 write actions and their execution/block status.
- `fat-admin-final-summary.json`: machine-readable totals.
