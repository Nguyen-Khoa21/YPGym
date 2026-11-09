Part of the [post-multigym master prompt](../post-multigym-master-prompt.md). Read its sections 0 to 3 first (operating rules, evidence, defaults, cross-cutting rules).

# Package 16: Staff workspace and in-person member registration

**Goal.** Staff see members' attendance and the live capacity of their gym in their own panel, and can register a walk-in member who then pays through a payOS QR. The new member is linked to the staff member's gym automatically.

### Part A: attendance and capacity in the staff panel

| ID | Requirement |
|---|---|
| FR-STF-001 | Turn `StaffTimeClockPage` into the staff workspace (keep the route `/staff/time-clock`; relabel the nav item "Workspace"). Keep the clock card and recent shifts. Add: the gym name in the header, the live capacity block (active count, capacity, percentage, status), and the attendance sessions panel (member, check-in, closed, status, source, manual close with a mandatory reason). |
| FR-STF-002 | Do not copy code. Extract the occupancy metrics and the sessions panel (with its manual-close modal) from `AdminAttendancePage.tsx` into shared components used by **both** pages. Staff do not get manager analytics (decision D-06 stays). |
| FR-STF-003 | The existing shift gate stays: with no open shift the workspace shows "Clock in to start" and requests no attendance or occupancy data. The backend still enforces `403 SHIFT_REQUIRED`. |

### Part B: register a new member at the gym

Flow from the owner: register the new user like the online flow but **without email verification**; choose a membership; create a QR code for the member to make payment; the member can then use the app with their account and check attendance. The account is linked to the staff member's gym.

| ID | Requirement |
|---|---|
| FR-STF-004 | New endpoint `POST /staff/members` for roles `staff`, `manager` and `admin`. Body: `name`, `email`, `phone`. Same validation and duplicate errors (`EMAIL_ALREADY_EXISTS`, `PHONE_ALREADY_EXISTS`) as `AuthService.register`; reuse that logic rather than copy it. The service creates a `member` with a generated one-time temporary password (reuse the workforce `_temporary_password` approach), `must_change_password=True`, `is_email_verified=True` and `email_verified_at=now` (decision D-17; see E6 for why). The password appears once in the response with `Cache-Control: no-store` and is never logged. |
| FR-STF-005 | Add nullable `registration_channel` (default `'online'`, value `'in_person'` here) and `registered_by_user_id` to `users` (migration `0024`). Write an audit entry `member.registered_in_person` with actor and gym (no password, no code). Do not create the "verify your email" welcome notification for these accounts. |
| FR-STF-006 | The gym is derived on the server: staff and manager get their assigned gym (`GymScopeService.effective_gym_id`), a client-supplied other gym is `403`; the owner must send a `gym_id`. Staff need an open shift (`SHIFT_REQUIRED`). Rate limit per actor (suggested 30 per hour). |
| FR-STF-007 | New `POST /staff/members/{user_id}/membership-checkout` with `plan_id` and `idempotency_key`. It creates a **pending payOS payment for that member at the actor's gym**, using the existing checkout service with an `actor` parameter (mirror how `manually_enroll_membership` passes `current_user=target, actor=...`). The member's home gym changes only after the verified payOS webhook (existing Package 4 rule). The response contains the checkout URL and a QR payload. Verify that the payOS response carries `qrCode`; if it does not, encode `checkout_url` instead. Add an optional `qr_code` field to the payment schema (E18). Cash or manual payment is not added. |
| FR-STF-008 | New `GET /staff/payments/{payment_id}` returning only `status`, member name, plan name and gym for payments of the actor's own gym created through this flow, so the staff screen can poll (about every 3 seconds, stop on a final status). Other gyms' payments are `404`. |
| FR-STF-009 | UI: a **Register new member** button on the staff workspace opens an `InPersonRegistrationDialog` in steps: (1) details, (2) pick a plan (gym name shown, read-only for staff), (3) choose how the member pays: a **Pay with cash** button (confirmation step first: "Confirm you received {amount} in cash"), or **Pay by QR**, which shows a large payOS QR rendered with `qrcode.react` plus the amount, plan and gym, with live status (waiting, paid, expired or failed), (4) a done screen showing the temporary password once with a Copy button and the line "Member signs in with this email and the temporary password, then sets a new password." The same dialog is available to manager and admin from `AdminMembersPage` (the owner picks the gym first). Reuse `Modal`, `Field`, `Input`, `Button`, `FeedbackState`. |
| FR-STF-010 | Member sign-in with a temporary password must reach the existing `/change-password` flow on web. **Mobile has no `must_change_password` handling (E17):** add the minimum needed so these members are not locked out, using the existing mobile change-password screen or API if there is one. Check `mobile/src/app/login.tsx` and `lib/auth.tsx`. |
| FR-STF-011 | After payment, the member appears with attendance in the workspace sessions list once they scan in at that gym. |
| FR-STF-012 | **Cash payment.** New `POST /staff/members/{user_id}/membership-cash` with `plan_id` and `idempotency_key`, same roles and gym rules as FR-STF-006. It reuses `MembershipService.purchase` with `actor` (the existing manual path already creates a succeeded payment, an invoice and queued receipt emails and writes an audit entry) and records `provider='cash'` and a `CASH-` reference so cash is distinguishable in billing and exports. The audit reason is fixed text naming the staff member's gym ("Cash payment received at {gym}"); the caller cannot override the amount, which always comes from the plan price in PostgreSQL. A repeated `idempotency_key` returns the original result and never creates a second payment. The target must be a member the actor may serve (see FR-STF-006 on gym scope; a member that already belongs to another gym is `403` for staff). |

### Acceptance criteria

- **AC-STF-001.** A District 1 staff member on shift sees District 1 occupancy and sessions only. A District 11 session is never returned.
- **AC-STF-002.** Staff not on shift cannot register members or read attendance (`SHIFT_REQUIRED`).
- **AC-STF-003.** Registering creates a verified member with `registration_channel='in_person'`, `must_change_password=True`; a duplicate email or phone returns the same `409` codes as online.
- **AC-STF-004.** A staff member sending another gym id gets `403`; the owner without a `gym_id` gets `422`.
- **AC-STF-005.** Paying the QR (simulate the payOS webhook in tests) activates the membership and sets `home_gym_id` to the staff member's gym; an unpaid or cancelled payment leaves the member with no membership.
- **AC-STF-006.** The temporary password never appears in logs, audit rows or any later API response.
- **AC-STF-007.** The new member signs in, is forced to change the password, then sees their dashboard, QR and attendance.
- **AC-STF-008.** Staff cannot poll a payment from another gym.
- **AC-STF-009.** Pressing Pay with cash creates exactly one succeeded `cash` payment at the staff member's gym, an invoice, an activated membership with `home_gym_id` set to that gym, and an audit row; repeating the request with the same key creates nothing new; staff not on shift get `SHIFT_REQUIRED`; a body field cannot change the amount or gym.

### Tasks

T16-01 spec and decisions D-16 and D-17. T16-02 extract shared attendance components, rebuild the workspace. T16-03 migration `0024`, service for in-person registration. T16-04 staff checkout on behalf with `actor`, QR field. T16-05 staff payment status endpoint. T16-06 dialog UI and admin entry point. T16-07 mobile forced password change. T16-08 tests (scope matrix, shift gate, payment settlement, password hygiene). T16-09 docs, route-screen map, role matrix.

**Out of scope:** staff access to the full member CRM, looking up existing online members (a duplicate email shows "ask the member to renew online or ask a manager"), changing manager/admin manual enrollment.

---

## 3. Cross-cutting rules

- **Errors:** use the existing structured error shape and meaningful code names stating the cause. Add each new code to the web `apiErrors` mapping and the mobile error handling.
- **Accessibility:** labels on every control, keyboard operation, visible focus, `aria-live` for countdowns and payment status, colour is never the only signal.
- **States:** every new screen has loading, empty, error (with retry), disabled and success states.
- **Rate limits and privacy:** counters hold hashed values only. No raw codes, passwords, tokens, emails or onboarding answers in logs, audit metadata or exports.
- **Seed and demo:** extend `backend/app/db/seed.py` idempotently only where a package needs demo data (for example a District 11 expired member and an onboarding sample large enough to pass the 5-response threshold). Mark synthetic data as demo data like the traffic summary does.
- **Docs to update as you go:** `docs/policies/roles.md`, `docs/policies/security.md`, `docs/api/*`, `docs/design/route-screen-map.md`, `RUN_GUIDE.md`, `specs/traceability.md`.

## 4. Verification (per package)

Run only what the project defines:

```powershell
docker compose config
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api alembic check
docker compose exec -T backend-api pytest -q
```
```powershell
cd frontend
npm run lint
npm run build
npm test
npm run test:e2e
```
For mobile, run the scripts defined in `mobile/package.json`. Then `git diff --check` and `git diff --stat`. Test one downgrade and upgrade cycle for each new migration. Do not claim anything passed that you did not run.

## 5. Completion report (after each package)

Use the `AGENTS.md` format: requirement addressed, existing implementation reused, files changed, dependencies (state "No dependencies changed." if none), database impact, commands executed, results, manual testing steps, risks and limitations, suggested next task. Add: the requirement IDs covered, the acceptance criteria that passed with the test that proves each one, and any decision recorded. Then **ask permission to push and stop**.

## 6. Start now

1. Read `AGENTS.md`, `specs/README.md`, `specs/decisions.md`, `docs/HANDOFF.md`, `docs/policies/roles.md`.
2. Run `git status` and list which modified files overlap with the package you are about to touch.
3. Create the Package 11 spec file, record D-12 to D-18, and begin Package 11.

### Implementation record

- **Backend.** Migration `20261110_0024` adds `users.registration_channel` (NOT NULL, default `'online'`, check constraint) and `users.registered_by_user_id`. `InPersonMemberService` implements FR-STF-004 to 008 and 012; `AuthService.ensure_identity_available` is shared with online registration. `MembershipService.purchase(cash=True)` records `provider='cash'` and a `CASH-` reference. `PayOSPaymentService.create_payment(actor=..., idempotency_key=...)` creates the QR checkout on behalf of the member and returns `qr_code` when payOS provides it (not stored; a replay returns the checkout link only).
- **Deviation.** `registration_channel` is NOT NULL with a default instead of nullable, so existing rows read as `'online'`.
- **Scope decision.** Staff and managers can serve only walk-ins registered in person (and, once they have a membership, only at their own gym). This is stricter than FR-STF-012's gym rule alone and prevents staff from charging arbitrary online members by id.
- **Web.** `AttendanceSessionsPanel` and `OccupancyMetrics` are shared by `AdminAttendancePage` and the staff workspace (`StaffTimeClockPage`, nav label "Workspace"). `InPersonRegistrationDialog` (details, plan, cash or QR, done) is available from the staff workspace and from `AdminMembersPage`. The temporary password is shown in every step after registration so closing the dialog early does not lose it.
- **Mobile.** `must_change_password` now redirects to `/change-password` (uses `PATCH /users/me`) from login and from the member layout.
- **Not verified.** Backend tests in `test_in_person_registration.py` are written but not run (no pytest or compose test stack in this session). The UI was type-checked and linted, not exercised in a browser; AC-STF-007 (full web and mobile sign-in journey) is unverified. The migration was not run (`alembic upgrade/downgrade` untested).
