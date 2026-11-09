# Package 10: member mobile app gym support

**Status:** `PLANNED`. Member app only (`mobile`). No backend change expected; if one is needed it is raised in decisions first.

## Purpose

Members on the phone cannot see or choose their gym. The backend resolves a missing gym to the member's previous gym, so nothing breaks, but a member cannot join or move to District 11 from the phone, and screens do not say which gym they describe. Business goals served: G1, G2, G6.

## What exists today (evidence)

- `grep` of `mobile/src` finds no `gym_id`, `gym_name` or `/gyms` call. The calls that matter are `crowdedness` (dashboard), `classes/upcoming` (classes tab), and `attendance-benefit/me?plan_id=` and `payos/create` (renewal confirm screen). None sends a gym.
- Backend behavior the app can rely on: `GET /gyms` (active gyms), `GET /gyms/me`, `gym_id` on `classes/upcoming`, `attendance-benefit/me` and `payos/create`; `CrowdednessResponse` includes `gym_name`; a first purchase without `gym_id` returns `422 GYM_SELECTION_REQUIRED`; the home gym changes only when payment succeeds.
- The owner has uncommitted edits in `mobile/` (`.gitignore`, `AGENTS.md`, `README.md`, `app.json`, `package.json`, `package-lock.json`, `(tabs)/_layout.tsx`). See decision D-11.

## Functional requirements

| ID | Requirement |
|---|---|
| FR-MOB-001 | The dashboard and QR screens show the member's home gym name. |
| FR-MOB-002 | The crowdedness card names its gym. |
| FR-MOB-003 | The renewal flow lists active gyms, defaults to the previous home gym, and sends `gym_id` to `attendance-benefit/me` and `payos/create`. |
| FR-MOB-004 | The renewal confirmation says the gym changes only after payment succeeds. |
| FR-MOB-005 | After a successful payment the app refreshes the gym and dashboard data. |
| FR-MOB-006 | The classes tab lists classes for the home gym and names it. |
| FR-MOB-007 | `GYM_SELECTION_REQUIRED`, `MEMBERSHIP_GYM_MISMATCH` and an inactive gym give clear member-facing messages. |
| FR-MOB-008 | The QR screen tells the member the QR is valid at their home gym. |

## Acceptance criteria

**AC-MOB-001** Given a member of District 11, when the dashboard loads, then the gym name and the crowdedness card both say District 11.

**AC-MOB-002** Given a renewal, when the member picks a gym, then both requests carry that `gym_id`; given no pick, then the previous gym is sent.

**AC-MOB-003** Given a gym that becomes inactive, when checkout is attempted, then the app shows the backend's refusal text rather than a crash.

**AC-MOB-004** Given payment success, when the app refreshes, then the new home gym is shown without a restart.

**AC-MOB-005** Given a District 1 member at the District 11 scanner, when scanned, then the member sees (or staff see) the mismatch message; the member's QR screen has already warned about the home gym.

**AC-MOB-006** Given the existing mobile tests, when run, then they still pass.

## Tasks

- **T10-00** Resolve D-11 (owner's uncommitted mobile edits) before touching those files.
- **T10-01** Gym types and an API helper for `GET /gyms` and `GET /gyms/me` (FR-MOB-001, 003).
- **T10-02** Gym name on dashboard, QR and crowdedness card (FR-MOB-001, 002, 008).
- **T10-03** Gym picker in the renewal flow and `gym_id` on both calls (FR-MOB-003, 004).
- **T10-04** Query refresh after payment (FR-MOB-005).
- **T10-05** Classes tab gym label and `gym_id` (FR-MOB-006).
- **T10-06** Error messages (FR-MOB-007).
- **T10-07** Node tests for the helpers, `tsc`, existing suite (AC-MOB-006).
- **T10-08** Run the ten-step demo with a real phone as the member and a scanner at each gym on Android and iOS. Record results honestly.

## Out of scope

Mobile traffic chart, preference questionnaire, recommendations, online PT services (deferred). A scanner or gym provisioning UI.
