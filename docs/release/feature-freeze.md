# Day 50 feature freeze and backlog

Updated 2026-09-14. The release candidate is frozen around the implemented member, operations, analytics, and native member-app journeys. New work must fix a release blocker or be added to the backlog below.

## Included in the release candidate

- PostgreSQL-backed authentication, membership lifecycle, plans, mock billing/invoices, notifications, broadcasts, classes, bookings, waitlists, attendance, rotating QR, IoT scanner contract, occupancy, CRM, exports, audit, configuration, trainer management, and role-aware web routes.
- Manager/admin analytics for membership trends, class popularity, attendance patterns, and successful payment summaries with manager/admin RBAC and bounded Redis freshness.
- Expo SDK57 member app using the same FastAPI contracts: session restoration, dashboard, QR, class booking/waitlists, bookings, attendance, notifications, profile/preferences, invoices, and mock renewal.
- Docker Compose runbook, idempotent development seed, route map, design evidence indexes, and PowerShell startup instructions.

## Explicitly deferred after Day 60

- AI chatbot expansion (FR39), personalization, and rule-based recommendations.
- Live payment settlement, external SMTP delivery, public hosting, app-store publishing, and physical scanner firmware.
- Advanced personal-trainer programming, payroll, and client-program management.

These are backlog items, not hidden release claims. The proposal source needed to reconcile FR39 and supervisor approval was not found in the repository, so no approval is inferred.

## Release bug and gap list

| Area | Item | Severity | State / next action |
|---|---|---|---|
| Backend | Day53 CSV/export and configuration integration checks remain to be added | Medium | In progress; add focused checks before release tag |
| Backend | Final query-plan/index review for the 1,000-account benchmark remains | Medium | In progress; keep the bounded measured results and limitations explicit |
| Web | Vite main bundle remains about 731 kB minified | Low | Known warning; consider code splitting after release blockers |
| Web | Existing TanStack React Compiler compatibility warning remains | Low | Known warning; no behavior failure observed |
| Mobile | Authenticated Android screenshots are not yet captured; current native evidence proves launch/login/API health only | High | Open; manually confirm the seeded credential and capture dashboard, QR, classes, and profile |
| Mobile | `npm audit --omit=dev` reports 14 moderate transitive advisories in the Expo SDK57 tree | Medium | Accepted for this candidate; review on Expo SDK upgrade rather than forcing incompatible fixes |
| Data | Seeded membership/payment rows can fall outside the default 30-day analytics window | Low | Expected; use explicit range or representative seed data for a trend demo |
| Docker | Fresh disposable rebuild and full native/shared-backend rehearsal remain outstanding | High | Open for Day59 |
| Documentation | Proposal FR1–FR39 identities, five-interview evidence, twenty-survey results, and eight-source literature list are unavailable | High | Open; report as unavailable, never fabricate |
