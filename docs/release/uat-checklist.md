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

## Adapted SUS-style questionnaire

Administer after each participant's applicable tasks. Use anonymous codes; record platform, role, tasks, date and qualitative issues. Obtain applicable consent/ethics approval through the project process; none is claimed here. Five real participants and a mean score of 68 are proposal commitments, not current results.

These statements are adapted for YPGym, **not the verbatim validated System Usability Scale**. Disclose the adaptation and agree the instrument with the supervisor before collecting data. If standard SUS is required, use the approved original instrument instead; do not claim this wording is equivalent.

Responses: 1 Strongly disagree, 2 Disagree, 3 Neither, 4 Agree, 5 Strongly agree. Leave unanswered items blank.

| Item | Adapted statement | Response 1–5 |
|---|---|---|
| 1 | I would choose YPGym regularly for my relevant gym tasks. |  |
| 2 | These tasks felt more complicated than necessary. |  |
| 3 | I could work out how to use the main screens easily. |  |
| 4 | I would need someone to guide me through this application. |  |
| 5 | The screens and actions worked together in a way I understood. |  |
| 6 | Similar actions behaved inconsistently across the application. |  |
| 7 | Other gym users could learn the main tasks quickly. |  |
| 8 | Using the application felt awkward during my tasks. |  |
| 9 | I felt confident about what each important action would do. |  |
| 10 | I needed substantial preparation before using the application. |  |

## Scoring and empty results

Score complete 1–5 responses only: odd items contribute `response − 1`; even items contribute `5 − response`. Sum all ten contributions and multiply by 2.5 (0–100, not task-success percentage). Arithmetic checks: all neutral yields 50; odd 5/even 1 yields 100; odd 1/even 5 yields 0. Report an adapted SUS-style score, mean over complete participants, and incomplete submissions separately. Do not substitute neutral values for missing responses. Fewer than five actual participants leaves the count target unmet regardless of mean.

| Anonymous code | Date | Platform / role | Tasks attempted / completed | Responses 1–10 | Adapted score | Comments |
|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |
|  |  |  |  |  |  |  |

Participants and responses: **not supplied**. Mean: **not calculated**. Findings and improvements: **await real data**. Empty rows are not participant records.
