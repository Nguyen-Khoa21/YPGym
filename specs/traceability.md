# Traceability

Business goal, requirement, package, implementation and test, with the status each had at commit `e161f32`. This covers the multi-gym initiative only. The BRD FR1 to FR39 mapping for the original project lives in [docs/release/requirements-traceability.md](../docs/release/requirements-traceability.md) and is not repeated here.

Completed packages use the Master Prompt section as their requirement reference, because they were not written with IDs. Planned packages use the IDs in their specs. Status labels are defined in the [README](README.md).

## Business goals

| ID | Goal |
|---|---|
| G1 | Members understand how crowded their gym is. |
| G2 | Members can identify suitable training times. |
| G3 | Members get location-specific gym services. |
| G4 | Managers get operational visibility for their own branch. |
| G5 | Owners get multi-location business insight. |
| G6 | QR attendance stays secure and reliable. |

## Matrix

| Goal | Requirement | Package | Implementation | Test | Status |
|---|---|---|---|---|---|
| G1 | Live occupancy per gym (Master Prompt, attendance and occupancy section) | 2 | `CrowdednessService`, `/attendance/crowdedness`, `/gyms/{id}/crowdedness` | `test_attendance_gym_isolation.py` | `IMPLEMENTED_VERIFIED` |
| G1 | Prominent live occupancy on the member dashboard, FR-DASH-002 | 5 | `OccupancyCard`, `MemberDashboardPage.tsx` (commit `04b676f`) | AC-DASH-001, 002; Playwright `member-dashboard.spec.ts` | `IMPLEMENTED_VERIFIED` |
| G1 | Occupancy updates in real time for the right gym, FR-OPS-016, FR-OPS-017 | 6 | Owner socket carries the branch; events refresh only that gym's queries (`778b8cb`) | `gymScope.test.mjs`; AC-OPS-014 | `IMPLEMENTED_VERIFIED` (predicate level, no two-session test) |
| G2 | Previous-month busiest and quietest two-hour windows | 3 | `/attendance/traffic-summary`, `TrafficAnalyticsService` | `test_traffic_analytics.py`, `test_traffic_analytics_storage.py` | `IMPLEMENTED_VERIFIED` |
| G2 | Show busiest, quietest and the two-hour chart to members, FR-DASH-003 to 006 | 5 | `TrafficHistory`, `memberDashboardLogic.ts` | `memberDashboard.test.mjs`; AC-DASH-007, 008 | `IMPLEMENTED_VERIFIED` |
| G3 | Choose a gym when buying or renewing; gym applied only after verified payment | 4 | `MembershipService.resolve_purchase_gym`, `PayOSPaymentService`, `payments.gym_id` | `test_payos_payment.py`, `test_account_journey.py` | `IMPLEMENTED_VERIFIED` |
| G3 | Inactive gym at webhook time moves payment to `paid_review`; idempotency conflict returns 409 | 4 | `payment_service.py`, `membership_service.py` | `test_payos_payment.py` (commit `a0f6e51`) | `IMPLEMENTED_VERIFIED` |
| G3 | Classes, overlap, listings and checkout are gym-aware | 4 | `ClassService`, `BookingService`, `ClassRepository` | `test_member_service_gym_isolation.py` | `IMPLEMENTED_VERIFIED` |
| G3 | Broadcasts are chain-wide or per gym; managers forced to their gym | 4 | `NotificationService` | `test_member_service_gym_isolation.py` | `IMPLEMENTED_VERIFIED` |
| G3 | Dashboard shows the member's home gym, FR-DASH-001, FR-DASH-013 | 5 | Dashboard header and QR page show the home gym | Playwright | `IMPLEMENTED_VERIFIED` |
| G4 | Manager attendance and manual close limited to the assigned gym | 2 | `GymScopeService`, `AttendanceService.manual_close` | `test_attendance_gym_isolation.py` | `IMPLEMENTED_VERIFIED` |
| G4 | Manager traffic summary limited to the assigned gym | 3 | `/admin/analytics/traffic-summary` | `test_traffic_analytics_storage.py` | `IMPLEMENTED_VERIFIED` |
| G4 | Staff use attendance only while clocked in, FR-OPS-001 to 008 | 6 | `ShiftGuard`, locked staff workspace (`05363bb`, `778b8cb`) | `test_shift_and_scope_rules.py`, Playwright | `IMPLEMENTED_VERIFIED` |
| G4 | Manager summary analytics limited to the branch, no chain-wide revenue, FR-OPS-014 | 6 | Scoped summary, manager forced to own gym, revenue owner-only (`05363bb`) | `test_shift_and_scope_rules.py` | `IMPLEMENTED_VERIFIED` |
| G4 | Gym scope shown in every operations header; manager has no selector, FR-OPS-009 to 011 | 6 | `GET /gyms/me`, `GymScopeBar` on Attendance and Branches pages only | Playwright; AC-OPS-013 | `PARTIALLY_IMPLEMENTED` |
| G4 | Typeable, consistent management forms including broadcasts, FR-FORM-001 to 010 | 7 | Broadcast Message uses a raw textarea; no shared `Textarea` | AC-FORM-001 to 010 | `IMPLEMENTED_VERIFIED` (modal and toolbar controls intentionally unchanged, see Package 7 audit) |
| G5 | Gym and workforce management API | 1 | `/admin/gym-locations`, `/workforce/assignments` | `test_gym_locations.py` | `IMPLEMENTED_VERIFIED` |
| G5 | Gym and workforce management in the web app, FR-OPS-015 | 6 | `AdminBranchesPage` (`778b8cb`) | typecheck and build only; not exercised in a browser | `IMPLEMENTED_UNTESTED` |
| G5 | Owner branch selector and per-branch comparison cards, FR-OPS-012, FR-OPS-013 | 6 | Branch selector and branch cards (`778b8cb`) | Playwright | `IMPLEMENTED_VERIFIED` |
| G6 | Scanner bound to a gym; member membership checked against that gym; occupancy and cache per gym | 2 | Scanner service, `AttendanceService` | `test_attendance_gym_isolation.py` | `IMPLEMENTED_VERIFIED` |
| G6 | Rotating QR visible on the dashboard with refresh and countdown, FR-DASH-007 to 010 | 5 | `EmbeddedQr`, `useRotatingQr` | Playwright rotation test | `IMPLEMENTED_VERIFIED` |
| G6 | Cross-gym manual close denied | 2 | `GymScopeService.require_access` | `test_attendance_gym_isolation.py` | `IMPLEMENTED_VERIFIED` |
| All | Role matrix, ERD, API reference, demo flow, verification record, FR-DOC-001 to 011 | 8 | `roles.md` has no gym scope (finding G-07) | AC-DOC-001 to 006 | `PARTIALLY_IMPLEMENTED` (documents written and checked against code and a seeded run; companion files used for architecture and route map; see Package 8 record) |
| G6 | Scanner app shows its gym and explains gym refusals, FR-SCN-001 to 004 | 9 | `scanner-mobile` `DeviceInfo`, header, `errors.ts` | `api.test.mjs`, `errors.test.mjs`, `state.test.mjs` (15 pass); not run on a device | `IMPLEMENTED_VERIFIED` (unit level), `IMPLEMENTED_UNTESTED` on device |
| G1, G3 | Member mobile app shows and chooses the gym, FR-MOB-001 to 008 | 10 | `mobile/src/lib/gyms.ts`, `api.ts`, `query.ts`, `types.ts`, dashboard, QR, classes, renew and payment-result screens | AC-MOB-002, 003, 004 and 006 by `mobile/tests/gyms.test.mjs`; AC-MOB-001 and 005 by code reading only | `PARTIALLY_IMPLEMENTED` |
| Post | New-member questionnaire, rule-based gym and quiet-hours recommendation, aggregate owner insights (min group 5), FR-ONB | 12 | `OnboardingService`, `features/onboarding`, mobile onboarding screen, migration `0023` | `test_onboarding_rules.py`, `test_onboarding.py` (backend not run); `mobile/tests/onboarding.test.mjs` pass | `IMPLEMENTED_UNTESTED` |
| Post | Expired members see renew or change-gym options; per-gym separation of manager and staff data, FR-EXP, FR-SEP | 13 | `ExpiredMembershipPanel`, `renewalIntent.ts`, `gym_member_clause` in CRM, requests, staff accounts, shifts | `renewalIntent.test.mjs` pass; `test_workforce_gym_separation.py` (not run). Known gap: audit logs are not gym-scoped | `PARTIALLY_IMPLEMENTED` |

"Verified" for Packages 1 to 4 means the named test files exist and the full backend suite (209 tests) passed on 2026-11-09. It does not mean every assertion in those files was re-audited.

## Task coverage check

Every functional requirement in Packages 5 to 7 is closed by at least one task, and every task names the requirements it closes. When a task or requirement is added, update the matrix row and keep the IDs stable.
