# FAT member record-flow discovery

- Detail tabs: 17/17 opened read-only; safe detail entries: 11/11.
- Action/endpoint mappings: 48; unique endpoints: 30; new vs 109-endpoint main scan: 13.
- Add Member opened for DOM inventory only; it was not submitted. Required markers: Account, Email, Phone Number.
- Arbitrary existing member data was used only for read-only structure evidence. Controlled writes were limited to the current-run target; no raw UID/member values were persisted.
- Current-run target list/detail correlation: True/True; KYC status=5.
- Controlled writes: 2 requests; restored flows: 1; unrestored side effects: 0.
- Deposit Function Limitation completed Allowed → Forbidden → Allowed through the same exact row and real approval TOTP. Irreversible/high-risk actions remain blocked.

## Outputs

- `record-flow-member-action-endpoint.csv`
- `record-flow-member-control-matrix.csv`
- `record-flow-member-add-form.csv`
- `record-flow-member-write-prerequisites.csv`
- `record-flow-member-summary.json`
