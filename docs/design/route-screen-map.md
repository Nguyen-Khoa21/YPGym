# Design Architecture Route-Screen Map

Primary references:

- `FYP Brief BRD - Anh Khoa - Design Architecture.docx`, section `10. Design Architecture`.
- Figma `Untitled` (`XQ3HBuKBg9NpLxCqoCwUb9`), Page 1.
- Figma frame `Membership Policies` (`1:2`) and mobile `Member Profile` (`1:4176`).

## Current Web Routes

| Screen | Canonical route | Existing alias | API dependencies | Status |
|---|---|---|---|---|
| YPGym Home | `/` | none | none | redesigned; public shell and no mocked feature data |
| Register | `/register` | none | `POST /auth/register` | redesigned and connected |
| Login | `/login` | none | `POST /auth/login`, `GET /auth/me` | redesigned and connected; redirects by role |
| Forgot Password | `/forgot-password` | none | `POST /auth/forgot-password` | redesigned and connected |
| Reset Password | `/reset-password?token=...` | none | `POST /auth/reset-password` | redesigned and query-token compatible |
| Email verification callback | `/verify-email?token=...` | none | `GET /auth/verify-email` | redesigned and connected |
| Email verification success | `/verify-email/success` | none | callback outcome | redesigned success destination |
| Membership Policies | `/policies/membership` | none | none | implemented from Figma `1:2`; lifecycle-only sections marked as planned |
| Membership Plans | `/memberships` | none | `GET /membership-plans` | redesigned; price and benefits remain API-owned |
| Buy/Renew Membership | `/memberships/buy/:planId` | none | `POST /memberships/purchase` | redesigned; idempotency and billing/dashboard invalidation retained |
| Member Dashboard | `/app/dashboard` | `/member` | payment and invoice summaries | redesigned; QR/classes are honest planned states |
| Profile Settings | `/app/profile` | `/profile` | `GET /users/me`, `PATCH /users/me` | redesigned from Figma `1:4176`; blocked email edit preserved |
| Payment and Invoice History | `/app/billing` | `/billing` | `GET /billing/me/payments`, `GET /billing/me/invoices`, invoice download | redesigned and connected |
| My QR Code | `/app/qr` | none | attendance API not built | UI-only planned state; Day 30 |
| Class Booking | `/app/classes` | none | class API not built | UI-only planned state; Day 33 |
| Admin Dashboard | `/admin` | none | none | redesigned admin shell; no CRM mocks |
| Admin Billing | `/admin/billing` | none | `GET /billing/admin/payments` | redesigned and role protected |
| Member CRM | `/admin/members`, `/admin/members/:id` | none | CRM API not built | UI-only planned state; Day 26 |
| Attendance Operations | `/admin/attendance` | none | attendance API not built | UI-only planned state; Day 30 |
| Class Management | `/admin/classes` | none | class API not built | UI-only planned state; Day 33 |
| PT Assignments | `/admin/pt-assignments` | none | PT API not built | UI-only planned state; Day 35 |
| PT Dashboard | `/pt/dashboard` | `/pt` | PT API not built | redesigned safe placeholder; PT role only |
| Permission Denied | `/permission-denied` | none | auth role state | implemented for blocked protected routes |
| Not Found | `*` | none | none | implemented |

## Shared Design System

- `AppFrame`: public navigation, authenticated identity chip, keyboard skip link and logout action.
- `AuthShell`: responsive authentication composition with real forms and inline API errors.
- `MemberShell`: desktop sidebar and mobile bottom navigation, based on the Figma member-profile hierarchy.
- `AdminShell`: distinct operations sidebar for current billing and future CRM/attendance/class/PT screens.
- Visual foundations: forest green `--primary`, lime `--secondary`, cream background, Barlow Condensed display type and Manrope UI type.

## Intentional Differences And Gaps

- The accessible Figma file contains only the `Membership Policies` and `Member Profile` frames. Public auth, purchase, billing and admin routes use the same local design system rather than claiming unprovided Figma frame parity.
- Figma MCP reached its Starter-plan call limit during the 2026-07-15 audit, preventing additional current screenshots, asset exports and frame inspection.
- QR, crowdedness, classes, broadcasts, notifications, CRM and PT assignments are routes with explicit planned/unavailable states. They do not show simulated records or actions.
- Mobile/Expo screens remain separate work; this pass covers responsive web only.
