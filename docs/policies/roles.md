# Release Role Permission Matrix

| Capability | Member | Staff | Manager | Admin | PT |
|---|:---:|:---:|:---:|:---:|:---:|
| Own profile, billing, notifications, QR, attendance, lifecycle requests | Yes | No | No | No | Own profile only |
| Scanner check-in/check-out | Device credential | Device credential | Device credential | Device credential | No |
| Attendance history and manual close | Own history | Yes | Yes | Yes | No |
| Peak-hours analytics | No | No | Yes | Yes | No |
| Limited freeze/cancellation approval queue | No | No | Yes | Yes | No |
| Full CRM and member detail | No | No | No | Yes | No |
| Sensitive billing and CSV export | No | No | No | Yes | No |
| Broadcast administration | No | No | Yes | Yes | No |
| Audit log | No | No | Yes | Yes | No |
| Operational configuration | No | No | Yes | Yes | No |
| Membership revocation | No | No | No | Yes | No |
| Admin class CRUD | No | No | No | Yes | No |
| PT profile maintenance | No | No | Yes | Yes | Read own linked profile only |
| Own trainer workspace and next-three assignments | No | No | No | No | Yes |
| Browse trainers/classes | Yes | No | No | No | Public trainer list |
| Own class booking/waitlist/cancellation | Yes | No | No | No | No |
| Own integrated member dashboard | Yes | No | No | No | No |

## Enforcement rules

- Every protected API uses current-user or explicit role dependencies. Scanner endpoints instead require the registered device ID and API key.
- Protected React routes mirror server roles. Role-specific navigation omits inaccessible areas; direct access resolves to `/permission-denied`.
- Managers can decide membership requests from `/admin/approvals` without access to full CRM or billing.
- Sensitive changes and personal-data exports require audit records. Reasons are mandatory for lifecycle decisions, revocation, manual attendance closure, and class cancellation.
- Device API keys, passwords, JWTs, and QR token material are never returned in CRM, audit, or export payloads.
- Manager/admin trainer mutations are enforced by backend role dependencies; class scheduling remains admin-only.
- Booking, waitlist, cancellation, and dashboard endpoints are member-only and derive the user ID from the JWT. A member cannot cancel another member's booking.
- `/trainers/me` is PT-only and derives the linked profile from the current account. PTs cannot mutate trainer profiles, schedule classes or read admin fields through this route. Public trainer list/detail routes remain accessible without a role.
- Expo is a member client; operations and PT logins are rejected. This platform boundary does not weaken backend permissions.
