# Day 50 feature freeze and backlog

Updated 2026-09-17. The release candidate is frozen around the implemented member, operations, analytics, and native member-app journeys. New work must fix a release blocker or be added to the backlog below.

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
| Backend | Day53 CSV/export/configuration integration and seed checks | Resolved | Verified September 16 in the final 102-test isolated suite |
| Backend | Query-plan/page review with 1,000 users | Medium | Verified September 16: bounded/disjoint CRM/attendance pages, fixed SELECT counts; empty billing/audit scale remains unmeasured, no justified new index |
| Web | Vite main bundle is 739.62 kB minified after compatible patches | Low | Known warning; consider code splitting after release blockers |
| Web | Existing TanStack React Compiler compatibility warning remains | Low | Known warning; no behavior failure observed |
| Mobile | Complete six-screen authenticated Android and session evidence | Resolved | All six reference screens, renewal/invoice, profile, QR recovery, SecureStore restore/logout/expiry and member-only role denial captured September 16; physical phone/iOS and full accessibility study remain unverified |
| Mobile | QR retry remained hidden after failed foreground refresh | Resolved | Shared guarded refresh callback and current-clock expiry initialization passed the final Android offline/background/foreground/Try again sequence |
| Mobile | `npm audit --omit=dev` reports 14 moderate transitive advisories in the Expo SDK57 tree | Medium | Accepted for this candidate; review on Expo SDK upgrade rather than forcing incompatible fixes |
| Data | Ordinary historical seed payments can fall outside the default analytics window | Low | Preserve invoice history; complete relative-date synthetic fixtures now exist only in isolated demo storage |
| Web | Twelve dependency audit advisories found September 16 | High | Resolved by compatible lockfile updates: fresh host install/lint/build/audit and rebuilt demo image pass; frontend audit 0 |
| Docker | Full interactive native/shared-backend rehearsal | Resolved | Fresh standalone images/migrations/seed/HTTP journey/worker checks plus native interactive member rehearsal passed September 16; September 17 changes affect packaging/documentation only |
| Documentation | FR1–FR39 mapping and release diagrams | Resolved | BRD Section 7 identifiers mapped to actual platform/code/test coverage; separate proposal still unavailable; API/PT/schema/UML reconciled September 17 |
| Packaging | September 16 ZIP included generated invoice PDFs | Resolved | Superseded local archive; new stdlib Git-source packager excludes all runtime storage and has three passing regression tests; see `archive-inventory.md` |
| Academic evidence | Separate proposal, five interviews, twenty survey results, eight-source literature list, competitor research and participant UAT | High | Open submission evidence gap; report as unavailable, never fabricate |
