# Role Permission Matrix

| Role | Allowed actions | Restricted actions |
|---|---|---|
| `member` | Manage own profile, membership, QR, attendance history, class bookings, waitlist, notifications and invoices. | Cannot view other members, admin billing exports, audit logs or scanner management. |
| `staff` | Use scanner flow, verify attendance state, close attendance sessions with reason if approved. | Cannot access full CRM, billing exports, policy configuration or manager analytics. |
| `manager` | Review analytics, approve cancellations, update operational configuration, review audit logs. | Cannot bypass audit logging or directly mutate database records. |
| `admin` | Full CRM, member details, class management, PT management, billing, exports, audit review and revocation actions. | Cannot perform sensitive actions without reason/audit trail. |
| `pt` | Maintain trainer profile and view assigned classes. | Cannot access member billing, CRM exports or system configuration. |

## Implementation Rules

- Every protected API must use a current-user dependency and role check.
- UI routes must show a permission-denied state instead of leaking unavailable data.
- Sensitive admin, manager and staff actions must write audit logs.

