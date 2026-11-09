# Package 9: scanner app gym awareness

**Status:** `IMPLEMENTED_VERIFIED` for the unit-testable parts; device behavior is `IMPLEMENTED_UNTESTED`. Scanner app only (`scanner-mobile`). No backend change.

## Purpose

A scanner belongs to one gym in the database, and the backend already enforces that. Staff at the door could not tell which gym a tablet was set to and got a generic error when a member scanned at the wrong gym. This package shows the gym and explains the two gym refusals. Business goals served: G1, G6.

## What exists today (evidence)

- `POST /attendance/device/verify` returns `gym_id` and `gym_name`, and every scan response returns `gym_id`, `gym_name` and that gym's occupancy. The scanner app typed neither field and ignored them.
- Refusals: `403 MEMBERSHIP_GYM_MISMATCH` (member's home gym differs from the scanner's) and `403 ATTENDANCE_GYM_MISMATCH` (check-out at a gym other than the one holding the session). The app showed its generic "scan could not be completed" text.
- Scanner provisioning to a gym is done by the backend command `python -m app.cli.scanner_device` with a gym slug. There is no admin API or screen for it.

## Functional requirements

| ID | Requirement |
|---|---|
| FR-SCN-001 | After device verification the scanner screen shows the gym name in a prominent header. |
| FR-SCN-002 | The success result shows the gym name next to the action. |
| FR-SCN-003 | `MEMBERSHIP_GYM_MISMATCH` and `ATTENDANCE_GYM_MISMATCH` show fixed staff guidance naming the cause, never the raw server text. |
| FR-SCN-004 | The app still works against a backend that omits the gym fields (they are optional in the types and the header is hidden when absent). |

## Acceptance criteria

**AC-SCN-001** Given verification returns `gym_name`, when the scanner screen renders, then the gym name is shown in capitals. Given it is absent, then no header appears.

**AC-SCN-002** Given a scan result with `gym_name`, when the success presentation is built, then it contains the gym name; without it the value is an empty string.

**AC-SCN-003** Given each gym refusal code, when staff guidance is requested, then it returns the fixed message and not the server message.

**AC-SCN-004** Given the existing scanner tests, when run, then they still pass.

## Tasks

- **T9-01** Add `DeviceInfo` and optional gym fields to the types and the verify call (FR-SCN-001, 004).
- **T9-02** Add `gymName` to the success presentation and render the header and result label in `App.tsx` (FR-SCN-001, 002).
- **T9-03** Add guidance for the two refusal codes (FR-SCN-003).
- **T9-04** Tests for AC-SCN-001 to 004; `tsc --noEmit`.
- **T9-05** On a physical Android device with scanners provisioned to both gyms, confirm the header and the two refusals. Not done.

## Results

`npm test` in `scanner-mobile`: 15 pass (12 before this package). `tsc --noEmit`: clean. `expo lint` was not run (its config and dependencies were not set up in the verification workspace). AC-SCN-001 is covered only by code reading, since the app has no component test setup. T9-05 is not done, so nothing here has run on a device.

## Out of scope

Scanner provisioning screen or API, scanning for another gym, mobile member app (Package 10).
