# Package 5: member web dashboard and QR page

**Status:** `PLANNED`. Depends on Packages 1 to 3, which are committed. Web only: nothing under `mobile/` or `scanner-mobile/` changes.

## Purpose

Business goals served: members understand current gym crowdedness (G1) and can pick suitable training times (G2), and they see services for their own gym (G3). The dashboard should answer "is my gym busy now, when is it usually quiet, and how do I get in" without scrolling.

## What exists today (evidence)

- `MemberDashboardPage.tsx` is 40 lines. It reads `GET /dashboard/me` (refetch every 30 s). The payload (`dashboard_schema.py`) already carries `membership` with `home_gym_id` and `home_gym_name`, `qr_access`, `crowdedness` for the home gym, `upcoming_bookings`, `active_waitlists`, `recent_notifications`, `active_broadcasts` (first 3) and `quick_actions`.
- The dashboard renders a large hero, three cards, a four-item Quick actions grid that includes **QR code** (`dashboard_service.py:88`), then bookings and notifications.
- `MemberQrPage.tsx` reads `GET /attendance/qr-token/me`, refreshes the token 5 s before `expires_at`, shows a seconds countdown, and shows live capacity from `GET /attendance/crowdedness`. It renders the code with `qrcode.react` (`QRCodeSVG`).
- `GET /attendance/traffic-summary` (member, home gym only, no client gym parameter) returns `TrafficSummaryResponse`: `gym_name`, `capacity`, `period_start/end`, `data_sufficient`, `insufficiency_reason`, `contains_demo_data`, `busiest_window`, `quietest_window`, `buckets` (12 two-hour windows with `label`, `average_headcount`, `average_capacity_percentage`, `sample_count`) and `methodology`. No web page calls it yet.
- Recharts `^3.5.0` is installed. No source file imports it yet.
- `AttendanceRealtime` invalidates any query whose first key is `dashboard`, `attendance` or `training`, so dashboard and QR data refresh on realtime events.
- Dashboard crowdedness for a user with no membership falls back to District 1 (`dashboard_service.py:76-79`). See decision D-04.

## Actors

Member only. Admin, manager, staff and PT never see these pages. The backend, not the page, enforces this: `/attendance/traffic-summary` is `require_roles("member")`.

## Functional requirements

| ID | Requirement |
|---|---|
| FR-DASH-001 | The dashboard header is compact: a short greeting and the text "Your gym: {home_gym_name}" near the top. The current large hero is removed or reduced to this header. |
| FR-DASH-002 | The most prominent block shows live occupancy of the home gym: `active_count` of `capacity`, `percentage`, and the `status` label, with the gym name. |
| FR-DASH-003 | A "Busiest time last month" card and a "Quietest time last month" card show the `label` and `average_capacity_percentage` of `busiest_window` and `quietest_window` from the traffic summary. |
| FR-DASH-004 | A Recharts chart shows average capacity percentage by two-hour window from `buckets`, in window order. It has a visible legend or axis labels, an accessible tooltip, and a text fallback listing each window and its percentage. |
| FR-DASH-005 | Copy near the chart says the values are historical estimates from last month, not predictions. When `contains_demo_data` is true, the page says the figures come from demonstration data. |
| FR-DASH-006 | When `data_sufficient` is false, the chart and both cards are replaced by "Not enough attendance data yet", plus the reason. No window, recommendation or placeholder numbers are invented. |
| FR-DASH-007 | The dashboard embeds the rotating QR code when `qr_access.eligible` is true. It reuses the existing token endpoint and refresh behavior, shows the expiry countdown, and refreshes before expiry. |
| FR-DASH-008 | A button under the embedded QR opens the full QR page (`/app/qr`). |
| FR-DASH-009 | The QR item is removed from Quick actions. The backend no longer returns a `qr` quick action, and the page does not render one. |
| FR-DASH-010 | When `qr_access.eligible` is false, the QR area shows `qr_access.reason` and a link to the membership page. No token request is made. |
| FR-DASH-011 | Notifications and upcoming bookings use the space recovered from the smaller header. The list of recent notifications and active broadcasts is shown once, without duplicating the same item in both. |
| FR-DASH-012 | Membership information (plan, status, expiry, days remaining) stays visible in a compact card below the live facility status. |
| FR-DASH-013 | The full QR page shows the home gym name and district, that gym's live capacity, and the same historical summary. It keeps the existing token refresh, countdown, error states and recent attendance list. |
| FR-DASH-014 | Every data block has loading, error (with retry), empty and, where relevant, expired or unauthorized states. A failure in the traffic summary does not hide the QR or the membership card. |
| FR-DASH-015 | The layout works from phone width (no horizontal page scroll, 16 px gutters) up to desktop. |

## Non-functional requirements

- **NFR-DASH-001.** The page makes no request that names another gym. The member endpoints derive the gym on the server.
- **NFR-DASH-002.** The chart, cards and QR do not block each other: each has its own query and its own state.
- **NFR-DASH-003.** No new dependency. Use Recharts and `qrcode.react`, already installed.
- **NFR-DASH-004.** The rotating QR keeps the existing security behavior: a short-lived signed token, no caching of the token in storage, refetch on window focus.

## Acceptance criteria

**AC-DASH-001** Given a member whose active membership is at District 1, when the dashboard loads, then it shows "District 1" as the home gym, District 1's occupancy, and District 1's last-month busiest and quietest windows, and the page makes no request containing a District 11 identifier.

**AC-DASH-002** Given a member at District 11, when the dashboard loads, then every gym name, occupancy figure and window shown belongs to District 11.

**AC-DASH-003** Given an eligible member, when the dashboard loads, then a QR code is visible on the dashboard without navigating, with a countdown, and a button that opens `/app/qr`.

**AC-DASH-004** Given the QR token expires in 5 seconds, when the timer fires, then a new token is requested and the displayed code changes without a page reload.

**AC-DASH-005** Given any member, when the Quick actions section renders, then it has no QR item, and `GET /dashboard/me` returns no action with key `qr`.

**AC-DASH-006** Given an ineligible member (for example a revoked membership), when the dashboard loads, then no call to `/attendance/qr-token/me` is made, and the reason text and a membership link are shown.

**AC-DASH-007** Given a gym with `data_sufficient` false, when the dashboard loads, then the text "Not enough attendance data yet" appears and no chart, busiest window or quietest window is rendered.

**AC-DASH-008** Given a gym with sufficient data, when the dashboard loads, then the chart has 12 two-hour bars or points whose values equal `average_capacity_percentage`, and a text list shows the same values.

**AC-DASH-009** Given the traffic-summary request fails, when the dashboard loads, then an error with a retry action replaces only the history block, and the QR, occupancy and membership blocks still render.

**AC-DASH-010** Given a 375 px wide viewport, when the dashboard and the QR page load, then the document has no horizontal scroll and the QR, occupancy and primary actions are reachable without overlap.

**AC-DASH-011** Given a non-member role (staff, manager, admin), when `GET /attendance/traffic-summary` is called, then the response is 403.

**AC-DASH-012** Given the full QR page, when it loads for a District 11 member, then it shows District 11's name, district, live capacity and historical summary.

## Tasks

Each task lists the requirements and acceptance criteria it closes. Run the stated checks before moving on.

**Backend**

- **T5-01** Remove the `qr` quick action from `DashboardService`. Update the assertion in `test_day_39_42_rules.py` (line 315 checks `quick_actions[0]`) and add one assertion that no `qr` key is returned. Closes FR-DASH-009, AC-DASH-005. Check: backend unit tests.

**Frontend: shared code**

- **T5-02** Add typed `TrafficSummary` and related types to `types/operations.ts` matching `analytics_schema.py`. Closes FR-DASH-003 to 006.
- **T5-03** Extract the QR token query, the pre-expiry refresh and the countdown from `MemberQrPage.tsx` into one hook, for example `useRotatingQr`, and use it from both pages. No behavior change on `/app/qr`. Closes FR-DASH-007, NFR-DASH-004, AC-DASH-004. Check: existing web tests, manual refresh test.
- **T5-04** Add a `useTrafficSummary` query (`["attendance", "traffic-summary"]`, so realtime refresh and the existing key convention apply). Closes FR-DASH-003, NFR-DASH-002.

**Frontend: components**

- **T5-05** Build `OccupancyCard` (live, home gym) and reuse it on the QR page in place of the duplicated capacity metrics. Closes FR-DASH-002, FR-DASH-013.
- **T5-06** Build `TrafficHistory`: busiest card, quietest card, Recharts chart, text fallback, estimate copy, demo-data notice, insufficient-data state. Closes FR-DASH-003 to 006, AC-DASH-007, AC-DASH-008, AC-DASH-009.
- **T5-07** Build `EmbeddedQr`: QR, countdown, refresh state, "Open full QR page" button, ineligible state. Closes FR-DASH-007, 008, 010, AC-DASH-003, AC-DASH-006.

**Frontend: pages**

- **T5-08** Rework `MemberDashboardPage.tsx`: compact header with home gym, then occupancy, QR and history, then notifications and bookings, then the compact membership card, then the remaining quick actions. Remove the QR quick action rendering. Closes FR-DASH-001, 009, 011, 012, 014, 015, AC-DASH-001, 002, 005.
- **T5-09** Update `MemberQrPage.tsx` to show the home gym name and district, the shared `OccupancyCard` and `TrafficHistory`. Closes FR-DASH-013, AC-DASH-012.

**Tests and checks**

- **T5-10** Add web tests for the pure logic: window ordering and percentage mapping, insufficient-data branching, and the quick-action filter. Use the existing `node --test` setup in `frontend/tests/`. Closes AC-DASH-007, AC-DASH-008.
- **T5-11** Add a backend test that a staff, manager and admin token gets 403 from `/attendance/traffic-summary`, if one is not already covered by `test_traffic_analytics_storage.py`. Closes AC-DASH-011.
- **T5-12** Manual responsive and rotation check with the seeded `memberdist1@ypgym.dev` and `memberdist11@ypgym.dev` accounts at 375 px and 1280 px, recorded in the commit report. Closes AC-DASH-001 to 004, 010. See decision D-02 for browser automation.
- **T5-13** Run backend suite, `npm run lint`, `npm run build`, `npm test`, `alembic check`. No migration is expected.

## Out of scope

Native mobile dashboard, a gym selector for members, recommendations, and any new analytics endpoint. The member endpoint already exists and must not accept a client gym.

## Dependencies

Packages 1 to 3 (gym scope, occupancy, traffic summary). Decision D-04 (members with no membership) before T5-08.
