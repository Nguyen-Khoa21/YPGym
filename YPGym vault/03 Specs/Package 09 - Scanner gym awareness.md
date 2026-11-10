---
type: spec-package
package: 9
status: implemented-verified
date: 2026-11-10
tags:
  - spec
  - package
related:
  - "[[Package 08 - Documentation]]"
  - "[[Package 10 - Member mobile gyms]]"
  - "[[Decisions Log]]"
---

# Package 9: Scanner gym awareness

> [!info] Status
> `implemented-verified`

## Goal
The scanner tablet shows which gym it belongs to and explains the two gym refusals instead of a generic error. Scanner app only, no backend change.

Business goals: G1, G6.

## Key requirements
- Type and show `gym_id` and `gym_name` from `POST /attendance/device/verify` and from scan responses.
- Explain `403 MEMBERSHIP_GYM_MISMATCH` (member's home gym differs from the scanner's).
- Explain `403 ATTENDANCE_GYM_MISMATCH` (check-out at a gym other than the one holding the session).

## Evidence
Unit-testable parts are verified.

## Known gaps
- Device behavior is `IMPLEMENTED_UNTESTED`.
- Provisioning a scanner to a gym is still a CLI command (`python -m app.cli.scanner_device`), with no admin screen.

## Decisions
- None specific to this package.

## Links
- Repo spec: `specs/package-09-scanner-gym-awareness/spec.md`
- Main code: `scanner-mobile/`
- Previous: [[Package 08 - Documentation]]
- Next: [[Package 10 - Member mobile gyms]]
