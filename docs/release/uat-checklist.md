# UAT checklist

This is a repeatable task sheet, not a fabricated study result. Leave participant names, dates, ratings, and SUS scores blank until real evaluators complete the tasks.

| ID | Role | Task | Expected result | Participant / date | Result / notes |
|---|---|---|---|---|---|
| UAT-01 | Member | Sign in, inspect membership, open rotating QR | Membership and eligibility come from the authenticated account; QR shows expiry and blocked states |  |  |
| UAT-02 | Member | Search and book a class, then cancel inside the configured window | Booking state and cancellation cutoff are server-enforced |  |  |
| UAT-03 | Member | Open attendance, invoices, notifications, and profile | Each page shows only the authenticated member's persisted records |  |  |
| UAT-04 | Staff | Open attendance operations and manually close an active session | Staff can operate attendance but cannot open manager analytics |  |  |
| UAT-05 | Manager | Review peak hours and analytics summary | Persisted aggregates render and repeat request stays within the documented cache window |  |  |
| UAT-06 | Admin | Review CRM, billing/export, audit, classes, and configuration | Admin-only controls require role authorization and audit sensitive actions |  |  |
| UAT-07 | PT | Open the trainer dashboard and assigned classes | PT sees only the protected trainer landing flow |  |  |
| UAT-08 | Mobile member | Launch Expo app, restore session, open dashboard, QR, classes, and profile | Native screens use the same backend and handle offline/401 states |  |  |

No participant count or SUS score is claimed by this repository until this sheet is completed with real data.
