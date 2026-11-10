---
type: spec-package
package: 13
status: committed
date: 2026-11-10
commit: "fe3cc46"
tags:
  - spec
  - package
related:
  - "[[Package 12 - Onboarding recommendations]]"
  - "[[Package 14 - Dashboard UI tweaks]]"
  - "[[Decisions Log]]"
---

# Package 13: Expired membership and location separation

> [!info] Status
> `committed` · commit `fe3cc46`

## Goal
An expired member is clearly asked to renew or change location, and each gym keeps its own manager, staff and PT accounts.

## Key requirements
- Expired panel on web dashboard, `/app/qr` and mobile: "Your membership at {gym} expired on {date}" with Renew and Change location.
- Home gym still changes only after verified payment (FR-EXP-003).
- Account separation audit: one active `workforce_gym_assignments` row per account, staff accounts need a gym, moving accounts is owner-only and audited.
- Every workforce page shows the account's gym.

## Evidence
Commit exists in git log.

## Known gaps
- None recorded in the spec.

## Decisions
- D-15 in [[Decisions Log]]

## Links
- Repo spec: `specs/package-13-expired-membership-location-separation/spec.md`
- Main code: `BuyMembershipPage`, `workforce_gym_assignments`
- Previous: [[Package 12 - Onboarding recommendations]]
- Next: [[Package 14 - Dashboard UI tweaks]]
