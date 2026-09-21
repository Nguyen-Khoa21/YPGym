# Post-Day-60 requirements

Created September 20, 2026 and revised September 21, 2026 for the owner-approved YPTrain scope. The BRD identifiers FR1–FR39 remain unchanged. FR40–FR55 were reserved by the first post-Day-60 slice; FR56 is the next unused identifier. The former YPFood meanings for FR45–FR51 are cancelled rather than implemented. Status describes the current repository, not the intended roadmap.

| ID | Requirement | Current status | Planned feature slice |
|---|---|---|---|
| FR40 | Reliable mobile back navigation, session restoration and logout | Verified in Feature 1 on an Android emulator; physical-device and iOS verification remain pending | Feature 1 |
| FR41 | Mobile membership purchase/renewal/cancellation state consistency | Implemented in Feature 1 for server-state refresh, status messaging, QR eligibility and renewal cache updates; mobile lifecycle-request UI remains Feature 3 | Features 1 and 3 |
| FR42 | Upcoming booked-class reminders and notification navigation | Planned | Feature 3 |
| FR43 | Individual manager-created staff and trainer accounts | Planned | Feature 10 |
| FR44 | Staff clock-in/clock-out records and manager reporting | Planned | Feature 10 |
| FR45 | Admin machine/exercise catalogue management | Planned | Feature 5 |
| FR46 | Upper/lower exercise browse and search | Planned | Feature 5 |
| FR47 | Guided exercise logging with 1–10 sets, reps and weight | Planned | Feature 6 |
| FR48 | Attendance-linked workout session per gym-local calendar date | Planned | Feature 6 |
| FR49 | Workout history calendar and same-exercise comparisons | Planned | Feature 7 |
| FR50 | Weekly front/back muscle heatmap | Planned | Feature 7 |
| FR51 | Guarded AI weekly training review | Architecture/provider decision required before live integration | Feature 8 |
| FR52 | Live gym equipment/exercise guide | Planned as the shared YPTrain catalogue | Feature 5 |
| FR53 | Registration welcome email through configurable SMTP delivery | Planned; live delivery remains credential gated | Feature 4 |
| FR54 | Consistent action success/error feedback and real-time UI refresh | Partially implemented in Features 1–2 and existing connected clients; later mutation corrections remain | Features 1, 2, 10 and 11 |
| FR55 | White-and-green workout-oriented responsive design system | Verified in Feature 2 across shared mobile components/member routes and the web foundation; physical-device and iOS verification remain pending | Feature 2 and later UI slices |
| FR56 | Previous-month attendance-based membership discount | Business combination/consumption policy required before implementation | Feature 9 |

## Feature 1 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR40 | `mobile/src/lib/session.ts`, `mobile/src/lib/navigation.ts`, `mobile/src/lib/auth.tsx`, route-aware `PageTop` fallbacks | `mobile/tests/reliability.test.mjs`; mobile typecheck, lint, tests and Android export |
| FR41 | `mobile/src/lib/query.ts`, fresh dashboard reads on membership screens, server-status labels on dashboard/profile/QR/renewal, unchanged server-issued rotating QR | Mobile state-transition test plus backend purchase/idempotency/lifecycle/JWT integration suite |

The current backend has no logout or token-revocation endpoint. Feature 1 therefore clears SecureStore and both web storage fallbacks, removes member-scoped query data and replaces navigation with `/login`; it does not claim server-side access-token revocation. The existing access token remains bounded by its configured expiry.

## Feature 2 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR54 | Semantic mobile loading, empty, error and field-validation states; larger reusable web/mobile controls | Mobile typecheck/lint/tests/export plus connected screen and mutation regression |
| FR55 | `mobile/src/lib/theme.ts`, `mobile/src/components/ui.tsx`, all member routes, Expo light shell, web CSS tokens and shared web buttons | Contrast test, phone/tablet/desktop visual inspection, Android emulator inspection, web lint/build |

The YPTrain Features 5–9 replace all previously proposed food catalogue, cart, checkout, stock, delivery, review and payment work. No YPFood schema, API or client implementation exists or is planned.
