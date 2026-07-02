# Design Architecture Route-Screen Map

Primary reference: `FYP Brief BRD - Anh Khoa - Design Architecture.docx`, section `10. Design Architecture`.

## Web and Admin Screens

| Screen | Route | API dependencies | Shared components | Status |
|---|---|---|---|---|
| YPGym Home Page | `/` | none initially | public nav, hero, cards, footer | pending |
| Register for YPGym | `/register` | `POST /auth/register` | auth shell, form fields, inline errors | implemented Day 12; exact screenshot unavailable in repo export, matched YPGym auth style |
| Login to YPGym | `/login` | `POST /auth/login` | auth shell, form fields, alert | implemented Day 14; exact screenshot unavailable in repo export, matched YPGym auth style |
| Forgot Password | `/forgot-password` | `POST /auth/forgot-password` | auth card, neutral success state | implemented Day 15; exact screenshot unavailable in repo export, matched YPGym auth style |
| Reset Password | `/reset-password?token=...` | `POST /auth/reset-password` | auth card, invalid/expired token error | implemented Day 15; derived from Forgot Password style |
| Email Verification Success | `/verify-email` and `/verify-email/success` | `GET /auth/verify-email` | success card, CTA | implemented Day 13; exact screenshot unavailable in repo export, matched success-card style |
| Profile Settings | `/profile` | `GET /users/me`, `PATCH /users/me` | member shell, profile form, security fields | implemented Day 16; derived from member profile design direction |
| Membership Plans | `/memberships` | `GET /membership-plans` | plan cards, CTA | implemented Day 18; exact screenshot unavailable in repo export, matched YPGym card hierarchy |
| Buy/Renew Membership | `/memberships/buy/:planId` | `POST /memberships/purchase` | plan summary, mock payment confirmation, success state | implemented Day 19; prepares mobile renewal state patterns |
| Membership Policies | `/policies/membership` | policy/config values | TOC sidebar, policy cards | pending |
| Payment and Invoice History | `/billing` | `GET /billing/me/payments`, `GET /billing/me/invoices`, invoice download | billing cards, invoice actions, empty/error states | implemented Day 20; exact screenshot unavailable in repo export, matched member billing style |
| Member Dashboard | `/member` | billing summary endpoints | member shell, KPI cards, quick actions | partial Day 20; invoice/payment summary connected, QR/classes placeholders retained |
| My QR Code | `/app/qr` | `GET /attendance/qr-token/me` | QR panel, timer, status card | pending |
| Web Class Booking | `/app/classes` | class list, booking, waitlist endpoints | member shell, class cards, filters | derived from mobile |
| Member CRM (Updated) | `/admin/members` | paginated member search | admin shell, KPI cards, TanStack Table | pending |
| Admin Member Details (Updated) | `/admin/members/:id` | member detail, billing, attendance, bookings | tabs/cards/action panel | pending |
| Class & Schedule Management (Updated) | `/admin/classes` | class CRUD, trainer list | admin shell, schedule cards, dialogs | pending |
| Attendance Dashboard | `/admin/attendance` | occupancy, attendance log, recent scans | KPI cards, facility status, tables | pending |
| PT Assignment Management | `/admin/pt-assignments` | PT profiles, assignments | assignment deck, trainer cards | pending |
| Personal Trainer Dashboard | `/pt/dashboard` | assigned classes, PT stats | PT shell, stat cards, schedule list | pending |
| Admin Billing Placeholder | `/admin/billing` | `GET /billing/admin/payments` | admin shell, simple billing table | partial Day 20; full Day 26 billing intentionally not built |

## Mobile Screens

| Screen | Route | API dependencies | Shared components | Status |
|---|---|---|---|---|
| Mobile Member Dashboard | `mobile/app/(tabs)/dashboard` | dashboard summary endpoint | mobile top bar, cards, bottom nav | pending |
| Mobile Membership Renewal Selection | `mobile/app/membership/renew` | plans, current membership | renewal card, plan cards, CTA | pending |
| Mobile Renewal Success | `mobile/app/membership/success` | payment result | success state, dashboard CTA | pending |
| Mobile QR Check-in | `mobile/app/(tabs)/qr` | QR token, attendance history | QR panel, timer, history link | pending |
| Mobile Class Booking | `mobile/app/(tabs)/classes` | class list, booking, waitlist | search/filter, class cards, states | pending |
| Mobile Member Profile | `mobile/app/(tabs)/profile` | profile, membership summary | profile header, menu rows, logout | pending |

## Day 5-10 State Expectations

- Every route must define loading, empty, API-error and permission-denied states before feature completion.
- The missing web Class Booking screenshot is an approved exception; derive it from mobile Class Booking and the web member layout.
- Day 11-20 auth, profile, membership, and billing screens are now implemented or partial as listed above.
- Exact exported screenshots for the Day 12-20 auth and billing screens were not available as standalone image files in this repository, so the implementation follows the existing YPGym sleek gym-style direction from the BRD/design notes and shared UI palette.
