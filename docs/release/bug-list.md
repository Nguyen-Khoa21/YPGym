# Release bug list

The categorized list is maintained in [`feature-freeze.md`](feature-freeze.md). This file is a short review entry point for the remaining release gates:

- **High:** complete six-screen native/session/parity evidence and interactive Day59 rehearsal; dashboard/QR/classes/bookings/cancel/rebook are now captured, fresh Compose/migrations/seed/HTTP checks pass. Proposal/UAT/research evidence remains unavailable and honestly labelled.
- **High:** native QR retry after failed foreground refresh was stuck hidden; shared guarded callback is implemented and exact post-Fast-Refresh regression remains to close.
- **Resolved:** twelve frontend dependency advisories were patched through compatible lockfile updates; fresh host install/lint/build/audit and demo image rebuild pass with frontend audit 0.
- **Medium:** Expo transitive advisories and future deep-page/large-export scale limits. The 1,000-user query/page review and Day53 CSV/configuration checks are now measured/passing; billing/audit scale is not inferred from empty benchmark tables.
- **Low:** existing frontend bundle-size and TanStack compiler warnings, plus the expected empty default analytics window for old seed rows.

No item above is silently treated as verified. The Day43–60 tracker is the status source for acceptance claims.
