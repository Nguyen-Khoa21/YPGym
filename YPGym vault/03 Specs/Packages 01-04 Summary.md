---
type: summary
status: implemented-verified
date: 2026-11-10
tags:
  - spec
  - summary
related:
  - "[[Package 05 - Member dashboard]]"
  - "[[Decisions Log]]"
---

# Packages 01 to 04 summary

Short evidence summary from `specs/completed-packages.md`. Branch `codex/feat/web-multigym-foundation`. Full backend suite on the Package 4 content: 209 tests passed (2026-11-09).

## What each package delivered

**Package 1, multi-location foundation** (commit `f46aa78`, migration `20261107_0020`). Tables `gym_locations` and `workforce_gym_assignments`, gym columns on devices, attendance, memberships, classes, shifts and broadcasts, a District 1 backfill, `GET /gyms`, `GymScopeService`.

**Package 2, gym-scoped attendance and realtime** (commit `3071514`). Scanner bound to a gym, per-gym occupancy and cache, gym-scoped history and manual close, WebSocket whose first frame may name a gym.

**Package 3, historical peak and off-peak analytics** (commit `f7f7dd8`). `GET /attendance/traffic-summary` for members and `GET /admin/analytics/traffic-summary?gym_id=` for admins. Previous completed month, 15 minute sampling, two-hour windows, busiest and quietest windows, weekday heatmap.

**Package 4, memberships, payments, classes and broadcasts** (commit `e161f32`, migration `20261109_0021`). Gym choice on first purchase and renewal, `payments.gym_id`, membership gym applied only after verified payment, gym-scoped classes, chain-wide or per-gym broadcasts.

## Gaps found in completed work

| ID | Finding | Handled in |
|---|---|---|
| G-01 | Staff can use attendance without an open shift | [[Package 06 - Management workspaces]] |
| G-02 | Admin attendance page has no gym selector | [[Package 06 - Management workspaces]] |
| G-03 | Realtime socket defaults to all gyms for an admin | [[Package 06 - Management workspaces]] |
| G-04 | Some admin endpoints fall back to District 1 | D-03 in [[Decisions Log]] |
| G-05 | No test for the inactive-gym webhook or idempotency conflict | D-05 in [[Decisions Log]] |
| G-06 | Dashboard still returns a QR quick action | [[Package 05 - Member dashboard]] |
| G-07 | Role and architecture docs lack gym-scoped roles | [[Package 08 - Documentation]] |
| G-08 | Analytics summary shows chain-wide totals to managers (security) | [[Package 06 - Management workspaces]], task T6-04 |
