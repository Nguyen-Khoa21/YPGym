---
type: spec-package
package: 5
status: implemented-verified
date: 2026-11-10
commit: "04b676f"
tags:
  - spec
  - package
related:
  - "[[Packages 01-04 Summary]]"
  - "[[Package 06 - Management workspaces]]"
  - "[[Decisions Log]]"
---

# Package 5: Member dashboard

> [!info] Status
> `implemented-verified` · commit `04b676f`

## Goal
Members see how busy their gym is right now, when it is usually quiet, and how to get in, without scrolling. Web only.

Business goals: G1, G2, G3.

## Key requirements
- Dashboard reads `GET /dashboard/me` and shows the home gym occupancy, bookings, notifications and broadcasts.
- Quiet-hours chart from `GET /attendance/traffic-summary` (first use of Recharts in the web app).
- QR quick action is removed from the dashboard because the QR page is its own screen (closes G-06).
- A member with no membership sees a prompt to buy and choose a gym, not District 1 occupancy (D-04).

## Evidence
Backend suite 211 passed, `alembic check` clean, web lint 0 errors, 31 web tests passed. Playwright run on a seeded stack at 375 px and 1280 px, QR rotation included.

## Known gaps
- Not verified on a physical phone.
- A District 11 history chart with real data was not verified (seeded District 11 history is all zeros).

## Decisions
- D-02 in [[Decisions Log]]
- D-04 in [[Decisions Log]]

## Links
- Repo spec: `specs/package-05-member-dashboard/spec.md`
- Main code: `MemberDashboardPage.tsx`, `MemberQrPage.tsx`, `dashboard_service.py`
- Previous: [[Packages 01-04 Summary]]
- Next: [[Package 06 - Management workspaces]]
