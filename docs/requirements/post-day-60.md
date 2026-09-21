# Post-Day-60 requirements

Created September 20, 2026. The BRD identifiers FR1–FR39 remain unchanged. Repository search found no existing FR40–FR55 assignments, so this extension reserves the following identifiers. Status describes the current repository, not the intended roadmap.

| ID | Requirement | Current status | Planned feature slice |
|---|---|---|---|
| FR40 | Reliable mobile back navigation, session restoration and logout | Verified in Feature 1 on an Android emulator; physical-device and iOS verification remain pending | Feature 1 |
| FR41 | Mobile membership purchase/renewal/cancellation state consistency | Implemented in Feature 1 for server-state refresh, status messaging, QR eligibility and renewal cache updates; mobile lifecycle-request UI remains Feature 3 | Features 1 and 3 |
| FR42 | Upcoming booked-class reminders and notification navigation | Planned | Feature 3 |
| FR43 | Individual manager-created staff and trainer accounts | Planned | Feature 10 |
| FR44 | Staff clock-in/clock-out records and manager reporting | Planned | Feature 10 |
| FR45 | YPFood product, image, price, stock and active-state administration | Planned | Features 5 and 7 |
| FR46 | YPFood macros, supplement stack and configurable product options | Planned | Features 5, 7, 8 and 9 |
| FR47 | Shared server-backed cart for web and mobile | Planned | Features 6, 8 and 9 |
| FR48 | Transaction-safe YPFood checkout and inventory decrement | Planned | Features 6, 8 and 9 |
| FR49 | User ratings and written reviews with five-star maximum | Planned | Features 5, 8 and 9 |
| FR50 | Pickup-at-register and user-delivery fulfillment workflows | Planned | Features 6–9 |
| FR51 | Pickup payment-at-register and delivery card/mock-card rules | Planned; real gateway remains credential/provider gated | Features 6, 8 and 9 |
| FR52 | Web and mobile gym-equipment guide placeholder | Planned | Feature 12 |
| FR53 | Registration welcome email through configurable SMTP delivery | Planned; live delivery remains credential gated | Feature 4 |
| FR54 | Consistent action success/error feedback and real-time UI refresh | Partially implemented in the existing web/mobile clients and Feature 1 membership refresh; cross-platform completion remains planned | Features 1, 7, 8, 9 and 11 |
| FR55 | White-and-green workout-oriented responsive design system | Planned; the existing released mobile theme is still dark/lime | Feature 2 and later UI slices |

## Feature 1 traceability

| Requirement | Implementation | Verification |
|---|---|---|
| FR40 | `mobile/src/lib/session.ts`, `mobile/src/lib/navigation.ts`, `mobile/src/lib/auth.tsx`, route-aware `PageTop` fallbacks | `mobile/tests/reliability.test.mjs`; mobile typecheck, lint, tests and Android export |
| FR41 | `mobile/src/lib/query.ts`, fresh dashboard reads on membership screens, server-status labels on dashboard/profile/QR/renewal, unchanged server-issued rotating QR | Mobile state-transition test plus backend purchase/idempotency/lifecycle/JWT integration suite |

The current backend has no logout or token-revocation endpoint. Feature 1 therefore clears SecureStore and both web storage fallbacks, removes member-scoped query data and replaces navigation with `/login`; it does not claim server-side access-token revocation. The existing access token remains bounded by its configured expiry.
