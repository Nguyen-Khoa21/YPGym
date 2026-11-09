# Package 8: documentation and release evidence

**Status:** `PARTIALLY_IMPLEMENTED`: the documents below were written and checked against code and a seeded run, with the gaps listed at the end. Documentation only: no application code changes.

## Purpose

Make the multi-gym system explainable and demonstrable, and give the owner honest evidence for what was verified. Business goals served: all of G1 to G6, through the demo flow.

## What exists today (evidence)

- `docs/policies/roles.md` has a capability table with no gym or branch scope. `docs/database/erd.md`, `docs/demo/demo-script.md`, `docs/design/route-screen-map.md`, `docs/architecture/system-architecture.md` and `docs/release/requirements-traceability.md` exist.
- Gym-aware API documents exist only for traffic analytics (`docs/api/traffic-analytics.md`) and memberships, classes and broadcasts (`docs/api/gym-scoped-services.md`).
- `route-screen-map.md`, `system-architecture.md` and `docs/diagrams/README.md` currently contain the owner's uncommitted edits. Package 8 edits them only after the owner commits or approves a merge, and stages only its own hunks.
- The demo seed creates the accounts the demo needs: `owner@ypgym.dev`, `managerdist1@`, `managerdist11@`, `staffdist1@`, `staffdist11@`, `memberdist1@` and `memberdist11@` (`ypgym.dev`), plus a scanner device for each gym.

## Functional requirements

| ID | Requirement |
|---|---|
| FR-DOC-001 | `docs/policies/roles.md` shows the Owner, Manager, Staff, PT and Member matrix from Package 6, including gym scope and the shift rule for staff, and says the owner is the `admin` role. |
| FR-DOC-002 | `docs/database/erd.md` includes `gym_locations`, `workforce_gym_assignments` and every table carrying a gym reference (`iot_devices`, `attendance_sessions`, `attendance_events`, `user_memberships.home_gym_id`, `classes`, `staff_shifts`, `broadcast_announcements`, `payments`), as a Mermaid diagram. |
| FR-DOC-003 | One API reference lists every gym-aware endpoint with role, gym scope rule and error codes, including `SHIFT_REQUIRED`. It links to the existing detailed pages instead of copying them. |
| FR-DOC-004 | The architecture document shows how a scan flows from scanner to gym-scoped occupancy, the Redis keys and channels per gym, and the realtime socket scope, as a Mermaid diagram. |
| FR-DOC-005 | `route-screen-map.md` lists the routes added or changed in Packages 5 and 6. |
| FR-DOC-006 | A migration note lists revisions `20261107_0020` and `20261109_0021` with what each backfills and what a downgrade removes. |
| FR-DOC-007 | The demo script walks the ten steps in the master prompt's acceptance flow with the seeded accounts and the expected result of each step. |
| FR-DOC-008 | A verification record states which commands were run, on which commit, and their exact results. Nothing is described as passing unless it ran. |
| FR-DOC-009 | A known-limitations list covers at least: real payOS payment untested, no physical phone or iOS testing, demo data in analytics, native mobile and scanner apps not updated for gyms. |
| FR-DOC-010 | A deferred-work list covers the mobile gym selector, mobile traffic chart, preference questionnaire, recommendations and online PT services, and links to the future-scope section of the master prompt. |
| FR-DOC-011 | A release-readiness checklist is completed only with verified items. Unverified items are shown as such. |

## Acceptance criteria

**AC-DOC-001** Given the role document, when compared with the Package 6 role table, then every row matches, and a spot check of five role and gym combinations against the API returns the documented result.

**AC-DOC-002** Given the ERD, when compared with `\d` output of the migrated test database, then every gym foreign key in the database appears in the diagram and no diagram relation lacks a database column.

**AC-DOC-003** Given the API reference, when each listed endpoint is compared with the router files, then paths, methods and roles match.

**AC-DOC-004** Given the demo script, when a person follows it on a freshly seeded stack, then every step produces the stated result. Any step that fails is fixed in the document or reported, not hidden.

**AC-DOC-005** Given the verification record, when each command in it is rerun on the stated commit, then the result matches what is written.

**AC-DOC-006** Given the limitations and deferred lists, when read, then no feature listed as deferred is described elsewhere as available.

## Tasks

- **T8-01** Update `roles.md` (FR-DOC-001). Check against Package 6 tests.
- **T8-02** Update `erd.md` with the gym relations, checking against `\d` on the migrated test database (FR-DOC-002).
- **T8-03** Write the API reference page and link it from `docs/api` (FR-DOC-003).
- **T8-04** Add the scan-to-occupancy and realtime diagrams to the architecture document (FR-DOC-004).
- **T8-05** Update the route-screen map and the migration note (FR-DOC-005, FR-DOC-006), staging only Package 8 hunks.
- **T8-06** Extend `demo-script.md` with the ten-step multi-gym flow and run it once on a seeded isolated stack (FR-DOC-007, AC-DOC-004).
- **T8-07** Write the verification record from fresh runs of the backend suite, `alembic upgrade`, downgrade and `check`, web lint, build and tests (FR-DOC-008, AC-DOC-005).
- **T8-08** Write limitations, deferred work and the release checklist, and update [traceability.md](../traceability.md) statuses to match what was verified (FR-DOC-009 to 011).

## Out of scope

Any code or test changes. If the documentation work finds a defect, it is reported to the owner and handled as its own change.

## Implementation record

Written 2026-11-09. Where a target file held the owner's uncommitted edits, a new companion file was written instead of editing it, so no unrelated hunks were staged.

| Requirement | Where | State |
|---|---|---|
| FR-DOC-001 | `docs/policies/roles.md`, new gym scope section | Done. Matches `GymScopeService` and `ShiftGuard`; spot checks are steps 5 to 9 of the demo flow. |
| FR-DOC-002 | `docs/database/erd.md`, new multi-gym section | Done. Checked against the foreign keys of the migrated test database; every gym column in it appears, and every relation drawn exists. |
| FR-DOC-003 | `docs/api/gym-aware-endpoints.md` | Done. Endpoint list taken from the application's OpenAPI document; roles and scope rules read from the router files. |
| FR-DOC-004 | `docs/architecture/multigym-flows.md` | Done as a companion file. Folding it into `system-architecture.md` waits for the owner's edits to that file. |
| FR-DOC-005 | `docs/design/multigym-routes.md` | Done as a companion file. `route-screen-map.md` itself is untouched for the same reason. |
| FR-DOC-006 | `docs/database/multigym-migrations.md` | Done. |
| FR-DOC-007 | `docs/demo/demo-script.md`, multi-gym walkthrough | Done. Steps 1 to 9 were run on a seeded stack through the API; step 10 is covered by Playwright. A person has not followed it by hand (AC-DOC-004 is partly met). |
| FR-DOC-008 | `docs/release/multigym-verification.md` | Done from fresh runs. |
| FR-DOC-009, 010, 011 | Same file | Done. The master prompt's future-scope section is not in the repository, so the deferred list does not link to it. |

Not done: the full AC-DOC-001 check of five role and gym combinations through the web UI, the AC-DOC-003 automated comparison of every endpoint (it was a manual read), and the AC-DOC-005 rerun by a second person.
