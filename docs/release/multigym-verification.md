# Multi-gym verification record

Written 2026-11-09 for the multi-gym web release on branch `codex/feat/web-multigym-foundation`, local head `0b76359` (Package 7). Every result below comes from a command that was run for this record. Anything not run is listed as not run.

## Where it was run

A cloud verification workspace (Linux, Python 3.13, Node 22, PostgreSQL 16, Redis) holding the repository files at the commit above. The owner's uncommitted local edits (compose files, member detail and training pages, mobile files and others) are not in that workspace, so they are not covered. Docker was not available, so the compose files were not run. The Windows development machine was not used for these runs.

## Results

| Check | Command | Result |
|---|---|---|
| Migration cycle | `alembic downgrade 20261103_0019`, `alembic upgrade head`, `alembic current`, `alembic check` | Downgraded 0021 then 0020, upgraded back to `20261109_0021 (head)`, `alembic check`: "No new upgrade operations detected." |
| Backend tests | `python -m pytest -q -x` | 217 passed, 11 warnings, 70 s |
| Web unit tests | `npm test` | 41 tests, 41 pass, 0 fail |
| Web lint | `npm run lint` | 0 errors, 1 warning (`react-hooks/incompatible-library` in an older table component) |
| Web build | `npm run build` (`tsc -b && vite build`) | Passed; service worker generated |
| Browser tests | `npx playwright test e2e/operations-scope.spec.ts` | 3 passed |
| Browser tests | `npx playwright test e2e/form-reliability.spec.ts` | 3 passed |
| Ten-step flow | Script against a freshly migrated and seeded API (`python -m app.db.seed --demo`) | Steps 1 to 9 behaved as written, see below |

Browser tests ran in Chromium at 1280 px for the default viewport and 375 px for one form test. Existing Playwright specs for other pages (`member-dashboard.spec.ts`) were not re-run for this record.

### Ten-step flow, actual results

```text
1  owner gyms                              200, two gyms
2  owner occupancy D1 / D11 before         200, active_count 0 and 0
3  memberdist1 scan in at D1 scanner       200 CHECK_IN_SUCCESS
3  owner occupancy D1 / D11 after          D1 active_count 1, D11 0
4  memberdist1 scan at D11 scanner         403 MEMBERSHIP_GYM_MISMATCH
4  memberdist11 scan at D11 scanner        200 CHECK_IN_SUCCESS
5  managerdist1 attendance list            200, only District 1 rows
5  managerdist1 asks for D11               403 PERMISSION_DENIED
6  staffdist1 list before clock-in         403 SHIFT_REQUIRED
6  staffdist1 clock in                     201
6  staffdist1 list on shift                200
7  staffdist1 on shift asks for D11        403 PERMISSION_DENIED
8  manager summary revenue / owner revenue absent / present
8  managerdist1 summary for D11            403 PERMISSION_DENIED
9  managerdist1 publishes own gym          200
9  managerdist1 names D11                  403 PERMISSION_DENIED
9  owner publishes chain-wide              200, gym_id null
9  memberdist1 sees both notices; memberdist11 sees only the chain-wide one
```

Step 10 (Branches page, one card per gym) is covered by `operations-scope.spec.ts`, not by this script.

### Not a release gate

`ruff check` reports 174 findings and `mypy app` reports 381 errors in this workspace. They were run only to record the numbers, were not triaged, and no claim is made about whether they existed before this release.

## Not run

- Real payOS payment and webhook against the live service.
- Any test on a physical phone, on iOS, or with a hardware scanner.
- `docker compose` stacks (`compose.demo.yml`, `docker-compose.yml`).
- A screenshot comparison of every existing page after the Package 7 form changes.
- The Package 7 audit rows marked "left as is" were not migrated, so those controls were not re-tested.

## Known limitations

- Real payOS payment is untested. The backend suite covers the gym rules around payments, but no request was made to the live payOS service.
- There was no physical phone or iOS testing.
- The analytics and attendance charts show seeded demo data, not real gym traffic.
- The native mobile app and the scanner app were not updated for gyms. They send no `gym_id`; members resolve to their previous gym, and a scanner belongs to the gym set on its device record.
- The gym scope bar exists only on Attendance and Branches. Other management pages do not yet let the owner switch gyms.
- Branch edit, workforce reassignment and double-click handling on the Branches page were not browser-tested.
- Realtime gym isolation is tested at the key and channel rule level, not with two live browser sessions.
- `GET /admin/analytics/traffic-summary` defaults to District 1 for the owner when no gym is given.
- Backfill sets all pre-existing broadcasts to District 1.
- The `docs/HANDOFF_MULTIGYM_SESSION.md` file is stale and is not part of this record.

## Deferred work

Mobile gym selector, mobile traffic chart, member preference questionnaire, recommendations and online PT services. They are future scope and are not available in this release. The master prompt's future-scope section was not in the repository, so no link is given.

## Release readiness

| Item | State |
|---|---|
| Migrations upgrade, downgrade and check on a clean database | Verified |
| Backend suite | Verified (217 passed) |
| Web lint, build and unit tests | Verified |
| Browser tests for scope and form pages | Verified (6 passed) |
| Cross-gym refusals and shift gate through the API | Verified (ten-step flow) |
| Isolated Docker demo stack | Not run |
| Real payOS payment | Not run |
| Physical device and iOS check | Not run |
| Mobile and scanner apps for gyms | Deferred |
