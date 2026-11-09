# Release Role Permission Matrix

| Capability | Member | Staff | Manager | Admin | PT |
|---|:---:|:---:|:---:|:---:|:---:|
| Own profile, billing, notifications, QR, attendance, lifecycle requests | Yes | No | No | No | Own profile only |
| Scanner check-in/check-out | Device credential | Device credential | Device credential | Device credential | No |
| Attendance history and manual close | Own history | Yes | Yes | Yes | No |
| Peak-hours analytics | No | No | Yes | Yes | No |
| Limited freeze/cancellation approval queue | No | No | Yes | Yes | No |
| CRM and member detail | No | No | Yes | Yes | No |
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
- Managers can review member CRM/detail records and create a reasoned manual membership enrollment. CRM CSV export, membership revocation, and the billing ledger remain admin-only.
- Sensitive changes and personal-data exports require audit records. Reasons are mandatory for lifecycle decisions, revocation, manual attendance closure, and class cancellation.
- Device API keys, passwords, JWTs, and QR token material are never returned in CRM, audit, or export payloads.
- Manager/admin trainer mutations are enforced by backend role dependencies; class scheduling remains admin-only.
- Booking, waitlist, cancellation, and dashboard endpoints are member-only and derive the user ID from the JWT. A member cannot cancel another member's booking.
- `/trainers/me` is PT-only and derives the linked profile from the current account. PTs cannot mutate trainer profiles, schedule classes or read admin fields through this route. Public trainer list/detail routes remain accessible without a role.
- Expo is a member client; operations and PT logins are rejected. This platform boundary does not weaken backend permissions.

## Gym scope and shift rule (multi-gym release)

The owner is the `admin` role in code, API and database. "Owner" is the business name. Manager, staff and PT accounts have exactly one active row in `workforce_gym_assignments`. Members use `user_memberships.home_gym_id`. The backend decides the gym through `GymScopeService`; the web app only hides controls.

| Role | Gym scope | Notes |
|---|---|---|
| Owner (`admin`) | All gyms | Picks a gym with `gym_id`. Some lists accept no gym and then cover every gym (attendance sessions, analytics summary, staff shifts, broadcasts). Others require one (crowdedness, peak hours: `422 GYM_SCOPE_REQUIRED`). The only role that sees revenue, billing ledger, class administration and branch management. |
| Manager | Assigned gym only | `gym_id` is optional. Naming another gym is `403`. No revenue in analytics, no billing ledger, no class administration. Can approve requests, read the CRM, run broadcasts and view analytics for the assigned gym. |
| Staff | Assigned gym, only while on shift | Attendance sessions and manual close return `403 SHIFT_REQUIRED` unless the staff member has an open shift at the assigned gym. Clock-in is at the assigned gym. No analytics. |
| PT | Assigned gym for shift clock-in | No attendance operations. Trainer workspace is unchanged. |
| Member | Home gym | Own QR, own attendance, home-gym crowdedness and traffic summary, class list for the home gym, chain-wide plus home-gym broadcasts. Choosing a gym at checkout does not change the home gym until payment succeeds. |

Cross-gym access by a non-owner returns `403`. A workforce account with no active assignment returns `403 GYM_ASSIGNMENT_REQUIRED`, and a member with no membership returns `403 GYM_MEMBERSHIP_REQUIRED`. An unknown or inactive gym returns `404`. Staff who are clocked in at one gym cannot operate another gym's attendance.

### Capability changes from the base matrix

| Capability | Staff | Manager | Owner |
|---|---|---|---|
| Attendance sessions list and manual close | Own gym, on shift | Own gym | Any gym, or all gyms for the list |
| Gym crowdedness and live occupancy | Own gym (the API does not check the shift; the web operations page does) | Own gym | One selected gym |
| Peak-hours analytics | No | Own gym | One selected gym |
| Analytics summary revenue | Not allowed | Hidden (field omitted) | Shown |
| Branch list, edit, workforce reassignment | No | No | Yes (`/admin/branches`) |
| Staff shift list (`/admin/staff-shifts`) | No | Own gym | Any gym |
| CRM list and member detail (`/admin/members`) | No | Own gym only (members whose latest membership is at the gym, plus the gym's workforce). Another gym's member is `403` | Any gym, or one chosen with `gym_id` |
| Membership requests list and freeze or cancellation decisions | No | Own gym; deciding another gym's request is `403` | Any gym |
| Staff account list (`/admin/staff-accounts`) | No | Own gym; each account shows its gym | Any gym, or one chosen with `gym_id` |
| Create staff or PT account | No | Forced to the own gym; naming another is `403` | Must choose a gym |
| Register a walk-in member (`POST /staff/members`) | Own gym, on shift | Own gym | Must send `gym_id` (`422` otherwise) |
| QR checkout or cash payment for a walk-in member | Own gym, on shift, only members registered in person whose membership (if any) is at the own gym | Same as staff | Any member |
| Poll a staff-created QR payment (`GET /staff/payments/{id}`) | Own gym, on shift | Own gym | Any gym |

Package 13 closed gaps where the CRM list and detail, membership requests, staff accounts and staff shifts were not yet limited to the manager's gym. Known remaining gap: the audit log (`/admin/audit-logs`) has no gym column and is still readable by managers across gyms; it needs a gym field on audit rows to be scoped.

The matching tests are `test_workforce_gym_separation.py`, `test_shift_and_scope_rules.py`, `test_attendance_gym_isolation.py`, `test_member_service_gym_isolation.py`, `test_gym_locations.py` and `test_analytics_storage.py` in `backend/app/tests/integration`. See [gym-aware endpoints](../api/gym-aware-endpoints.md) for the per-endpoint rules.
