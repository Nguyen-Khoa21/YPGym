# Design Architecture Route-Screen Map

Primary UI references are the BRD Design Architecture document and its embedded My QR, Member CRM, Admin Member Details, Class Schedule, and Attendance Dashboard screenshots. The repository's shared forest/lime/cream design system supplies responsive web behavior where a live Figma frame is unavailable.

## Member and public routes

| Screen | Route | Role | API dependencies | Status through Day 42 |
|---|---|---|---|---|
| Home/auth/verification/reset | `/`, `/login`, `/register`, `/verify-email`, `/forgot-password`, `/reset-password` | Public | `/auth/*` | Connected |
| Membership plans/policy/purchase | `/memberships`, `/policies/membership`, `/memberships/buy/:planId` | Public/member | `/membership-plans`, `/memberships/purchase` | Connected; payment is explicitly mock-only |
| Member dashboard | `/app/dashboard` | Member | `/dashboard/me` | Connected composite with membership/QR, crowdedness, bookings/waitlists, notifications, broadcasts, quick actions, and complete account states |
| Profile | `/app/profile` | Authenticated | `/users/me`, notification preference link | Connected |
| Billing history | `/app/billing` | Authenticated | `/billing/me/payments`, `/billing/me/invoices`, PDF download | Connected |
| My QR | `/app/qr` | Member | `/attendance/qr-token/me`, `/attendance/crowdedness`, `/attendance/me` | Connected rotating QR, countdown, refresh, blocked/error states |
| Attendance history | `/app/attendance` | Member | `/attendance/me` | Connected paginated history and event/source context |
| Freeze/cancel requests | `/app/membership-requests` | Member | `/memberships/freeze-requests`, `/memberships/cancellation-requests`, `/memberships/requests/me` | Connected |
| Notifications | `/app/notifications` | Member | `/notifications/me`, read-one/read-all | Connected and paginated |
| Notification preferences | `/app/notifications/preferences` | Member | `/notifications/preferences/me` | Connected |
| Member class booking | `/app/classes` | Member | `/classes/upcoming`, `/classes/{id}/book`, waitlist join/leave | Connected responsive class cards, PT cards, capacity, eligible/ineligible, booked/full/waitlisted/cancelled states |
| My bookings | `/app/bookings` | Member | `/bookings/me`, booking cancel, waitlist leave | Connected confirmed/cancelled/promoted/waiting states and configured cancellation cutoff |

Aliases `/member`, `/profile`, and `/billing` redirect to their canonical `/app/*` routes.

## Operations routes

| Screen | Route | Role | API dependencies | Status through Day 42 |
|---|---|---|---|---|
| Role-specific operations home | `/admin` | Staff/manager/admin | Auth role | Connected navigation only to permitted areas |
| Member CRM | `/admin/members` | Admin | `/admin/members`, filtered CSV | Connected search, role/tier/status/expiry filters, KPI cards, table, pagination |
| Admin Member Details | `/admin/members/:id` | Admin | detail composite, decisions, revocation | Connected profile, membership, billing, attendance, booking summary, requests, audit, reasoned actions |
| Membership approvals | `/admin/approvals` | Manager/admin | `/admin/membership-requests`, decision endpoints | Connected limited queue without full CRM/billing exposure |
| Billing ledger | `/admin/billing` | Admin | `/admin/billing/payments`, `/invoices`, exact-filter CSV | Connected member/status/date/plan/tier filters |
| Attendance dashboard | `/admin/attendance` | Staff/manager/admin | attendance admin list, manual close, crowdedness; analytics for manager/admin | Connected table, filters, KPI cards, manual-close dialog, accessible 7x24 heatmap |
| Class schedule | `/admin/classes` | Admin | class list/trainers/create/update/cancel | Connected table, filters, side card, create/edit dialog, cancellation confirmation |
| Broadcasts | `/admin/broadcasts` | Manager/admin | broadcast list/create/update | Connected |
| Audit log | `/admin/audit` | Manager/admin | `/admin/audit-logs` | Connected date/action/actor/target/entity filters and pagination |
| Configuration | `/admin/settings` | Manager/admin | `/admin/configuration` | Connected validated editing and cache invalidation |
| PT profiles | `/admin/pt-assignments` | Manager/admin | `/admin/trainers`, `/admin/classes/trainers` | Connected create/edit/deactivate, active/inactive filters, assigned-class deactivation guard, confirmation, and audit |
| PT dashboard | `/pt/dashboard` | PT | Auth role | Intentionally lightweight protected landing page; payroll/client-programming scope is not fabricated |

## Attendance field mapping

| UI region | Server fields |
|---|---|
| QR pass | token, issued/expiry timestamps, TTL, effective membership status |
| Facility status | active count, configured capacity, percentage, threshold label, calculated timestamp |
| Member history | check-in/close timestamps, session status, source, device ID, ordered events |
| Operations log | member identity, date/status/member filters, source/device, manual-close reason |
| Analytics heatmap | 168 weekday/hour cells, visits today, busiest hour, current occupancy, selected range |

## Shared states and responsive behavior

- `AppFrame`, `MemberShell`, and role-filtered `AdminShell` provide skip links, identity/logout, a role-aware Workspace shortcut, desktop navigation, and member mobile bottom navigation.
- Operations pages share header, metrics, panels, status badges, pagination, dialogs, loading, empty, error, validation, and confirmation patterns.
- Protected routes wait for authentication resolution and redirect denied roles to `/permission-denied` without rendering protected data.
- Tables remain horizontally scrollable on narrow viewports; core member actions are reachable from mobile navigation.
- Class, booking, and dashboard pages use card grids that collapse to one column at mobile width; trainer management uses the same responsive operations shell.
- The BRD Member Dashboard, PT Assignment Management, Personal Trainer Dashboard, and mobile Class Booking exports were inspected. The current forest/lime/cream web system was preserved instead of copying the screenshots' unrelated chrome.

## Explicit scope boundaries

Days 39-42 are connected. Expo/mobile delivery begins at Day 43. Personalization, recommendations, AI chatbot expansion, live payment settlement, physical hardware firmware, and advanced PT business workflows remain outside this milestone.
