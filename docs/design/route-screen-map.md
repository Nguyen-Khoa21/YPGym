# Design Architecture Route-Screen Map

Primary UI references are the BRD Design Architecture document and its embedded My QR, Member CRM, Admin Member Details, Class Schedule, and Attendance Dashboard screenshots. The post-Day-60 white, deep-green and light-green workout system in `workout-visual-system.md` supersedes the former dark/neon mobile palette and supplies responsive shared tokens where a live Figma frame is unavailable.

## Member and public routes

| Screen | Route | Role | API dependencies | Status through Day 42 |
|---|---|---|---|---|
| Home/auth/verification/reset | `/`, `/login`, `/register`, `/verify-email`, `/forgot-password`, `/reset-password` | Public | `/auth/*` | Connected |
| Required temporary-password replacement | `/change-password` | Authenticated workforce user | `/users/me` | Connected first-login gate; all other protected APIs remain blocked until replacement succeeds |
| OAuth callback/account linking | `/oauth/callback`, `/auth/link-account` | Public one-time flow | provider callback/exchange and pending-link password/email confirmation | Connected first-attempt callback guard, expiry/replay/collision states, and explicit ownership proof |
| Membership plans/policy/purchase | `/memberships`, `/policies/membership`, `/memberships/buy/:planId` | Public/member | `/membership-plans`, `/memberships/attendance-benefit/me`, `/payments/vnpay/create`, `/payments/{transaction_id}` | Connected; server-calculated previous-month attendance quote, better-of renewal pricing, VNPay checkout and server-confirmed result |
| Member dashboard | `/app/dashboard` | Member | `/dashboard/me` | Connected composite with membership/QR, crowdedness, bookings/waitlists, notifications, broadcasts, quick actions, and complete account states |
| Profile | `/app/profile` | Authenticated | `/users/me`, notification preference link | Connected |
| Billing history | `/app/billing` | Authenticated | `/billing/me/payments`, `/billing/me/invoices`, PDF download | Connected |
| My QR | `/app/qr` | Member | `/attendance/qr-token/me`, `/attendance/crowdedness`, `/attendance/me` | Connected rotating QR, countdown, refresh, blocked/error states |
| Attendance history | `/app/attendance` | Member | `/attendance/me` | Connected paginated history and event/source context |
| Freeze/cancel requests | `/app/membership-requests` | Member | `/memberships/freeze-requests`, `/memberships/cancellation-requests`, `/memberships/requests/me` | Connected |
| Notifications | `/app/notifications` | Member | `/notifications/me`, read-one/read-all | Connected and paginated |
| Notification preferences | `/app/notifications/preferences` | Member | `/notifications/preferences/me` | Connected |
| Account security | `/app/security` | Authenticated user | `/account/identities`, provider link/unlink | Connected provider status, explicit link/unlink, recent-auth and last-method states |
| Member class booking | `/app/classes` | Member | `/classes/upcoming`, `/classes/{id}/checkout`, `/payments/{id}`, waitlist join/leave | Connected per-session VND price, capacity/holds, non-member purchase, authoritative VNPay result, and booked/full/waitlisted/cancelled states |
| My bookings | `/app/bookings` | Member | `/bookings/me`, booking cancel, payment/invoice links, waitlist leave | Connected paid/legacy bookings, confirmation, cancellation, refund-required, promoted/waiting, and class-start cancellation cutoff |
| YPTrain exercise guide, workout history and weekly muscle map | `/app/train`, `/app/train/:id` | Member | `/training/exercises`, `/training/workouts/today`, `/training/workouts/history`, `/training/workouts/{date}`, `/training/workouts/muscle-map` | Shared upper/lower browse, guide and attendance-gated 1–10 set logging; contribution calendar distinguishes attendance from workouts; exact day detail, descriptive prior-session comparisons, accessible front/back weighted-set-exposure map and explicitly non-AI rule-based weekly balance derive from member-owned records |
| Mobile member shell | `mobile/src/app/` (Expo Router) | Member | Shared `/api/v1` auth, dashboard, attendance, classes, bookings, notifications, profile, billing, lifecycle requests and YPTrain | FR40/FR41 centralizes logout/reset, route-aware Back behavior, membership refresh, registration/verification and freeze/cancellation requests; FR42 adds persistent in-app class reminders that open the matching booking; YPTrain shares catalogue, attendance-linked logging, history, comparisons and muscle exposure with web; FR56 adds the server-derived attendance renewal quote and immutable billing result; FR54/FR55 supplies the responsive white/green shell and accessible states; physical phone/iOS remain unverified |

Aliases `/member`, `/profile`, and `/billing` redirect to their canonical `/app/*` routes.

## Operations routes

| Screen | Route | Role | API dependencies | Status through Day 42 |
|---|---|---|---|---|
| Role-specific operations home | `/admin` | Staff/manager/admin | Auth role | Connected navigation only to permitted areas |
| Member CRM | `/admin/members` | Manager/admin | `/admin/members`; admin-only filtered CSV | Connected search, role/tier/status/expiry filters, KPI cards, table, pagination |
| Admin Member Details | `/admin/members/:id` | Manager/admin | detail composite and manual enrollment; admin-only revocation | Connected profile, membership, billing, attendance, booking summary, requests, audit, reasoned actions |
| Membership approvals | `/admin/approvals` | Manager/admin | `/admin/membership-requests`, decision endpoints | Connected limited queue without full CRM/billing exposure |
| Billing ledger | `/admin/billing` | Admin | `/admin/billing/payments`, `/invoices`, product filters, manual class refund resolution, exact-filter CSV | Connected membership/class revenue, unpaid holds, provider/invoice references, and refund exceptions |
| Email delivery operations | `/admin/email-deliveries` | Manager/admin | `/admin/email-deliveries`, retry action | Connected masked recipient, invoice reference, honest delivery state, safe failure and audited retry |
| Attendance dashboard | `/admin/attendance` | Staff/manager/admin | attendance admin list, manual close, crowdedness; analytics for manager/admin | Connected table, filters, KPI cards, manual-close dialog, accessible 7x24 heatmap |
| Manager analytics summary | `/admin/attendance` (manager/admin panel) | Manager/admin | `/admin/analytics/summary` | Connected persisted membership trends, class popularity, attendance patterns, successful revenue, 60-second Redis freshness window; staff is denied |
| Class schedule | `/admin/classes` | Admin | class list/trainers/create/update/cancel | Connected session VND pricing, seat review, filters, create/edit dialog, and deterministic cancellation/refund flags |
| Broadcasts | `/admin/broadcasts` | Manager/admin | broadcast list/create/update | Connected |
| Audit log | `/admin/audit` | Manager/admin | `/admin/audit-logs` | Connected date/action/actor/target/entity filters and pagination |
| Configuration | `/admin/settings` | Manager/admin | `/admin/configuration` | Connected validated editing and cache invalidation |
| PT profiles | `/admin/pt-assignments` | Manager/admin | `/admin/trainers`, `/admin/classes/trainers` | Connected create/edit/deactivate, active/inactive filters, assigned-class deactivation guard, confirmation, and audit |
| YPTrain catalogue | `/admin/exercises` | Manager/admin | `/admin/training/exercises`, image upload | Shared record create/edit/archive/restore, search/filter, validated image replacement and audit |
| Workforce accounts and shift report | `/admin/staff` | Manager/admin | `/admin/staff-accounts`, `/admin/staff-shifts` | Connected one-time credential provisioning, PT linkage, search/role/status/local-date filters and pagination |
| Staff time clock | `/staff/time-clock` | Staff/PT | `/staff/shifts/me`, clock-in/out | Connected server UTC timestamps, one-open-shift constraint, audit and gym-timezone presentation |
| PT dashboard | `/pt/dashboard` | PT | Auth role | Intentionally lightweight protected landing page; payroll/client-programming scope is not fabricated |

## Attendance field mapping

| UI region | Server fields |
|---|---|
| QR pass | token, issued/expiry timestamps, TTL, effective membership status |
| Facility status | active count, configured capacity, percentage, threshold label, calculated timestamp |
| Member history | check-in/close timestamps, session status, source, device ID, ordered events |
| Operations log | member identity, date/status/member filters, source/device, manual-close reason |
| Analytics heatmap | 168 weekday/hour cells, visits today, busiest hour, current occupancy, selected range |
| Analytics summary | monthly membership status counts, class-type bookings/utilization, check-ins/unique members/visit duration, successful payment totals, generated timestamp/cache TTL |

## Native reference parity

BRD Figures19–24 (`docs/design/references/image19.png` through `image24.png`) map respectively to native Dashboard, Renewal Selection, Renewal Success, QR Check-in, Class Booking and Member Profile. All use the existing shared API. Actual synthetic account data, VND billing and server eligibility replace sample reference values; the four-position Dashboard/Check-in/Classes/Profile navigation is retained within the post-Day-60 white/green visual system. Native renewal is confirmed by the account-returned invoice, not a client-only success screen.

The native evidence index records each implementation path, actual captures, observed/fixed clipping and badge alignment, explicit scope exceptions, and pending acceptance cases. Profile initials replace an invented avatar; personalization is deferred. This is partial visual parity with documented exceptions, not a claim of pixel identity or fulfilled deferred features.

## Shared states and responsive behavior

- `AppFrame`, `MemberShell`, and role-filtered `AdminShell` provide skip links, identity/logout, a role-aware Workspace shortcut, desktop navigation, and member mobile bottom navigation.
- Canonical web paths live in `frontend/src/app/routes.ts`; typed public/member/operations navigation and client-side role visibility live in `frontend/src/app/navigation.ts`. These values drive links and frontend guards only. FastAPI remains the authorization authority.
- Web visual tokens remain in `frontend/src/index.css` and `frontend/tailwind.config.ts`; Expo tokens remain independently defined in `mobile/src/lib/theme.ts` because the platforms use different rendering and styling systems.
- Operations pages share header, metrics, panels, status badges, pagination, dialogs, loading, empty, error, validation, and confirmation patterns.
- Protected routes wait for authentication resolution and redirect denied roles to `/permission-denied` without rendering protected data.
- Tables remain horizontally scrollable on narrow viewports; core member actions are reachable from mobile navigation.
- Class, booking, and dashboard pages use card grids that collapse to one column at mobile width; trainer management uses the same responsive operations shell.
- The BRD Member Dashboard, PT Assignment Management, Personal Trainer Dashboard, and mobile Class Booking exports were inspected. The current forest/lime/cream web system was preserved instead of copying the screenshots' unrelated chrome.

## Explicit scope boundaries

Days 39–42 and the documented Day 43–60 release are connected. Post-Day-60 mobile reliability and the shared workout visual system are also connected; later YPTrain, guarded review, staff and discount slices remain governed by `docs/progress/post-day-60-yptrain.md`. Live payment settlement, physical hardware firmware and unapproved advanced PT business workflows remain outside this milestone.
