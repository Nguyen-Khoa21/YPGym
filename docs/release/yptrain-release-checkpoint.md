# YPTrain post-Day-60 release checkpoint

Validated October 24, 2026 against `main` at `1b016f9` before this documentation-only checkpoint. Repository code, migrations and tests are the authority. The former YPFood proposal is cancelled: no YPFood model, migration, endpoint, route or client feature exists. The only remaining `YPFood` text explains that cancellation.

The working tree also contained preserved owner edits to Compose/dependency configuration, the member training-card height, Vite development networking and local diagram/document artifacts. They were not staged into this checkpoint. Fresh commands exercised that working tree, so the results are not presented as a pristine-checkout reproduction; the isolated business tests and migration checks still ran against disposable PostgreSQL/Redis storage.

## Feature disposition

| Feature | Status | Pushed implementation |
|---|---|---|
| 1. Mobile reliability and membership state | Verified | `436473c` — `feat(mobile): add reliable sessions navigation and membership updates` |
| 2. White/green workout design system | Verified | `bc5a6bd` — `feat(ui): add white green YPGym workout design system` |
| 3. Mobile member journey and class reminders | Verified | `e7f5d76` — `feat(mobile): complete member self service and class reminders` |
| 4. Registration welcome email | Development verified; live inbox delivery remains external | `cd15402` — `feat(auth): add configurable welcome email delivery` |
| 5. YPTrain catalogue and equipment guide | Verified; physical machine inventory remains unconfirmed | `80e6505` — `feat(yptrain): add shared exercise catalogue and guide` |
| 6. Attendance-linked workout logging | Verified | `013fd99` — `feat(yptrain): add attendance linked workout logging` |
| 7. History, comparisons and muscle map | Verified | `775b542` — `feat(yptrain): add workout history and weekly muscle map` |
| 8. Guarded weekly review | Partial by owner decision | `e593980` — `feat(yptrain): add deterministic weekly training summary`; explicitly labelled non-AI because live provider integration was deferred |
| 9. Attendance renewal benefit | Verified with approved better-of and first-successful-renewal policy | `2431fd0` — `feat(billing): add VNPay checkout, paid classes, and attendance renewal benefits` |
| 10. Staff/PT accounts and time clock | Verified | `cc6a017` — `feat(staff): add account provisioning and shift clock` |
| 11. Management UX corrections | Verified | `e5dc423` — `feat(admin): add reliable management action feedback`; later PT completion render correction `1b016f9` |
| 12. Integrated release checkpoint | Verified for implemented scope | This documentation checkpoint; its commit hash is reported in the final handoff because a commit cannot contain its own hash |

Features 1–7 and 9–11 are complete at the development-verification level. Feature 8 is not represented as live AI: the same backend-derived deterministic summary is shown on web and Expo with a **not AI-generated** label and no provider, key, model dependency or unrestricted chatbot.

## Shared YPTrain implementation

Web and Expo use the same authenticated FastAPI services and PostgreSQL records:

- Catalogue: `GET /api/v1/training/exercises` and `GET /api/v1/training/exercises/{id}`.
- Management: `/api/v1/admin/training/exercises` create/update/archive/restore and validated image replacement, restricted to manager/admin roles.
- Current workout: `GET /api/v1/training/workouts/today` and attendance-gated exercise submission under the current-workout contract.
- History: paginated activity, exact day detail, exercise history/comparison and weekly muscle-map endpoints under `/api/v1/training/workouts`.
- Renewal benefit: member-only previous-complete-month quote and server-authoritative membership checkout snapshots.
- Staff operations: manager/admin account provisioning/reporting and staff/PT self clock-in/out endpoints.

Self-service workout routes derive the member from the authenticated principal. They do not accept a client-selected `member_id`. Workout creation requires a recorded scanner check-in, eligible membership and the current configured gym-local day. Snapshotted exercise names and muscle tags preserve historical meaning after catalogue edits.

## Migrations

| Revision | Purpose |
|---|---|
| `20260921_0008` | Class-reminder preferences and notification targets |
| `20260922_0009` | Welcome-email delivery attempts |
| `20260922_0010` | Shared YPTrain exercise catalogue |
| `20260922_0011` | Attendance-linked workout sessions/exercises/sets |
| `20260924_0012` | Expanded controlled muscle taxonomy |
| `20261009_0017` | Attendance-renewal benefit reservations and immutable billing snapshots |
| `20261013_0018` | Staff first-login state and auditable shifts |

An empty disposable PostgreSQL database upgraded through `20261013_0018 (head)`. `alembic check` reported no new upgrade operations.

## Fresh verification

The isolated backend command was:

```powershell
docker compose -p ypgym-yptrain-release -f compose.test.yml up --build --abort-on-container-exit --exit-code-from test-runner --attach test-runner
```

Result: **186 passed, 12 warnings in 92.90 seconds**. All warnings are the existing Starlette `HTTP_422_UNPROCESSABLE_ENTITY` deprecation. The disposable project, network and volumes were removed afterward.

Additional checks:

| Area | Commands | Result |
|---|---|---|
| Compose | `docker compose config --quiet` | Passed |
| Database | `alembic upgrade head`, `alembic current`, `alembic check` in the isolated stack | Head `20261013_0018`; no drift |
| Python dependencies | `pip check` in the isolated backend image | No broken requirements |
| Web | `npm run test`, `npm run lint`, `npm run build` | 20 tests passed; lint/build passed |
| Mobile | `npm run test`, `npm run typecheck`, `npm run lint` | 12 tests passed; typecheck/lint passed |
| Android package export | `npx expo export --platform android --output-dir <temporary-directory>` | Passed |

Web lint retains the known TanStack Table compiler warning. The production/PWA build retains the known large main-chunk warning and generated 15 safe precache entries. Mobile Node tests retain their module-type performance warning. None is a test failure.

The fresh pass found one actual regression: `PtDashboardPage` called `Date.now()` during render. Commit `1b016f9` removed the redundant client clock branch; the server remains authoritative for class confirmation eligibility. Frontend lint/build then passed.

## Security and integrity controls

- Backend RBAC and ownership protect catalogue management, private workouts, billing and staff operations.
- PostgreSQL remains authoritative; Redis contains replaceable short-lived QR, rate-limit, cache and Celery state.
- Catalogue changes cannot rewrite workout history because saved workout entries snapshot exercise meaning.
- Daily workout uniqueness, request idempotency, row locking and server-derived date/member values protect concurrent submissions.
- Attendance renewal prices and eligibility are calculated and reserved server-side, then snapshotted on payments and invoices.
- Temporary staff passwords are generated with `secrets`, immediately hashed, revealed once, and require replacement before normal access.
- Error responses and logs preserve request correlation without exposing tokens, passwords, provider secrets or database exception text.
- Generated mail, invoices, exports, build artifacts, environment files and credentials remain excluded from release commits.

## Manual demo journeys

Start the local application using `RUN_GUIDE.md`, apply migrations and seed development data. Then exercise these paths:

1. Register and verify a member, inspect the development welcome-email outbox, sign in, purchase/renew membership, open the invoice, generate the rotating QR, scan it with the IoT simulator, inspect attendance/crowdedness, book a class and open its reminder.
2. As manager/admin, open `/admin/exercises`, create or update an illustrative exercise and muscle tags, then confirm the same entry appears under member web `/app/train` and the Expo YPTrain tab.
3. As a checked-in member, add 1–10 validated sets from web or Expo and confirm the same current-day workout appears on both. A direct request without a qualifying check-in must return `WORKOUT_CHECK_IN_REQUIRED`.
4. Open history, select the workout day, compare the exercise and confirm the calendar, textual exposure list and front/back muscle map agree. Confirm the weekly text is labelled rule-based and not AI-generated.
5. Open the renewal quote and confirm the previous-complete-month numerator, denominator, percentage, selected better-of discount and final invoice snapshot agree.
6. As manager, create distinct staff and PT accounts. Replace the temporary password, clock in/out as workforce, confirm the shift report, then exercise trainer, broadcast, configuration and class mutations without a full-page reload.

Detailed procedures are in `docs/api/training-catalogue.md`, `docs/api/workout-logging.md`, `docs/api/workout-history.md`, `docs/api/attendance-renewal-benefit.md`, `docs/api/staff-operations.md` and `RUN_GUIDE.md`.

## Known limitations

- Live guarded AI remains owner-deferred. The deterministic weekly balance is complete but is not AI.
- SMTP adapters and controlled tests pass; a real recipient/inbox acceptance run is not claimed by this checkpoint.
- VNPay uses its configured sandbox/integration boundary; internal refund `resolved` state is not proof of a provider reversal.
- Physical Android/iOS rendering, app-store packaging and human UAT were not rerun.
- Illustrative catalogue entries do not assert which equipment is physically installed at YPGym.
- Generated state diagrams remain local/ignored under the owner's later instruction and are not part of this release commit.
