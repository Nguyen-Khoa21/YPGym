---
type: decision
status: approved
date: 2026-11-10
tags:
  - decision
related:
  - "[[Packages 01-04 Summary]]"
  - "[[Home]]"
---

# Decisions Log

Source: `specs/decisions.md`. On 2026-11-09 the owner approved every recommendation ("go with your recommendations"). D-12 to D-18 were answered by the owner where marked in the repo file, otherwise approved by default.

## Decisions

| ID | Question | Affects | Outcome |
|---|---|---|---|
| D-01 | How does the web client learn a manager or staff member's gym? | [[Package 06 - Management workspaces]] | Add `GET /gyms/me`. User payload stays untouched. |
| D-02 | Browser tests: set up Playwright or stay with `node --test`? | [[Package 05 - Member dashboard]], [[Package 07 - Form reliability]] | Minimal Playwright config for the broadcast form and dashboard responsive check. |
| D-03 | Fallback to District 1 when an admin sends no gym? | [[Package 06 - Management workspaces]] | Require an explicit gym (`422 GYM_SCOPE_REQUIRED`) where the owner compares branches. |
| D-04 | What does the dashboard show with no membership? | [[Package 05 - Member dashboard]] | No occupancy or history; prompt to buy a membership and choose a gym. |
| D-05 | Add tests for the inactive-gym webhook and idempotency conflict? | Package 4 confidence | Yes, one small test-only commit. |
| D-06 | Should staff crowdedness be shift-gated? | [[Package 06 - Management workspaces]], [[Package 16 - Staff workspace and in-person registration]] | Occupancy stays ungated; the workspace just does not request it while locked. |
| D-07 | May a manager see branch revenue? | [[Package 06 - Management workspaces]] | No. Owner-only revenue. The chain-wide summary is fixed either way (G-08). |
| D-08 | Owner attendance page default: one branch or all? | [[Package 06 - Management workspaces]] | Default to one branch, with an "All branches" option. |
| D-09 | Name of the shift error | [[Package 06 - Management workspaces]] | `403 SHIFT_REQUIRED` in the existing error format. |
| D-10 | What to do with the stale `docs/HANDOFF_MULTIGYM_SESSION.md`? | Housekeeping | Replace with a short handoff later; do not commit the stale one. |
| D-11 | Commit the owner's uncommitted `mobile/` edits first? | [[Package 10 - Member mobile gyms]] | Owner continued without choosing. Package 10 left the seven files untouched and unstaged. They still need the owner's own commit. |
| D-12 | Verification code shape | [[Package 11 - Email verification code]] | 6 digits, 10 minute expiry, 5 wrong attempts then locked, 60 second resend cooldown. |
| D-13 | When does the questionnaire appear? | [[Package 12 - Onboarding recommendations]] | Owner confirmed: right after first login, skippable, editable in Profile. |
| D-14 | Who sees onboarding data? | [[Package 12 - Onboarding recommendations]] | Owner and manager see aggregates only; groups under 5 hidden; staff and PT see nothing. |
| D-15 | Meaning of "each location with each role account staying separate" | [[Package 13 - Expired membership and location separation]] | Every gym has its own manager, staff and PT; only the owner is cross-gym. Ask again if the owner meant something else. |
| D-16 | In-person registration payment | [[Package 16 - Staff workspace and in-person registration]] | Owner confirmed: payOS QR, or staff press Pay with cash. Staff need an open shift. |
| D-17 | Email status of in-person accounts | [[Package 16 - Staff workspace and in-person registration]] | Marked verified, `registration_channel='in_person'`, forced password change at first login. |
| D-18 | Reading of the annotated dashboard screenshots | [[Package 14 - Dashboard UI tweaks]] | See Package 14 in the repo spec. |

## Findings that need no decision

> [!warning] G-08 (security)
> `GET /admin/analytics/summary` returned totals for all gyms and allowed managers. Fixed in Package 6, task T6-04.

Other gaps from completed work are in [[Packages 01-04 Summary]].
