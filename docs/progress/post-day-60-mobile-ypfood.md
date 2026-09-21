# Post-Day-60 mobile and YPFood tracker

Updated September 20, 2026. This tracker covers the post-Day-60 roadmap only. The completed Day 42–60 release remains recorded separately in `day-43-60-tracker.md`.

## Discovery baseline

- Repository: `C:\Users\Admin\ypgym`, branch `main`, upstream `origin/main`, remote `https://github.com/Nguyen-Khoa21/YPGym.git`.
- Starting HEAD and remote: `451f0d3a5731a99bd7930ba18c4f7a7e7aca72d8`; annotated tag `v0.60.1`; branch was synchronized at discovery.
- No merge or rebase state was present. User-owned `README.md`, `RUN_GUIDE.md` and `tmp/` work was preserved and excluded from this slice.
- Alembic is at `20260723_0007 (head)` and `alembic check` reports no new upgrade operations. Normal PostgreSQL/Redis dependency health is `ok`.
- Fresh web baseline: lint passed with the existing TanStack Table React Compiler warning; production build passed with the existing 739.63 kB bundle warning.
- Fresh mobile baseline before editing: typecheck, lint, two QR tests and Android export passed. Expo Doctor reported 20/21 because four installed SDK 57 packages are one patch behind current compatibility recommendations: `@expo/ui`, `expo`, `expo-constants` and `expo-router`. No dependency was silently upgraded in Feature 1.
- Fresh isolated backend: 102 passed with five existing Starlette deprecation warnings in 67.27 seconds. Final mobile typecheck/lint, six Node tests and Android export pass. The normal Android emulator login/status/QR/logout/restart journey also passed; physical phone and iOS remain unverified.

## Existing dependency map

| Capability | Mobile/web client | API/service/repository/state |
|---|---|---|
| Authentication/session | Mobile `auth.tsx`; web `AuthContext`/`ProtectedRoute` | `/auth/register`, `/verify-email`, `/login`, `/me`, forgot/reset; `AuthService`, token/user repositories, PostgreSQL JWT identity; no logout endpoint |
| Membership and billing | Mobile dashboard/renew/invoices; web membership/billing pages | `/membership-plans`, `/memberships/purchase`, lifecycle request/admin decision routes, `/billing/me/*`; membership/billing services and repositories; PostgreSQL transaction plus immutable invoice metadata |
| Attendance and QR | Mobile dashboard/QR/attendance; web member/operations attendance | `/attendance/qr-token/me`, member/admin attendance, scanner and crowdedness routes; PostgreSQL source of truth and Redis short-lived QR/occupancy state |
| Classes and trainers | Mobile classes/bookings; web member/admin/PT pages | class/trainer/booking/waitlist routes; class/trainer services and repositories; PostgreSQL row locking and waitlist rules |
| Notifications/broadcasts | Mobile inbox/preferences/dashboard; web member/manager pages | notification/preference/broadcast routes; `NotificationService`; PostgreSQL records and Celery expiry-reminder schedule |
| UI feedback/cache | React Native alerts/messages and TanStack Query; web Sonner and TanStack Query | Per-feature query keys and mutation invalidation; Feature 1 centralizes member session cleanup and membership refresh roots |
| Development email | Web auth entry; no native registration yet | `AuthService` writes privacy-sensitive verification/reset messages to ignored Maildir in development; external SMTP delivery is not implemented |

## Feature slices

| Slice | Requirement IDs | Status | Evidence / boundary |
|---|---|---|---|
| 1. Mobile reliability and membership state | FR40, FR41, part of FR54 | Verified | Session/navigation/state code; 102 backend tests, six mobile tests, typecheck/lint/export and Android logout/restart journey pass |
| 2. White/green workout design system | FR55 | Not started | Must replace the former dark/lime direction after Feature 1 push decision |
| 3. Complete mobile journey and class reminders | FR41, FR42 | Not started | Native registration/lifecycle requests and reminder persistence remain |
| 4. Welcome email | FR53 | Not started | Provider-neutral implementation precedes mandatory live-credential checkpoint |
| 5. YPFood catalog foundation | FR45, FR46, FR49 | Not started | Requires forward migration and backend vertical slice |
| 6. YPFood cart/checkout/stock | FR47, FR48, FR50, FR51 | Not started | Requires server-authoritative totals, row locking and idempotency |
| 7. YPFood admin | FR45, FR46, FR54 | Not started | Depends on Features 5–6 |
| 8. YPFood web shop | FR46–FR51, FR54–FR55 | Not started | Depends on Features 5–7 |
| 9. YPFood mobile shop | FR46–FR51, FR54–FR55 | Not started | Depends on Features 5–8 |
| 10. Staff accounts and time clock | FR43, FR44 | Not started | Requires migration, RBAC, audit and first-login policy |
| 11. Management UX corrections | FR43, FR54–FR55 | Not started | Reuses the current Sonner/query patterns and Feature 10 accounts |
| 12. Equipment placeholder | FR52, FR55 | Not started | Shared honest demo catalogue; no workout tracking schema |
| 13. Integrated release checkpoint | FR40–FR55 | Not started | Begins only after all functional slices and push gates |

## Scope controls

- Each slice is committed separately and waits for explicit push permission before the next slice starts.
- FR39 chatbot, recommendations, personalization, workout programming and exercise-progress tracking remain out of scope.
- Live payment, SMTP credentials, Expo push credentials, public deployment and app-store release remain credential or environment gated.
- Physical phone, iOS and human UAT are not inferred from emulator, export or automated checks.
