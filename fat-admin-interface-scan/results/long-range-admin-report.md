# FAT admin long-range supplemental scan

- Focused pages: 28/57; unique endpoints: 28; new vs main: 0.
- Page results: {"ACTIVE_FAILED": 1, "EMPTY_TO_MAX_OBSERVED_RANGE": 1, "NON_EMPTY": 24, "UI_DATE_INPUT_BLOCKED": 1, "UNVERIFIED_LONG_RANGE": 1}.
- Business query requests: 47; successful: 46.
- This is additive evidence only and does not change the 109-endpoint main scan count.

## Exceptions

- VIP Rewards `/member-management/vip-rewards`: EMPTY_TO_MAX_OBSERVED_RANGE; ranges=7d | 30d | 90d | 365d | page_max_observed;
- Daily Report `/operations/daily-reports`: ACTIVE_FAILED; ranges=7d | 30d | 90d; business failure at 90d; retained without a later success override
- Temporary Restriction List `/risk-control/temporary-restriction-list`: UI_DATE_INPUT_BLOCKED; ranges=7d; date control rejected target value; query not clicked
- Betting Record `/game/bet-orders`: UNVERIFIED_LONG_RANGE; ranges=7d | 30d | 90d | 365d | page_max_observed; QUERY_NOT_TRIGGERED_AFTER_7D: only the 7d empty response is verified; 30/90/365/max are unverified

## Evidence

- `long-range-page-summary.csv`
- `long-range-page-action-endpoint.csv`
- `long-range-endpoint-summary.csv`
- Raw: `long-range-admin-results.json`, `long-range-admin-retry-results.json`
