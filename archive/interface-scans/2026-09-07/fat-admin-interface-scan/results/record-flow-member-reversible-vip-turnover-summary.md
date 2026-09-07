# FAT Member Detail reversible VIP / turnover scan

- Environment: FAT only
- Target: `FAT-MEMBER-REV-01` / `FAT-UID-REV-01` (raw lookup values remain in the mode-0600 runtime file only)
- Page: Member Management → Member Detail
- Route: `/member-center/detail/{uid}`
- Scope: VIP manual adjustment and turnover-requirement adjustment only
- Database writes: none

## VIP result

The `VIP Level Log` overflow tab exposed `Manual Adjust VIP`. The UI offered target levels V0–V9 and a required reason. A controlled V0→V1 request and the V1→V0 recovery request both called `POST /admin/member/vip/level/manual/upgrade` with body fields `remark`, `target_level`, and `uid`; both returned HTTP 200 and business status `true`.

The first immediate detail read still showed V0. A read-only check after 12 seconds showed `vip_level=1` and one row from `GET /admin/member/vip/level/list`. The recovery request then returned the target to `vip_level=0`. This endpoint is therefore `ACTIVE`, with an asynchronously observable side effect. The exact original baseline was restored.

State closure: `vip_level 0 → 1 → 0`; `vip_manual_level` remained 0.

## Turnover result

The amount-field blocker was fixed with an exact bilingual label locator. The modal footer was independently probed before submission: it contained one cancel button and one unique primary `type=button` submit control whose whitespace-normalized text was `确定`. No coordinate or forced click was used.

The dedicated reversible member completed `left_turnover_count 0 → 1 → 0`. `POST /admin/finance/turnover/add` used body fields `amount`, `bet_multiplier`, `google_code`, `plats`, `remark`, and `uid`; it returned HTTP 200 / business `true`. The UI selected the all-games root; the final database row contains 5,731 game restriction entries. The detail endpoint then showed one remaining requirement.

The subtract branch rendered its game-restriction search input disabled and exposed no selectable tree nodes. The restore therefore filled only the live required controls: amount 1, a newly generated approval TOTP, and a recovery reason. `POST /admin/finance/turnover/sub` used body fields `amount`, `google_code`, `remark`, and `uid`; it returned HTTP 200 / business `true`. The next detail read showed `left_turnover_count=0` without needing the delayed retry.

A read-only database query matched one `fb_members_turnover` row with `ty=4`, final `state=2`, `turnover=1.00`, `finished=1.00`, `locked=0.00`, and 5,731 game entries. The add/sub endpoints are `ACTIVE`. `/admin/finance/turnover/clear` was not called and remains `DOCUMENTED_UNVERIFIED`; it was unnecessary because the exact subtract recovery succeeded.

## Evidence

- `record-flow-member-reversible-vip-adjust-probe.json`: controls and V0/V1 recovery-path proof, no writes
- `record-flow-member-reversible-vip-adjust-flow.json`: V0→V1 request and immediate stale read
- `record-flow-member-reversible-vip-adjust-final-check.json`: delayed detail V1 and VIP log count 1, no writes
- `record-flow-member-reversible-vip-adjust-restore.json`: V1→V0 recovery and restored state
- `record-flow-member-reversible-turnover-adjust-flow.json`: add/sub requests, response status, before/add/restore states, and final restoration
- `record-flow-member-reversible-turnover-submit-control-probe.json`: read-only footer button evidence
- `record-flow-member-reversible-turnover-sub-control-probe.json`: read-only subtract-branch field evidence
- `record-flow-member-reversible-turnover-db-readonly.json`: sanitized database read-only reconciliation
- `record-flow-member-turnover-game-tree.json`: previously captured read-only hierarchy reused by this run
- `record-flow-member-reversible-vip-turnover-action-endpoint.csv`: normalized action-to-interface matrix

## Data handling

Network evidence stores methods, standardized paths, field names, status, and response shape only. It does not persist request values, response member values, tokens, cookies, TOTP values, phone numbers, or raw UID. All approval codes were generated only at runtime. The dedicated temporary target file remains outside the repository with mode 0600.
