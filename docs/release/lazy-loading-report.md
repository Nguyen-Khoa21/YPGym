# Route-level lazy-loading report

Updated 2026-10-20 at commit `7f15109` plus the uncommitted route-splitting change described below.

## Scope

The measured high-value routes below now load through `React.lazy` while retaining their existing `ProtectedRoute` role checks:

| Route | Module | Allowed roles |
|---|---|---|
| `/admin/attendance` | `AdminAttendancePage` | staff, manager, admin |
| `/admin/exercises` | `AdminTrainingPage` | manager, admin |
| `/admin/billing` | `AdminBillingPage` | admin |
| `/admin/audit` | `AdminAuditPage` | manager, admin |
| `/app/train` and `/app/train/:id` | `MemberTrainingPage` | member |

Login, member dashboard, QR attendance and payment-result routes remain eager so authentication, entry and payment recovery do not depend on an additional route chunk.

One `Suspense` boundary in `frontend/src/app/App.tsx` provides the existing accessible `LoadingState` while a route module loads. Unexpected chunk failures reach `AppErrorBoundary`, which presents a safe reload action without exposing a stack trace in production.

## Production bundle comparison

Both measurements used `npm run build` in `frontend/` with Vite 7.3.6.

| Artifact | Before | After | Change |
|---|---:|---:|---:|
| Initial JavaScript | 828.00 kB | 771.83 kB | -56.17 kB (-6.8%) |
| Initial JavaScript gzip | 237.46 kB | 223.99 kB | -13.47 kB (-5.7%) |
| CSS | 45.97 kB | 45.97 kB | unchanged |

The build now emits these on-demand route chunks:

| Chunk | Minified | Gzip |
|---|---:|---:|
| Admin audit | 3.98 kB | 1.57 kB |
| Admin billing | 8.28 kB | 2.83 kB |
| Admin training | 9.75 kB | 3.19 kB |
| Admin attendance | 12.50 kB | 4.06 kB |
| Member training | 24.64 kB | 6.78 kB |

The initial bundle remains above Vite's 500 kB warning threshold. Further splitting should be driven by another bundle measurement rather than moving critical routes indiscriminately.

## Verification

- `npm run test`: 11 passed.
- `npm run lint`: passed with the existing TanStack Table compiler warning and no errors.
- `npm run build`: passed and emitted the chunks listed above.
- Headless Chromium loaded and refreshed every lazy route against the running API using the matching seeded role.
- A member navigating directly to `/admin/audit` was redirected to `/permission-denied`, confirming that code splitting did not weaken route authorization.

The browser check used local seeded development identities only. Backend authorization remains authoritative for every API request.
