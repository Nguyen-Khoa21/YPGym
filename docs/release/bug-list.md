# Release bug list

The categorized list is maintained in [`feature-freeze.md`](feature-freeze.md). This file is a short review entry point for the remaining release gates:

- **Resolved:** six-screen Android member/session evidence and interactive Day59 rehearsal were completed September 16, including the final QR offline/background/foreground/retry regression. Physical phone/iOS and full accessibility evaluation remain unverified.
- **Resolved:** September 17 release review added the FR1–FR39 platform matrix, actual API/PT/table mappings and editable UML, and corrected stale architecture/use-case labels. The old local archive contains runtime invoice PDFs and is superseded by the filtered package documented in `archive-inventory.md`.
- **High academic gap:** the separate proposal artifact, participant UAT and required research evidence remain unavailable. These are unfulfilled submission evidence requirements, not passing software checks.
- **Resolved:** twelve frontend dependency advisories were patched through compatible lockfile updates; fresh host install/lint/build/audit and demo image rebuild pass with frontend audit 0.
- **Medium:** Expo transitive advisories and future deep-page/large-export scale limits. The 1,000-user query/page review and Day53 CSV/configuration checks are now measured/passing; billing/audit scale is not inferred from empty benchmark tables.
- **Low:** existing frontend bundle-size and TanStack compiler warnings, plus the expected empty default analytics window for old seed rows.

No item above is silently treated as verified. The Day43–60 tracker is the status source for acceptance claims.
