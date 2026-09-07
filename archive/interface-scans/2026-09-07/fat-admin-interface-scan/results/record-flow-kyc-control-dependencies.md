# FAT KYC record-flow control and dependency inventory

Captured for the record-level interface-discovery stage. This is not a P0 result and does not change P0/P1 scope.

## Environment and ownership gate

- Environment: FAT only.
- Existing `KYC_CLIENT_*` lane is configured, but the latest read evidence shows KYC status `5` (already approved). It is not submit-ready and must not be reused to manufacture another submission.
- `REGISTER_PHONE` is not configured. A new number must first be allocated through the existing FAT provisioning rule: query the admin member list from `9000000001` upward and use the first exact non-match.
- Registration password and the FAT admin-SMS OTP lookup source are configured. No OTP or phone value may be persisted in discovery evidence.
- The configured legal test image exists at the configured local path. The image contents and uploaded object keys must not be written to repository evidence.
- Approval TOTP secret is present and configured for SHA256. Presence alone is not proof that the current code is accepted; approval must stop if the UI/API rejects the generated dynamic code. The FAT fixed admin login code must never be substituted.
- Database access is not required for the planned branch. If later used, it is read-only.

## Client KYC flow dependencies

Expected UI route: `/s-kyc-v2`, entered from the BASIC-account KYC prompt or My → Verify Now.

| Stage | Required controls/data | Expected interface candidates | Gate |
|---|---|---|---|
| Account allocation | first unused FAT test phone from the approved pool | `POST /admin/member/list` | exact non-match must be proven before registration |
| Registration/login | phone, password, same-request OTP ID/code held only in memory | `POST /member/sms`, `POST /member/register`, login endpoints | stop if registration/login business status is false |
| Before state | authenticated dedicated member | `GET /member/kyc/detail` | must be submit-ready (`kyc_status=0`) |
| Identification | ID type, front, back, selfie test image controls | `POST /member/oss/upload` | all uploads must succeed; object keys stay in memory |
| Address/work | permanent/current address, nearest branch, nature of work, source of income | `POST /member/kyc/shops` | use a branch returned by the current UI/API |
| Personal details | test first/middle/last name, gender, birthday, nationality, place of birth, test ID number | no claim until Network capture | use synthetic test values only |
| Review/submit | Check Your Information, Submit | `POST /member/kyc/insert` or `/member/kyc/v2/insert` | actual UI request decides the active version |
| After state | result page and refreshed client KYC status | `GET /member/kyc/detail` | submission success means pending review, not approval |

## Admin `/kyc` top-level controls

Static inventory and the valid page-initialization scan confirm:

- Filters: Phone Number, First Name, Middle Name, Last Name, Start Date, End Date, Registration IP, KYC status (currently Under Review).
- Buttons: Reset, Query, EKYC Config.
- Page tabs/cards: KYC, Bonus Reissue, Bonus Order Count, with approved-today and pending-review counters.
- Initialization requests: `GET /admin/kyc/approved/count`, `POST /admin/kyc/list`, plus shared admin shell requests.

## Admin record/detail candidates to prove through live UI

| UI area/action | Candidate request | Required data/control |
|---|---|---|
| Locate exact record | `POST /admin/kyc/list` | dedicated UID held in process memory; repository stores only `target_ref` |
| Row detail / drawer | `GET /admin/kyc/detail` and/or `POST /admin/kyc/details` | exact matched row only |
| eKYC config modal | `GET /admin/kyc/config/info` | open read-only first; do not save config changes in this branch |
| eKYC mutation log | `GET /admin/kyc/ekyc/log` | current record identifier from selected row |
| Record edit/update | `POST /admin/kyc/edit`, `POST /admin/kyc/update` | only the dedicated record; capture original values and recovery path |
| Approve | `POST /admin/kyc/approve` | pending dedicated UID + dynamic approval TOTP |
| Reject | `POST /admin/kyc/reject` | pending/re-submitted dedicated UID + dynamic approval TOTP and reason |
| After-state counts | `GET /admin/kyc/pending/count`, `GET /admin/kyc/approved/count` | counts are supplementary; exact UID state is authoritative |

## State-chain decision

One KYC submission cannot be both approved and rejected from the same pending state. The safe state order is:

1. create a dedicated BASIC member;
2. submit once and capture pending state;
3. inspect row detail, drawer/modal tabs, and mutation log;
4. execute one terminal review action with dynamic TOTP;
5. verify the exact UID's after state;
6. only test the opposite terminal action if the real product allows a controlled re-submit that creates a new pending review state.

If re-submit is unavailable or any business result is false, stop that branch. No later success endpoint may overwrite the failure.
