# FAT Member Detail 17-tab read-only deep scan (B lane)

- Tabs inventoried: 17/17
- UI action decisions: 72 across 14 data tabs; Details, KYC Records, and Function Limitation are DOM-inventory-only in this lane
- Action-endpoint CSV mapping rows: 76; four actions map to two endpoints each, so this is not a second action count
- Read-only operations completed: 40
- Unique admin method+paths observed: 33
- Interaction/control blocks: 18
- Targeted retries: 11
- Targeted retry evidence is merged into the final action state and is not emitted as duplicate CSV action rows
- Business writes: 0; side effects: none; UAT accessed: no
- Export discovery ends after the request/response is captured; save confirmation is not required or attempted

## Tab results

| Tab | Inventory | Completed operations | Classification | Block |
| --- | --- | ---: | --- | --- |
| Details | CONTROLS_INVENTORIED | 0 | DOCUMENTED_REACHABLE |  |
| KYC Records | CONTROLS_INVENTORIED | 0 | DOCUMENTED_REACHABLE |  |
| Function Limitation | CONTROLS_INVENTORIED | 0 | DOCUMENTED_REACHABLE |  |
| Wallet Transaction Change | CONTROLS_INVENTORIED | 2 | ACTIVE |  |
| Bet Details | CONTROLS_INVENTORIED | 2 | ACTIVE |  |
| Deposit Record | CONTROLS_INVENTORIED | 3 | ACTIVE |  |
| Withdrawal Record | CONTROLS_INVENTORIED | 3 | ACTIVE |  |
| Bonus Log | CONTROLS_INVENTORIED | 3 | ACTIVE |  |
| Turnover Detail | CONTROLS_INVENTORIED | 2 | ACTIVE |  |
| VIP Level Log | CONTROLS_INVENTORIED | 3 | ACTIVE |  |
| XP Growth Log | CONTROLS_INVENTORIED | 4 | ACTIVE |  |
| Risk Control Log | CONTROLS_INVENTORIED | 2 | ACTIVE |  |
| Login Logs (New) | CONTROLS_INVENTORIED | 4 | ACTIVE |  |
| Login Logs | CONTROLS_INVENTORIED | 4 | ACTIVE |  |
| Token Wallet Transaction | CONTROLS_INVENTORIED | 3 | ACTIVE |  |
| Daily Statistics | CONTROLS_INVENTORIED | 3 | ACTIVE |  |
| Game Stats | CONTROLS_INVENTORIED | 2 | ACTIVE |  |

Evidence details, parameter fields, HTTP/business status and response shapes are in `record-flow-member-tab-readonly-deep-scan.json`; action/endpoint rows are in `record-flow-member-tab-readonly-action-endpoint.csv`.
