# YPGym Diagram Package

These diagrams describe the implemented release and explicitly marked future scope. Source authority is the available BRD/Design Architecture document, revised development plan, and inspected repository. The separate project proposal document was not found; it has not been read or independently reconciled.

Status styling is intentional:

- Green or blue solid shapes describe implemented project capabilities.
- Purple dashed shapes describe proposal or later-target capabilities.
- Gray dotted shapes describe external integrations or features explicitly outside the initial project scope.

## Editable Draw.io diagrams

| Diagram | Editable source | Embedded preview |
|---|---|---|
| Whole-project architecture | `ypgym-architecture.drawio` | `ypgym-architecture.drawio.png` |
| YPGym-branded architecture overview | `ypgym-architecture.html` | Standalone browser diagram |
| Whole-project use cases | `ypgym-use-case.drawio` | `ypgym-use-case.drawio.png` |
| Membership verification reconciliation | `ypgym-membership-state-transition.drawio` | `ypgym-membership-state-transition.drawio.png` |
| Membership coverage and freeze | `ypgym-membership-coverage-state-transition.drawio` | `ypgym-membership-coverage-state-transition.drawio.png` |
| Membership cancellation and revocation | `ypgym-membership-terminal-state-transition.drawio` | `ypgym-membership-terminal-state-transition.drawio.png` |
| Historical VNPay payment lifecycle (retired; see `docs/api/payos-payments.md` for the active contract) | `ypgym-vnpay-payment-state-transition.drawio` | `ypgym-vnpay-payment-state-transition.drawio.png` |
| Class booking and payment hold | `ypgym-class-booking-payment-state-transition.drawio` | `ypgym-class-booking-payment-state-transition.drawio.png` |
| Class, waitlist and refund | `ypgym-class-waitlist-refund-state-transition.drawio` | `ypgym-class-waitlist-refund-state-transition.drawio.png` |
| Attendance session lifecycle | `ypgym-attendance-session-state-transition.drawio` | `ypgym-attendance-session-state-transition.drawio.png` |
| QR token lifecycle | `ypgym-qr-token-lifecycle.drawio` | `ypgym-qr-token-lifecycle.drawio.png` |
| Registration and email verification | `ypgym-registration-verification-state-transition.drawio` | `ypgym-registration-verification-state-transition.drawio.png` |
| PostgreSQL ERD | `ypgym-erd.drawio` | `ypgym-erd.drawio.png` |
| Domain relationships | `ypgym-domain-relationships.drawio` | `ypgym-domain-relationships.drawio.png` |
| Backend UML class diagram | `ypgym-backend-uml.drawio` | `ypgym-backend-uml.drawio.png` |

The PNG files contain embedded Draw.io XML. The `.drawio` files remain the clearest sources for manual editing and lecturer review.

The state-transition package is indexed in `ypgym-state-transition-index.md`. Its verified transition tables are in `ypgym-state-transition-tables.md`, and its audit findings and limitations are in `ypgym-state-transition-audit.md`. Every state diagram also has a synchronized `.mmd` source rendered and syntax-checked with Pretty Mermaid.

`architecture.mmd` and `use-cases.mmd` provide compact topology/use-case sketches. `backend-uml.mmd` is the authoring source for the representative UML subset: booking, trainer and attendance services/repositories plus their domain entities. The detailed ERD covers the complete durable schema. Use the named `ypgym-*.drawio` package above for editable review. Sources and embedded previews are versioned; only editor backups are ignored.

## Open the diagrams on Windows

Run these commands from the repository root:

```powershell
Start-Process .\docs\diagrams\ypgym-architecture.drawio
Start-Process .\docs\diagrams\ypgym-use-case.drawio
Start-Process .\docs\diagrams\ypgym-membership-state-transition.drawio
```

## Manual review checklist

### Architecture

1. Confirm the client layer contains the implemented React web/PWA and Expo member app, IoT simulator and physical-hardware boundary.
2. Confirm the Docker platform shows FastAPI/security, domain services, repository, PostgreSQL, Redis, Celery, invoice and email responsibilities.
3. Confirm the chatbot and AI runtime are marked as later target scope.
4. Confirm live payment settlement and physical door hardware are not presented as implemented.

### Use cases

1. Confirm Member, Staff, Manager, Admin, Personal Trainer, IoT Scanner/Simulator and Scheduled Worker actors are present.
2. Confirm the system boundary covers account, membership, billing, QR attendance, crowdedness, classes, waitlists, notifications, CRM, reporting, audit and configuration.
3. Confirm role-sensitive operational use cases match the backend permission model.
4. Confirm the PT's own read-only profile/next-three assigned classes are implemented; chatbot and advanced PT programming remain deferred.
5. Confirm scanner actions belong to the device-authenticated scanner actor; staff attendance-desk access does not grant scanner credentials.

### Membership state transitions

1. Trace verification reconciliation between Pending Verification and each dated non-terminal state.
2. Trace date-driven coverage, renewal, approved freeze, freeze-end and expiry in the coverage diagram.
3. Trace cancellation approval and admin revocation in the terminal-state diagram.
4. Confirm Cancellation Requested is documented as a separate request workflow rather than a stored `MembershipStatus`.
5. Confirm Active and Expiring Soon are the only access-eligible states, while Cancelled and Revoked are terminal during lifecycle synchronization.

## Source authority

The diagrams reconcile:

- `FYP Brief BRD - Anh Khoa - Design Architecture.docx` (including Section 7 FR1–FR39)
- `YPGym_60_Day_Development_Plan_Revised_PostgreSQL (1).md`
- `README.md`
- `docs/HANDOFF.md`
- `docs/design/route-screen-map.md`
- `docs/policies/membership-lifecycle.md`
- the current FastAPI, React, PostgreSQL, Redis, Celery and IoT simulator implementation
