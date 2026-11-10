---
type: spec-package
package: 10
status: partially-implemented
date: 2026-11-10
commit: "bc6096f"
tags:
  - spec
  - package
related:
  - "[[Package 09 - Scanner gym awareness]]"
  - "[[Package 11 - Email verification code]]"
  - "[[Decisions Log]]"
---

# Package 10: Member mobile gyms

> [!info] Status
> `partially-implemented` · commit `bc6096f`

## Goal
Members on the phone can see and choose their gym, and screens say which gym they describe. Member app only (`mobile/`).

Business goals: G1, G2, G6.

## Key requirements
- Call `GET /gyms` and `GET /gyms/me` and send `gym_id` on `classes/upcoming`, `attendance-benefit/me` and `payos/create`.
- Handle `422 GYM_SELECTION_REQUIRED` on a first purchase without a gym.
- The home gym changes only when payment succeeds (same rule as web).

## Evidence
T10-00 to T10-07 are done (results recorded 2026-11-09). The commit hash comes from `git log`.

## Known gaps
- T10-08 (real devices) is not done.
- Owner's uncommitted edits in `mobile/` still need the owner's own commit (D-11).

## Decisions
- D-11 in [[Decisions Log]]

## Links
- Repo spec: `specs/package-10-member-mobile-gyms/spec.md`
- Main code: `mobile/src`, `mobile/(tabs)/_layout.tsx`
- Previous: [[Package 09 - Scanner gym awareness]]
- Next: [[Package 11 - Email verification code]]
