---
type: spec-package
package: 16
status: committed
date: 2026-11-10
commit: "9088536"
tags:
  - spec
  - package
related:
  - "[[Package 15 - Invoice viewer]]"
  - "[[Decisions Log]]"
---

# Package 16: Staff workspace and in-person registration

> [!info] Status
> `committed` · commit `9088536`

## Goal
Staff see attendance and live capacity in their own workspace and can register a walk-in member who pays by payOS QR or cash.

## Key requirements
- `StaffTimeClockPage` becomes the staff workspace (route unchanged, nav label "Workspace") with live capacity and the attendance sessions panel, shared with `AdminAttendancePage`.
- Shift gate stays: no open shift means no attendance or occupancy requests (`403 SHIFT_REQUIRED`).
- In-person registration without email verification; the account is linked to the staff member's gym automatically.
- Payment: payOS QR, or a Pay with cash button that records cash, activates the membership and issues the invoice (D-16).
- New `GET /staff/payments/{payment_id}` for polling; account marked verified with `registration_channel='in_person'` and a forced password change (D-17).

## Evidence
Commit exists in git log. API notes in `docs/api/staff-in-person-registration.md`.

## Known gaps
- None recorded in the spec.

## Decisions
- D-06 in [[Decisions Log]]
- D-16 in [[Decisions Log]]
- D-17 in [[Decisions Log]]

## Links
- Repo spec: `specs/package-16-staff-workspace-in-person-registration/spec.md`
- Main code: `StaffTimeClockPage.tsx`, `InPersonRegistrationDialog`, migration `0024`
- Previous: [[Package 15 - Invoice viewer]]
