---
type: spec-package
package: 12
status: committed
date: 2026-11-10
commit: "25da3e8"
tags:
  - spec
  - package
related:
  - "[[Package 11 - Email verification code]]"
  - "[[Package 13 - Expired membership and location separation]]"
  - "[[Decisions Log]]"
---

# Package 12: Onboarding recommendations

> [!info] Status
> `committed` · commit `25da3e8`

## Goal
Ask a short radio-button questionnaire, recommend a gym and quiet hours, and give the owner aggregate data. Never recommend from an unanswered question.

## Key requirements
- Three required questions: new to the gym, uncrowded hours, closer location (one radio per active gym from `GET /gyms`, never hard-coded).
- Optional extras: main goal, training time, days per week, interest in classes.
- Member-only endpoints under the existing user/me router with a status of `not_started`, `skipped`, `partial` or `complete`.
- Owner and manager see aggregates only; groups under 5 responses are hidden (D-14).

## Evidence
Commit exists in git log. API notes in `docs/api/onboarding.md`.

## Known gaps
- None recorded in the spec.

## Decisions
- D-13 in [[Decisions Log]]
- D-14 in [[Decisions Log]]

## Links
- Repo spec: `specs/package-12-onboarding-recommendations/spec.md`
- Main code: `docs/api/onboarding.md`
- Previous: [[Package 11 - Email verification code]]
- Next: [[Package 13 - Expired membership and location separation]]
