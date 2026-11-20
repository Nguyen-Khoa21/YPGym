---
type: spec-package
package: 17
status: uncommitted
date: 2026-11-20
tags:
  - spec
  - package
related:
  - "[[Package 14 - Dashboard UI tweaks]]"
  - "[[Package 16 - Staff workspace and in-person registration]]"
---

# Package 17: Lecturer dashboard feedback

> [!info] Status
> `uncommitted`. The changes are in the working tree on `refactor/frontend-readability`.

## Goal
Apply the lecturer's notes on the web member dashboard. This replaces the two-tab card (Important, Membership) from [[Package 14 - Dashboard UI tweaks]].

## Changes
- The greeting "Hi, {first name}" moved into the site header next to the YPGym logo (`AppFrame`, `.header-greeting`). It is hidden below 1100px wide.
- The dashboard heading is now the member's gym ("YPGym District 1" with a map pin).
- The quiet-time box is highlighted: thick green border, tinted background, dark icon tile and large time label.
- `OccupancyCard` is more compact.
- Membership status moved off the dashboard into the new `MembershipStatusCard`, shown on the Profile page and the Membership plans page. It reuses the cached `/dashboard/me` query through `useMemberDashboard`.
- Important notifications moved into the header as a light-green bell button, next to Workspace, with a red unread count (`HeaderNotifications`). The dropdown lists announcements and unread notifications, links to the inbox, and closes on Escape or when focus leaves it. It is shown to members only.
- On phones and tablets (1100px wide and below), Workspace and the bell are icon-only, and the count sits on the bell.

## Evidence
- `npm run lint`, `npm run build`, `npm run test` (79 pass) and `prettier --check` pass.
- Checked in the browser at 375, 780, 900, 1120 and 1280px with no horizontal overflow.
- The Playwright spec `e2e/member-dashboard.spec.ts` is updated but has not been run, because no Playwright browser is installed.

## Known gaps
- No backend, API or database change.
- The mobile app is unchanged.

## Links
- Main code: `AppFrame.tsx`, `HeaderNotifications.tsx`, `MembershipStatusCard.tsx`, `MemberDashboardPage.tsx`, `index.css`
- Previous: [[Package 16 - Staff workspace and in-person registration]]
