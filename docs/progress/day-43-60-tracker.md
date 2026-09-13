# Day 42 through Day 60 release tracker

Updated 2026-09-07. Release scope is the user's Day 42–60 continuation request and the revised PostgreSQL plan. Status values: `not_started`, `in_progress`, `verified`, `blocked`. Implementation alone does not establish acceptance.

## Starting evidence and preserved work

- Repository: `C:\Users\Admin\ypgym`, branch `main`, HEAD `69dcb8b` (Days 39–42 implementation plus VND and Workspace navigation). No staged changes at entry.
- Pre-existing changes, preserved: `.gitignore`, revised plan (whitespace-only difference with `git diff -w`), `docs/database/erd.md`, historical `handoff.md`; deletions of old plan Markdown/PDF and Day 5–10 review DOCX; untracked `AGENTS.md` and `docs/diagrams/README.md`. Existing ignored Draw.io sources/images are user work.
- Available sources: `docs/HANDOFF.md`, historical root handoff, complete revised development plan, BRD Design Architecture DOCX with 24 embedded images, API/policy/design documents, code, seed and migrations. The separately named proposal and pasted Markdown files were not found by repository filename search. The full local plan/handoffs cover the supplied continuation scope; proposal FR identities must await the actual source, not be invented.
- Node `22.20.0`, npm `11.12.1`, host Python `3.13.7`. Frontend uses npm lockfile; backend uses `requirements.txt` and Docker Python 3.13. No mobile directory exists at entry.
- Docker Desktop was stopped; launched without deleting containers/volumes. Server now reports `29.4.3`; existing Compose `app` profile is running. Ports remain web 5174, API 8001, PostgreSQL 5433, Redis 6380.
- New baseline: `docker compose config --quiet` passes. Frontend `npm run lint` passes with the existing TanStack warning; `npm run build` passes (Vite 7.3.3, 730.67 kB main bundle warning). Backend/migration/live VND checks await running services.
- The Codex in-app browser completed the Day 42 interactive checkpoint. Evidence and limitations are indexed in `docs/design/evidence/day-42/README.md`. Fresh September 13 desktop/tablet/phone checks found no document-width overflow. Live backend suite: 59 passed; migration head/check and VND invoice content were verified September 7.

## Milestones

| Day | Requirement | Status | Implementation paths | Current evidence | Remaining work or blocker |
|---|---|---|---|---|---|
| 42 | Dashboard and interactive desktop/tablet/phone gate on dashboard, classes, bookings, trainer management | verified | `frontend/src/features/member/pages/MemberDashboardPage.tsx`, `frontend/src/features/classes/`, `backend/app/services/dashboard_service.py` | Real browser interactions, three viewport captures per route, role denial, loading/empty/error checks; `docs/design/evidence/day-42/README.md`; 59 backend tests | Design reference parity is separately tracked for Day 46 |
| 43 | Expo scaffold, shared API, secure token conventions and native health call | not_started | Intended `mobile/`; existing `/api/v1/health` | Existing backend contracts inspected | Day 42 gate; establish compatible Expo runtime |
| 44 | Mobile login/session restoration, dashboard and rotating QR | not_started | Existing auth, dashboard and attendance contracts | Existing web/backend implementation available | Implement and verify native critical flow |
| 45 | Mobile self-service and basic web PWA metadata | not_started | Existing classes/bookings/notifications/profile/purchase APIs | No mobile implementation at entry | Connect real flows; manifest/icons; responsive checks |
| 46 | Web/admin design parity | not_started | `docs/design/route-screen-map.md`, BRD DOCX | 24 embedded reference images located | Extract/map references and inspect all applicable routes |
| 47 | Six functional mobile screens and design parity | not_started | Intended `mobile/` | Dark/green mobile target specified | Native flows, screenshots and failure/session checks |
| 48 | Connected member/admin/mobile journeys | not_started | Web/backend/simulator and intended mobile | July regression is historical evidence only | Repeatable integration journeys and empty data |
| 49 | Manager analytics with real data and bounded cache freshness | not_started | Existing attendance analytics, operations shell | No new claims | Membership/class/attendance/revenue summaries and RBAC |
| 50 | Feature freeze, explicit backlog and categorized bug list | not_started | Intended release/backlog documents | FR39/chatbot, recommendations and personalization explicitly deferred | Inventory required flows and remove only obsolete release stubs |
| 51 | Dedicated database auth/role/membership tests | not_started | `backend/app/tests/` | Existing suite uses unit/service test doubles | Repeatable real database success/failure/ownership coverage |
| 52 | Attendance/QR/device/worker/occupancy tests | not_started | Attendance services, workers, simulator | Prior results require fresh verification | Concurrency, expiry, replay, timeouts and reconciliation |
| 53 | Booking/billing/audit/configuration tests | not_started | Class/billing/operations services and tests | Existing Day 39–42 rule tests | Real transaction races, retries, invoice/CSV/audit verification |
| 54 | Measured performance with at least 1,000 synthetic users | not_started | Existing repositories/indexes/Redis | No measurements this session | Isolated dataset/load harness, metrics and limitations |
| 55 | Redis rate limits and security verification | not_started | Existing core/auth/attendance/export code | Needs inspection | Limits, JWT/RBAC, CORS, CSV injection and secret inventory |
| 56 | Responsive/accessibility/error/offline/session QA | not_started | Web/mobile UI, route-screen map | Browser tooling available | Rendered checks; separate native/browser evidence |
| 57 | Architecture/API/ERD/UML/policies/table traceability | not_started | `docs/architecture`, `docs/api`, `docs/database`, `docs/diagrams` | Existing diagrams/docs available | Verify/update against release code; reconcile checklist tables |
| 58 | Repeatable isolated representative seed and examiner demo | not_started | `backend/app/db/seed.py`, `docs/demo` | Existing idempotent seed inspected | All required tiers/states/bookings/waitlists/relative dates and full script |
| 59 | Fresh disposable stack rebuild and complete demo rehearsal | not_started | Compose, migrations, seed, all clients | Normal development volumes preserved | Isolated fresh DB/Redis/services; native/shared API rehearsal |
| 60 | Screenshots, reviewed local archive, commit/tag, viva evidence | not_started | Intended local release and evidence documents | Final local commit/tag explicitly authorized after gates pass; remote push not authorized | Complete software gates; archive inventory; local commit/tag |

## Cross-cutting release and academic gates

- Maintain unchanged FR1–FR39 identifiers from the actual proposal when provided; distinguish web/native platform coverage. FR5 email changes require reverification or an explicit partial status. FR39 remains deferred with proposal discrepancy and no assumed supervisor approval.
- Software release does not prove completion of the 30-week academic schedule. Prepare UAT tasks, accurately labelled SUS-style questionnaire/scoring and empty results; never fabricate the required five participants or score.
- Inventory evidence for five interviews, twenty survey responses, eight credible sources and three competitors; report missing evidence without inventing research.
- No live settlement, physical access hardware, public hosting, store publishing, remote push, AI/chatbot or personalization is authorized in this release.

## Next exact action

Day 42 interactive acceptance passed. Continue Day 43–47: build and verify the Expo member app against the shared backend, then document native launch and screen parity honestly.
