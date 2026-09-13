# YPGym Diagram Package

These diagrams describe the complete YPGym project target from the project proposal and the current repository. They are not limited to the implementation milestone through Day 42 or to the Day 43 mobile boundary.

Status styling is intentional:

- Green or blue solid shapes describe implemented project capabilities.
- Purple dashed shapes describe proposal or later-target capabilities.
- Gray dotted shapes describe external integrations or features explicitly outside the initial project scope.

## Editable Draw.io diagrams

| Diagram | Editable source | Embedded preview |
|---|---|---|
| Whole-project architecture | `ypgym-architecture.drawio` | `ypgym-architecture.drawio.png` |
| Whole-project use cases | `ypgym-use-case.drawio` | `ypgym-use-case.drawio.png` |
| Membership lifecycle state transition | `ypgym-membership-state-transition.drawio` | `ypgym-membership-state-transition.drawio.png` |
| PostgreSQL ERD | `ypgym-erd.drawio` | `ypgym-erd.drawio.png` |
| Domain relationships | `ypgym-domain-relationships.drawio` | `ypgym-domain-relationships.drawio.png` |

The PNG files contain embedded Draw.io XML. The `.drawio` files remain the clearest sources for manual editing and lecturer review.

The older `architecture.mmd`, `use-cases.mmd` and `membership-state.mmd` files are early planning sketches. Use the named `ypgym-*.drawio` package above for the current whole-project diagrams.

## Open the diagrams on Windows

Run these commands from the repository root:

```powershell
Start-Process .\docs\diagrams\ypgym-architecture.drawio
Start-Process .\docs\diagrams\ypgym-use-case.drawio
Start-Process .\docs\diagrams\ypgym-membership-state-transition.drawio
```

## Manual review checklist

### Architecture

1. Confirm the client layer contains the React web app, Expo/PWA target, IoT simulator and physical-hardware boundary.
2. Confirm the Docker platform shows FastAPI/security, domain services, repository, PostgreSQL, Redis, Celery, invoice and email responsibilities.
3. Confirm the chatbot and AI runtime are marked as later target scope.
4. Confirm live payment settlement and physical door hardware are not presented as implemented.

### Use cases

1. Confirm Member, Staff, Manager, Admin, Personal Trainer, IoT Scanner/Simulator and Scheduled Worker actors are present.
2. Confirm the system boundary covers account, membership, billing, QR attendance, crowdedness, classes, waitlists, notifications, CRM, reporting, audit and configuration.
3. Confirm role-sensitive operational use cases match the backend permission model.
4. Confirm the controlled chatbot and full PT workspace are visibly marked as later targets.

### Membership state transition

1. Trace the main path: Pending Verification -> Active -> Expiring Soon -> Expired.
2. Trace renewal, approved freeze, freeze-end, cancellation approval and revocation paths.
3. Confirm every transition label names the triggering Member, Manager/Admin, Admin or Scheduled Worker.
4. Confirm Cancellation Requested is documented as a logical request workflow state rather than a stored `MembershipStatus`.
5. Confirm Active and Expiring Soon are the only access-eligible states, while Cancelled and Revoked are terminal during lifecycle synchronization.

## Source authority

The diagrams reconcile:

- `YPGym_COMP1682_Project_Proposal.docx`
- `YPGym_60_Day_Development_Plan_Revised_PostgreSQL (1).md`
- `README.md`
- `docs/HANDOFF.md`
- `docs/design/route-screen-map.md`
- `docs/policies/membership-lifecycle.md`
- the current FastAPI, React, PostgreSQL, Redis, Celery and IoT simulator implementation
