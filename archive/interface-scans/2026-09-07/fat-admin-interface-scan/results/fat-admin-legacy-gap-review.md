# FAT first-pass gap review

This review is generated from redacted repository evidence. It sends no request and does not change business data.

- Safe skips reviewed: 184
- Interaction errors reviewed: 6
- Legacy write blockers reviewed: 60
- Pages proven unused: 0. Every reviewed page is in the live 57-route menu evidence, so no row is marked STALE merely because the first pass did not trigger Network.
- Root causes: {'CURRENT_STATE_NOT_VISIBLE': 1, 'MISSING_LEGAL_DATA': 60, 'STRICT_LOCATOR_PROBLEM': 189}

The six interaction errors are strict-locator/overlay failures. Safe skips marked not actionable or not in filter context are scanner-safety gaps, not endpoint failures. The single no-option row is current-state dependent. Write blockers remain missing-legal-data findings unless newer controlled-flow evidence supersedes them.

Known method/classification drift remains `POST /admin/member/list` versus documented GET and `POST /admin/finance/tokens/transaction/list` versus documented GET; both use `MISCLASSIFIED`.
