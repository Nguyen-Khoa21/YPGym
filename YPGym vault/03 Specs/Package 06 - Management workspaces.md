---
type: spec-package
package: 6
status: implemented-verified
date: 2026-11-10
commit: "05363bb (backend), 778b8cb (web)"
tags:
  - spec
  - package
related:
  - "[[Package 05 - Member dashboard]]"
  - "[[Package 07 - Form reliability]]"
  - "[[Decisions Log]]"
---

# Package 6: Management workspaces

> [!info] Status
> `implemented-verified` · commit `05363bb (backend), 778b8cb (web)`

## Goal
Staff, managers and owners work only on the branch they are allowed to see, and staff act only while on shift.

Business goals: G4, G5, G6.

## Key requirements
- New `GET /gyms/me` returns the caller's effective gym (D-01).
- Shift guard: attendance operations return `403 SHIFT_REQUIRED` with no open shift (D-09, closes G-01).
- Admin attendance page gets a gym selector and gym label (closes G-02).
- Realtime socket carries the branch and only that gym's queries refresh (closes G-03).
- Analytics summary is scoped by gym. Managers get no revenue (D-07, closes G-08, task T6-04).
- Owner must pass a gym for class list, peak hours and crowdedness (D-03).

## Evidence
Backend suite 217 passed, `alembic check` clean (no migration). Web lint 0 errors, 36 web tests passed. Playwright run passed three times in a row.

## Known gaps
- FR-OPS-009 only partly met: the gym scope bar shows on Attendance and Branches only.
- AC-OPS-011 does not assert the loading state or that District 1 rows vanish at once.
- AC-OPS-014 checked at query-key level, not with two live browser sessions.
- Branches edit and reassign flows, and double clicks on clock-in, clock-out and manual close, were not exercised in a browser.
- Admin traffic summary still defaults to District 1 for the owner.

## Decisions
- D-01 in [[Decisions Log]]
- D-03 in [[Decisions Log]]
- D-06 in [[Decisions Log]]
- D-07 in [[Decisions Log]]
- D-08 in [[Decisions Log]]
- D-09 in [[Decisions Log]]

## Links
- Repo spec: `specs/package-06-management-workspaces/spec.md`
- Main code: `attendance.py`, `attendance_service.py`, `attendance_realtime.py`, `AdminAttendancePage.tsx`
- Previous: [[Package 05 - Member dashboard]]
- Next: [[Package 07 - Form reliability]]
