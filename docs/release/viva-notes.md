# Viva notes

- **PostgreSQL:** It is the source of truth for members, memberships, billing, classes, bookings, attendance, audit logs, and configuration. Constraints and transactions protect ownership, capacity, uniqueness, and immutable invoice history.
- **Redis:** It handles short-lived QR replay state, occupancy/configuration projections, bounded analytics freshness, and fixed-window abuse limits. Redis can be discarded and rebuilt from PostgreSQL state where the design permits.
- **Docker separation:** API, worker/beat, web, PostgreSQL, and Redis have isolated responsibilities and repeatable Compose startup.
- **IoT scanner safety:** A device ID and API key authenticate scanner requests; the backend validates rotating signed QR tokens, rejects replay/duplicate scans, and records device/source evidence.
- **Rotating QR:** Tokens carry short expiry and a server-tracked active JTI, so a newer token supersedes an old screenshot.
- **Occupancy:** Check-out, timeout, and manual close update persisted sessions; the occupancy projection is recalculated from active PostgreSQL sessions.
- **Auditability:** Sensitive membership, class, configuration, export, broadcast, and attendance actions write actor, target, reason, outcome, and timestamp data.
- **JWT/RBAC:** JWTs identify the account; backend role dependencies enforce member, staff, manager, admin, and PT boundaries on every protected route.
- **Design architecture:** The route map records live API dependencies, responsive state coverage, screenshot references, and documented exceptions instead of claiming pixel parity without evidence.
- **Scale story:** The September 16 query review populated the local database with 1,000 users, memberships, attendance sessions and related rows. CRM and attendance pages stayed bounded and disjoint with fixed query counts; billing/audit export scale and deep-page limits remain unmeasured, so this is a query-shape review rather than a capacity claim. See `docs/release/performance-report.md` and `docs/release/query-review-september16.json`.
- **Mobile evidence:** The Android emulator rehearsal verified member dashboard, QR recovery after API loss, renewal/invoice, classes, booking/cancellation, session restore/expiry, logout persistence and operations-role denial. Full WCAG, physical-phone and iOS coverage remains outside the recorded evidence.
