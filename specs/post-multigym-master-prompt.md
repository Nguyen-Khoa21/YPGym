# YPGym Post-Multigym Master Prompt (Packages 11 to 16)

You are continuing the YPGym repository after the multi-gym rollout (Packages 1 to 10). This prompt holds the specs for six new packages. Read section 0 first, then do the packages **in order, one focused commit each**.

---

## 0. Operating rules (non-negotiable)

1. Follow `AGENTS.md` (ponytail mode) and `specs/README.md`. Inspect the full flow (React or Expo screen -> FastAPI endpoint -> service -> repository -> model -> PostgreSQL/Redis) before editing. Search for an existing implementation before adding one. Reuse before you build.
2. Branch: `codex/feat/web-multigym-foundation` (or a child branch if the owner prefers). Run `git status` first. **The working tree already contains the owner's uncommitted edits** (for example `backend/app/services/invoice_service.py`, `docker-compose.yml`, `RUN_GUIDE.md`, `frontend/nginx.production.conf`, files under `mobile/`). Never revert, stash, overwrite or stage them. Stage only your own hunks (`git add -p`).
3. **One package = one commit. Do not push. Do not commit unless the owner's message for that package says so.** After each package, give the completion report required by `AGENTS.md`, ask permission to push, and stop.
4. Before coding a package, create `specs/package-NN-<slug>/spec.md` from the matching section below (same IDs: `FR-`, `AC-`, `T`), and add its rows to `specs/traceability.md`. If code and spec disagree, write it in `specs/decisions.md` (use the next free ID, D-12 onward). Do not silently edit code to match a spec or a spec to match a bug.
5. Layering stays: endpoint -> service -> repository -> model. PostgreSQL is the source of truth. Redis is cache and rate-limit state only. Schema changes use Alembic (current head is `20261109_0021`). New migrations are reversible and named `20261110_0022_...`, `..._0023_...`, and so on.
6. Backend authorization decides access. Hiding a control in React is not security. The gym for any staff, manager or member action is derived on the server through `GymScopeService`, never trusted from the client.
7. No new dependency unless the installed ones cannot do the job. Already available: `qrcode.react`, `recharts`, `sonner`, `react-hook-form`, `zod`, TanStack Query/Table (web); `reportlab` (backend); Expo packages already in `mobile/package.json`. Check `mobile/package.json` before assuming a mobile package exists.
8. Never print or log secrets, tokens, verification codes, temporary passwords, SMTP credentials or `.env` values. Do not read `.env` files; use `.env.example` and the settings class.
9. Every package ships tests (success, validation, permission, conflict) and a manual test script. Run only commands the project defines (see `AGENTS.md`). Do not claim a command passed unless it ran. If a command cannot run, say which one and why.
10. Existing e2e and unit tests that encode the old UI (for example `frontend/e2e/member-dashboard.spec.ts`, `frontend/tests/*.test.mjs`) must be **updated deliberately** where the owner's new requirement changes the behavior, and the change recorded in `specs/decisions.md`. Never delete a test to make the suite pass.

---

## 1. What the inspection found (evidence)

Each statement names its source. Anything marked *Unverified* must be checked by you before relying on it.

| # | Finding | Source |
|---|---|---|
| E1 | The verification email is plain text with **two links and no code**: `{FRONTEND_URL}/verify-email?token=...` and `{MOBILE_APP_URL}verify-email?token=...`. `FRONTEND_URL` defaults to `http://localhost:5174` and `MOBILE_APP_URL` to `ypgym://`. A phone cannot open `localhost`, and mail apps rarely make `ypgym://` clickable. | `backend/app/services/auth_service.py` (`_prepare_development_email`), `backend/app/core/config.py` |
| E2 | The mobile verify screen asks for a "Verification token" and requires at least 16 characters, so users are told to paste the long URL token. The email never shows a short code. | `mobile/src/app/verify-email.tsx` |
| E3 | With `EMAIL_DELIVERY_MODE=development` the message is written to a Maildir folder, not sent. `_prepare_development_email` also returns silently when mode is `development` and `ENVIRONMENT` is not `development`. A phone tester gets no email unless SMTP is configured. Verification mail is sent inline, outside the retryable outbox, and a send failure at registration is only logged. | `auth_service.py`, `email_service.py`, `docs/policies/security.md` |
| E4 | The welcome email says "Verify your email using the separate verification message". It is a second email through the notification outbox. | `email_service.py` (`_welcome_message`) |
| E5 | `email_verifications` stores `token_hash`, `expires_at`, `used_at`, `new_email`. The same table also serves email-change confirmation (`new_email`). Do not break that path. | `backend/app/models/auth_token.py`, `auth_service.py` |
| E6 | `derive_membership_status` returns `pending_verification` when `is_email_verified` is false. **A member who is not verified has no access.** This matters for in-person registration (Package 16). | `backend/app/services/lifecycle_service.py` |
| E7 | **No onboarding questionnaire, preference store or recommendation code exists.** `specs/README.md` lists them as out of scope for Packages 5 to 8. They are new work. | repo-wide search, `specs/README.md` |
| E8 | Building blocks that already exist: gyms `GET /gyms`; member traffic summary `GET /attendance/traffic-summary` (home gym only, needs a membership); manager/admin `GET /admin/analytics/traffic-summary`; `GymScopeService`; `workforce_gym_assignments` (one active assignment per manager, staff or PT); seeded per-district accounts (`managerdist1@`, `staffdist11@`, and so on). | `docs/policies/roles.md`, `specs/completed-packages.md`, `backend/app/db/seed.py` |
| E9 | Expired memberships: status is derived as `expired` and the QR is blocked with the message "Renew your expired membership to restore access." `BuyMembershipPage` already offers "Keep or change your gym location" for members with a membership. There is **no explicit expired prompt** that offers renew-or-change-location; the dashboard shows a small status badge and a "Renew membership" link. | `lifecycle_service.py`, `BuyMembershipPage.tsx`, `MemberDashboardPage.tsx` |
| E10 | Web dashboard: the gym name appears twice, both small (`text-sm` "Your gym: ..." and a `text-xs` label inside `OccupancyCard`). The occupancy card is documented as "the most prominent block". Membership and Notifications are separate full-width sections below, which causes scrolling. | `MemberDashboardPage.tsx`, `OccupancyCard.tsx` |
| E11 | **Conflict with the Package 5 spec:** `FR-DASH-001` (header text "Your gym: {home_gym_name}"), `FR-DASH-002` (occupancy is the most prominent block), `FR-DASH-011` and `FR-DASH-012` (membership as a compact card below the facility status) are superseded by Package 14. Record this in `specs/decisions.md`. | `specs/package-05-member-dashboard/spec.md` |
| E12 | Mobile dashboard order today: big membership card, then a row with "Show QR" and "Live capacity" tiles, then announcements, then "Upcoming Classes", then "Notifications". The bell icon has no unread badge although `unread_notification_count` is already in the payload. | `mobile/src/app/(member)/(tabs)/dashboard.tsx` |
| E13 | The heading "When is it quiet?" is hard-coded. `summary.gym_name` is available (seed gym names already start with "YPGym", for example "YPGym District 1"). | `frontend/src/features/member/components/TrafficHistory.tsx` |
| E14 | Billing page: the screenshot shows the invoice list rendered **and** an "Unexpected error / Something went wrong" banner. The lists only render when the list queries succeed, so the banner comes from the **download** handler, which throws a plain `Error` that `toUiError` shows as a generic message and hides the real status and code. The download also always uses `Content-Disposition: attachment` (`FileResponse(filename=...)`), so it can never preview like Gmail. The PDF is regenerated on every request into `INVOICE_STORAGE_DIR` (default relative `storage/invoices`). *The actual failing cause is unverified.* | `PaymentHistoryPage.tsx`, `billing.py`, `billing_service.py`, `invoice_service.py` |
| E15 | Production CSP: `object-src 'none'` and `default-src 'self'` in `frontend/nginx.production.conf`; backend adds `frame-ancestors 'none'`. A PDF preview in an iframe or object from a `blob:` URL needs `frame-src 'self' blob:` (or equivalent) on the page CSP. | `frontend/nginx.production.conf`, `backend/app/core/security_headers.py` |
| E16 | Staff workspace today (`StaffTimeClockPage`) contains only the clock card and recent shifts. Attendance sessions and live capacity exist on a separate page (`AdminAttendancePage`). Staff can read occupancy (decision D-06) but not manager analytics. | `StaffTimeClockPage.tsx`, `AdminAttendancePage.tsx`, `specs/decisions.md` |
| E17 | Manual enrollment exists only for **existing** members and only for manager/admin: `POST /admin/members/{user_id}/membership`, with a mandatory reason. There is no staff-created member account. Workforce accounts already use a one-time temporary password and `must_change_password`. The mobile app has no `must_change_password` handling (search found none). | `admin.py`, `staff_service.py`, `mobile/src/lib/auth.tsx` |
| E18 | payOS checkout currently returns `checkout_url`. A QR payload is not passed through the schema. *Unverified:* whether the payOS SDK response includes `qrCode`. | `payment_schema.py`, `payos_service.py` |
| E19 | Admin "Schedule a class" dialog: the Description field is a raw `<textarea className="min-h-24 ...">` inside a single cell of a two-column grid, so it is narrow and leaves empty space. A shared `Textarea` already exists in `components/ui/Form.tsx`. | `AdminClassesPage.tsx`, `components/ui/Form.tsx` |

---

## 2. Defaults assumed (owner can change any of these)

The owner approved "go with the recommendation" for the earlier decisions, so use these without stopping. Record each in `specs/decisions.md`.

| ID | Decision | Default |
|---|---|---|
| D-12 | Verification code shape | 6 digits, expires in 10 minutes, 5 wrong attempts then locked until a new code is sent, resend cooldown 60 seconds. The link in the email stays valid as a secondary path. |
| D-13 | When the questionnaire appears | **Owner confirmed:** right after the member's first successful login, as the first screen they see. Skippable. Editable later in Profile. No nagging after a skip. |
| D-14 | Who sees onboarding data | Owner (all gyms or one gym) and manager (own gym) see **aggregates only**. Groups with fewer than 5 responses are hidden. Staff and PT see nothing. No raw per-member answers outside the member. |
| D-15 | "Each location with each role account staying separate" | Read as: every gym has its own manager, staff and PT accounts; no account is shared across gyms; only the owner (`admin`) is cross-gym; moving an account is an explicit owner action. Most of this already exists, so Package 13 verifies and closes gaps. **If the owner meant something else, stop and ask.** |
| D-16 | In-person registration payment | **Owner confirmed:** two ways to pay. (1) payOS QR for the member to scan on the spot. (2) If the customer pays by cash, staff press a **Pay with cash** button, which records a cash payment, activates the membership and issues the invoice at once. Manager/admin manual enrollment stays as is. Staff must have an open shift. |
| D-17 | In-person account email status | Marked verified because identity is checked at the desk. Record `registration_channel='in_person'` and who registered it. Force a password change at first login. |
| D-18 | Mobile dashboard reading | See Package 14, section "Reading of the annotated screenshots". |

---

## Package 11: Email verification code

**Goal.** The email mails a short code the user can type on a phone, with the link as an optional extra that is never a localhost link.

### Requirements

| ID | Requirement |
|---|---|
| FR-VER-001 | On registration and on resend, generate a 6-digit numeric code with `secrets` (zero-padded, uniform). Store only an HMAC-SHA256 of the code keyed with a server secret and bound to the user id (a plain hash of a 6-digit value is trivially reversible). Compare with `hmac.compare_digest`. |
| FR-VER-002 | The code and the existing link token live on the **same** `email_verifications` row, so using either one consumes both. Add nullable `code_hash` and `failed_attempts int not null default 0`. Do not add a second table. Keep `token_hash` unique and the `new_email` email-change path working. |
| FR-VER-003 | The verification email is multipart (plain text and HTML, HTML-escaped). The code is the first and largest thing in it, with the expiry time in minutes. A web link is included **only** when `FRONTEND_URL` is not a loopback host (`localhost`, `127.0.0.1`, `::1`). Remove the `ypgym://` link. Reuse `EmailDeliveryService._base_message` and the HTML escaping style instead of hand-building another message. |
| FR-VER-004 | New `POST /auth/verify-email/code` with `{email, code}`. On success it returns the same `VerifyEmailResponse` as the link path. Wrong code: `400 INVALID_VERIFICATION_CODE`. Expired: `400 VERIFICATION_TOKEN_EXPIRED`. Locked after the fifth wrong attempt: `429 VERIFICATION_CODE_LOCKED` (resend required). Use the existing structured error shape. |
| FR-VER-005 | New `POST /auth/verify-email/resend` with `{email}`. It always answers the same generic `200` whether or not the account exists or is already verified (no account enumeration). When it does apply, it invalidates earlier unused codes for that user, creates a new one and sends it. Enforce the 60-second cooldown from the newest row's `created_at`, plus Redis rate limits per hashed IP and per hashed IP+email (add them next to the existing `verify` limits and document them in `docs/policies/security.md`). |
| FR-VER-006 | Keep `GET /auth/verify-email?token=` unchanged for old links. |
| FR-VER-007 | Web `/verify-email`: when `?token=` is present, keep the current behavior. Otherwise show an email field (prefilled from `?email=`), a 6-digit input (`inputMode="numeric"`, `autoComplete="one-time-code"`, paste-friendly), a Verify button, and a Resend button with a visible countdown. The registration success card links to `/verify-email?email=...`. A login rejected with `EMAIL_NOT_VERIFIED` offers a link to the same page. Reuse the shared `Field`, `Input`, `Button`, `FeedbackState` components. |
| FR-VER-008 | Mobile `verify-email.tsx`: replace the token box with a 6-digit code input (`keyboardType="number-pad"`, `textContentType="oneTimeCode"`), show the email, add Resend with countdown, keep accepting a deep-linked `token` param. Show clear messages for wrong, expired, locked and rate-limited. |
| FR-VER-009 | The welcome email must no longer say "separate verification message" if both emails now arrive together. Reword to match. |
| FR-VER-010 | Register response includes `verification_email_sent: boolean`. If the send failed, the UI says so and offers Resend immediately instead of showing a success message that is not true. |
| FR-VER-011 | Document in `RUN_GUIDE.md` / `docs/api/identity-and-membership-email.md`: to test on a phone, set `EMAIL_DELIVERY_MODE=smtp` with real SMTP settings and set `FRONTEND_URL` to an address the phone can reach. State plainly that the development Maildir is not email. |

### Acceptance criteria

- **AC-VER-001.** Given a new registration with SMTP or a fake transport, when the email is sent, then its text and HTML both contain a 6-digit code and no `localhost` or `ypgym://` URL.
- **AC-VER-002.** Given a correct code before expiry, when posted, then `is_email_verified` becomes true, the row is `used_at`-stamped, and the link token for that row no longer works (already-used message).
- **AC-VER-003.** Given five wrong codes, when a sixth (even correct) code is posted, then it is rejected with `VERIFICATION_CODE_LOCKED` until a resend creates a new code.
- **AC-VER-004.** Given resend within 60 seconds, then the request is rejected with a retry-after; given resend for an unknown email, then the response is identical to a real one.
- **AC-VER-005.** Given an expired code, then `VERIFICATION_TOKEN_EXPIRED`; the database holds no plaintext code anywhere (check the row, logs and test fixtures).
- **AC-VER-006.** Given an existing email-change verification (`new_email`), when its link is used, then it still works.
- **AC-VER-007.** A phone user can register, read the code in the mail app, type it on the mobile verify screen, and sign in.

### Tasks

T11-01 spec and decisions D-12. T11-02 migration `0022` (`code_hash`, `failed_attempts`). T11-03 repository and service changes. T11-04 endpoints, schemas, rate limits. T11-05 email message. T11-06 web page and login link. T11-07 mobile screen. T11-08 tests (backend integration, frontend `node --test`, mobile tests). T11-09 docs.

**Out of scope:** changing email-change flow, SMS, OAuth linking emails.

---

## Package 12: New-member questions, recommendations, owner insights

**Goal.** Ask a short radio-button questionnaire, use the answers to recommend a gym and quiet hours, and give the owner aggregate data to plan from. **Never recommend from an unanswered question.**

### Questions (all radio buttons, one screen, about one minute)

Required to count as "complete" (the three the owner asked for):
1. Are you new to the gym? Yes / No.
2. Would you like to work out in uncrowded hours? Yes / No.
3. Which location are you closer to? One radio per **active gym from `GET /gyms`** (today District 1 and District 11). Never hard-code gym names.

Suggested extras, optional (they make the owner's data more useful):
4. Main goal: Lose weight / Build muscle / Stay fit and healthy / Improve stamina / Not sure yet.
5. When can you usually train? Early morning (05:00 to 08:00) / Daytime (08:00 to 16:00) / Evening (16:00 to 20:00) / Night (20:00 to 24:00).
6. How many days a week? 1 to 2 / 3 to 4 / 5 or more.
7. Interested in group classes? Yes / No.
8. Interested in a personal trainer? Yes / No.

Show one line of purpose text ("We use this to suggest quiet hours and your closest gym"). Do **not** ask for health or medical data.

### Requirements

| ID | Requirement |
|---|---|
| FR-ONB-001 | New table `member_onboarding_profiles` (migration `0023`): `id`, `user_id` unique FK to `users` (cascade), nullable answer columns for Q1 to Q8 (booleans for Q1, Q2, Q7, Q8; `closer_gym_id` FK to `gym_locations`; short string columns with `CHECK` constraints for Q4 to Q6), `completed_at`, `dismissed_at`, timestamps. "Complete" means Q1 to Q3 are non-null. |
| FR-ONB-002 | Endpoints (member role only, user id from the JWT, placed under the existing user/me router, follow its conventions): `GET .../onboarding` (answers plus `status`: `not_started`, `skipped`, `partial`, `complete`), `PUT .../onboarding` (validated upsert; partial saves allowed), `POST .../onboarding/skip`. The closer gym must be an active gym. |
| FR-ONB-003 | Web: **immediately after a member's first successful login** (no row yet), open `/app/onboarding` as the first screen, once. It has a visible "Skip for now". A skip stores `dismissed_at` and the member is not asked again. Profile gets a "Training preferences" section to answer or edit later. Reuse React Hook Form, Zod and shared form components; build radios as accessible `fieldset`/`legend` groups. |
| FR-ONB-004 | Mobile: the same questionnaire as one screen in the member app, reached once after first login and from Profile. Reuse the `ui` components and `lib/gyms.ts`. |
| FR-ONB-005 | `GET .../recommendations` (member only). Pure, explainable rules, no machine learning: **R1 location**: only if Q3 is answered and that gym is active, return `recommended_gym`. **R2 quiet hours**: only if Q2 is "Yes", return the quietest two-hour window from the previous-month traffic data of the recommended gym (or of the home gym if Q3 is unanswered and the member has a membership). If Q5 is answered, choose the quietest window that overlaps the member's training window. If `data_sufficient` is false, return `quiet_hours: null` with `reason: "not_enough_data"`; never invent numbers. Each rule is independent; an unanswered input yields **no** recommendation for that rule. Reuse `TrafficAnalyticsService`/repository functions; do not call the manager-only endpoint and do not expose another member's data. |
| FR-ONB-006 | Where recommendations show: (a) the membership purchase and renewal gym picker marks the recommended gym "Recommended for you" and preselects it only when the member has no home gym; (b) the member class list marks that gym's tab "Recommended for you". Default class gym order stays: home gym, then recommended gym, then the first active gym. The member can always choose any gym. (c) The member dashboard shows a small card "Quiet time for you: {window} at {gym}" only when R2 produced a result. Web and mobile. |
| FR-ONB-007 | Owner and manager insights: `GET /admin/analytics/onboarding-insights?gym_id=` returns counts and percentages for respondents, response rate (respondents divided by members), new-to-gym, prefers uncrowded hours, closer-gym split next to the actual home-gym split, goal, training window, frequency, class interest, PT interest. Owner (`admin`) may pass any gym or none; manager is locked to the assigned gym (scoped by `closer_gym_id`; naming another gym is `403`); staff and PT get `403`. Hide any group below 5 responses (config value, default 5). Show it as a panel on the admin overview for manager/admin using existing `Panel` and `MetricCard`. Percentages of different gyms are never summed (same rule as occupancy). |
| FR-ONB-008 | Privacy: answers are deleted with the account (cascade); they are not written to logs, audit metadata or CSV exports; `docs/policies/security.md` states what is stored and why. |

### Acceptance criteria

- **AC-ONB-001.** A member who answered Q3 = District 11 sees District 11 marked "Recommended for you" in checkout and in the class list; a member who skipped sees no such marker anywhere.
- **AC-ONB-002.** Q2 = "No" or unanswered: no quiet-hours card and `quiet_hours` absent from the response.
- **AC-ONB-003.** Q2 = "Yes", enough data: the card shows the quietest window inside the member's Q5 window. Not enough data: the card says "Not enough attendance data yet" and shows no percentage.
- **AC-ONB-004.** A staff token gets `403` on the insights endpoint; a District 1 manager naming District 11 gets `403`; the owner can read both.
- **AC-ONB-005.** A group of 4 responses is returned as hidden/suppressed, never as numbers.
- **AC-ONB-006.** A member cannot read or write another member's answers (no user id in any path or body).
- **AC-ONB-007.** An inactive or unknown gym id in Q3 is rejected.

### Tasks

T12-01 spec, decisions D-13 and D-14. T12-02 migration `0023`, model, repository. T12-03 schemas and service (rules R1, R2). T12-04 endpoints. T12-05 web questionnaire, Profile section, recommendation markers, dashboard card. T12-06 mobile screen and markers. T12-07 insights endpoint and admin panel. T12-08 tests (answered versus unanswered matrix, scope matrix, suppression). T12-09 docs.

**Out of scope:** machine learning, push notifications, health questions, changing membership pricing from answers.

---

## Package 13: Expired membership prompt and per-location account separation

**Goal.** An expired member is clearly asked to renew or change location. Each gym keeps its own manager, staff and PT accounts, and tests prove it.

### Requirements

| ID | Requirement |
|---|---|
| FR-EXP-001 | When the derived membership status is `expired` (not cancelled, revoked or frozen), the web dashboard, `/app/qr` and the mobile dashboard and QR tab show a prominent panel: "Your membership at {gym} expired on {date}." with two actions: **Renew at {gym}** and **Change location**. Reuse existing `membership` data from the dashboard payload; add no new endpoint unless a field is truly missing. |
| FR-EXP-002 | Renew goes to the plan list with the home gym preselected. Change location goes to the same flow with the gym picker open and no gym preselected, except the recommended gym from Package 12 is marked. `BuyMembershipPage` needs a small route or query parameter to accept this (it currently derives the gym from the dashboard). Mobile does the same through the `renew` screens. |
| FR-EXP-003 | The home gym still changes **only after verified payment** (existing Package 4 rule). The panel never changes it. Test this again with an expired member who picks a different gym. |
| FR-EXP-004 | While expired the QR stays blocked, class booking follows the existing `access_snapshot` rule, and the member can still see attendance history and invoices. No new restriction. |
| FR-LOC-001 | Account separation audit. Confirm and test: (a) manager, staff and PT have exactly one active `workforce_gym_assignments` row (partial unique index exists); (b) `POST /admin/staff-accounts` requires a gym (owner chooses, manager is forced to own); (c) moving an account between gyms is owner-only, audited, and closes the old assignment; (d) a District 1 manager or staff cannot read or act on District 11 attendance, members, classes, broadcasts or staff shifts; (e) the owner is the only cross-gym role. Add the missing tests to `test_shift_and_scope_rules.py` or a new file in `backend/app/tests/integration`. Fix any gap found; do not add new roles. |
| FR-LOC-002 | Every workforce page shows the gym the signed-in account belongs to, prominently (name in the page header, same style as Package 14's gym label). The admin staff list shows each account's gym. |

### Acceptance criteria

- **AC-EXP-001.** Given an expired member, then the panel appears with both actions; given an active, frozen or cancelled member, then it does not appear.
- **AC-EXP-002.** Given the member picks another gym and pays, then `home_gym_id` changes only after the verified webhook (payment pending leaves it unchanged).
- **AC-LOC-001.** The scope matrix test (role x gym x endpoint family) passes and covers `403` for cross-gym and `GYM_ASSIGNMENT_REQUIRED` for an unassigned workforce account.

### Tasks

T13-01 spec and decision D-15. T13-02 shared `ExpiredMembershipPanel` (web) and mobile equivalent. T13-03 `BuyMembershipPage` and mobile renew parameter. T13-04 scope matrix tests and fixes. T13-05 gym label on workforce pages. T13-06 docs (`docs/policies/roles.md`).

**Out of scope:** grace periods, auto-renewal, changing expiry rules.

---

## Package 14: Dashboard and form UI tweaks (web and mobile)

Source: the annotated screenshots in `Post_Multigym_UI_tweaks.pdf`. Use `frontend-design` thinking only to stay inside the existing white-and-green system (`docs/design/route-screen-map.md`); do not restyle anything the owner did not mention.

### Reading of the annotated screenshots (D-18)

- **Web, page 1.** Move the gym location to the top and make it stand out. Shrink the occupancy card. Put a two-tab card beside/under it: **Important notifications** and **Membership**.
- **Mobile, page 2.** The live capacity block and the membership block swap places: capacity becomes the large top card; the membership summary becomes the compact tile. The "Show QR" tile and the membership tile then have the **same size**. "Upcoming classes" sits directly under that row so it is visible without scrolling. The bell shows a small red circle with the unread count. The owner's text "Live capacity tab should swap places with the membership tab above" is read this way because the capacity tile is currently below the large membership card. If the owner meant otherwise, stop and ask.
- **Web, page 3.** The heading "When is it quiet?" becomes "YPGym {current gym}'s Occupancy".

### Requirements

| ID | Requirement |
|---|---|
| FR-UIX-001 | Web dashboard header: show the member's gym as a prominent element near the greeting (map-pin icon, larger type, primary colour, for example "YPGym District 1"). Remove the small duplicate "Your gym: ..." text. Inside `OccupancyCard` the label becomes plain "Live occupancy". This replaces `FR-DASH-001`. |
| FR-UIX-002 | `OccupancyCard` becomes compact: less padding, smaller percentage figure, same data (percentage, status, `active_count` of `capacity`, updated time, progress bar). It stays at the top of the left column. |
| FR-UIX-003 | Directly under it, add one card with two tabs: **Important** (with an unread-count pill) and **Membership**. Important lists active broadcasts first, then unread notifications, at most 5, reusing `dedupeNotifications`, each item once, with an "Open inbox" link. Membership shows plan, status badge, days remaining, expiry, gym and the Renew link (and the Package 13 expired panel when expired). Default tab: Important when there is anything unread or any broadcast, otherwise Membership. Implement with native elements: `role="tablist"`, `role="tab"`, `role="tabpanel"`, `aria-selected`, arrow-key navigation. **No new dependency.** Remove the old full-width Membership section and Notifications card. Keep "Upcoming bookings" and "Quick actions". This replaces `FR-DASH-011` and `FR-DASH-012`. |
| FR-UIX-004 | `TrafficHistory.tsx`: the `<h2>` becomes "{display gym name}'s Occupancy" with a helper that adds the "YPGym " prefix only when the name does not already start with it, so the page never shows "YPGym YPGym District 1". During loading or error the heading uses the gym name from the dashboard payload; if none is known it falls back to "Occupancy". Update `aria-labelledby` and any test that reads the old text. Search the mobile app for the same string and change it if present. |
| FR-UIX-005 | Mobile bell: show a small red circle at the top-right of the bell with `unread_notification_count`, capped at "99+", hidden at 0, with `accessibilityLabel` "Notifications, N unread". Use the existing `IconButton`; extend it with an optional badge rather than writing a new button. Refresh with the dashboard query. |
| FR-UIX-006 | Mobile dashboard order: Brand/bell, heading, **Live capacity hero card** (gym name prominent, percentage, status pill, progress bar), then a two-tile row **[Show QR | Membership]** with equal height and width, then **Upcoming classes** (compact: next 2 bookings, "See all"), then announcements, then notifications. The membership tile shows the status pill, days remaining, and "Expires {date}", and taps through to the renew screens. The account tier text moves into the tile as small text; the home gym shows in the hero. On narrow phones (under 390 px) the tiles stack as they do today. |
| FR-UIX-007 | Admin "Schedule a class" dialog: the Description field spans both grid columns (`sm:col-span-2`), is full width, uses the shared `Textarea` from `components/ui/Form.tsx` (same border, radius and focus style as the inputs), has at least 8rem height, vertical resize only, and a live counter against the 3000-character limit already in the Zod schema. Check the edit dialog uses the same field. Do not change other fields. |
| FR-UIX-008 | Update `memberDashboardLogic.ts` and its tests, `frontend/e2e/member-dashboard.spec.ts`, and the Package 5 spec rows listed in E11. Add e2e checks at 390 px and 1280 px wide: no horizontal scroll, tabs switch by mouse and keyboard, the heading text is correct. |

### Acceptance criteria

- **AC-UIX-001.** At 1280 px the gym label, occupancy and the tab card are all visible without scrolling; at 390 px nothing overflows horizontally.
- **AC-UIX-002.** Switching tabs by keyboard works; each notification or broadcast appears once.
- **AC-UIX-003.** A member with no membership still sees the existing "Choose your gym" prompt (decision D-04 is unchanged).
- **AC-UIX-004.** Heading shows "YPGym District 11's Occupancy" for a District 11 member (not a doubled prefix).
- **AC-UIX-005.** Mobile: with 3 unread the bell shows "3"; with 120 it shows "99+"; with 0 no badge. Capacity card is above the QR/Membership row; the two tiles have equal measured size; at least the first upcoming class is on screen on a typical 390 x 844 device without scrolling (verify on a simulator or document a manual check).
- **AC-UIX-006.** The class description field is as wide as the dialog content and the dialog still fits at 1280 x 720.

### Tasks

T14-01 spec and the E11 spec edits. T14-02 web header, `OccupancyCard`, tab component, remove old sections. T14-03 `TrafficHistory` heading and helper. T14-04 mobile bell badge. T14-05 mobile layout reorder and equal tiles. T14-06 class dialog field. T14-07 tests and screenshots at both widths for the report.

**Out of scope:** a web notification badge (add it only if the shell already has a bell and it is a one-line change), redesigning other pages.

---

## Package 15: Invoices: fix download, add a Gmail-style viewer

**Goal.** Invoice PDFs download reliably and open in an in-page viewer, like previewing an attachment in Gmail.

### Step 1: diagnose before changing code

1. Reproduce with a member token: `GET /api/v1/billing/me/invoices/{id}` for a membership invoice **and** for a class-booking invoice (the screenshot has both).
2. Read the backend log for that request. Check that `INVOICE_STORAGE_DIR` is writable by the container user and survives restarts (compose volume), that `generate_pdf` receives the fields each product type needs, and that the response is `application/pdf`.
3. Write the confirmed root cause in the commit report. Do not guess. If it cannot be reproduced, say so and still deliver the hardening below.

### Requirements

| ID | Requirement |
|---|---|
| FR-INV-001 | Fix the confirmed cause. Add a regression test with an invoice of each product type: `200`, `application/pdf`, body starts with `%PDF`; another member's invoice is `404`. |
| FR-INV-002 | If PDF generation or file access fails, return a structured error (for example `503 INVOICE_PDF_UNAVAILABLE`) instead of an unhandled `500`. Prefer reading a stored file when it exists and regenerating only when missing; make generation write to a temporary name and rename so a half-written file is never served. Keep deletion behavior in the owner's uncommitted `remove_pdfs` untouched. |
| FR-INV-003 | Add a blob-aware request helper to `lib/apiClient.ts` that reuses the existing error parsing, so a failed download shows the real code and message, not "Unexpected error". Use it on the billing page. |
| FR-INV-004 | New in-page viewer on the billing page: clicking an invoice opens a full-screen dialog with the invoice number as title and a toolbar: **Download**, **Print**, **Open in new tab**, **Close** (Esc closes, focus is trapped and restored). The PDF is fetched with the bearer token as a blob and shown through a `blob:` URL in an `iframe` or `object`. Revoke the object URL on close. Show loading and error states with a Retry. Keep a plain Download button on each card. |
| FR-INV-005 | Update the page CSP so the viewer works in the production build: allow `frame-src 'self' blob:` (and `object-src blob:` only if you use `<object>`). Change the narrowest directive. `frontend/nginx.production.conf` already has uncommitted owner edits: add only your line and stage only your hunk. Also check the Vite dev server and `index.html` for a CSP meta tag. |
| FR-INV-006 | Mobile: open the invoice through the platform viewer or share sheet using a package already in `mobile/package.json` (check for `expo-sharing`, `expo-file-system`, `expo-web-browser`). If none is installed, list the smallest option and **ask the owner** before adding a dependency. The mobile invoices screen currently only lists records. |
| FR-INV-007 | Keep access rules: the invoice must belong to the signed-in user; no token in the URL or query string; no PDF path or filesystem detail in any response or log. |

### Acceptance criteria

- **AC-INV-001.** Clicking an invoice opens the viewer and shows the PDF in Chrome, Edge and Firefox on desktop.
- **AC-INV-002.** Download saves `{invoice_number}.pdf`; Print opens the print dialog for the PDF.
- **AC-INV-003.** When the API returns an error, the banner shows that error's title and message.
- **AC-INV-004.** The viewer works in the Nginx production container, not only in dev.
- **AC-INV-005.** Opening another member's invoice id returns `404` and the UI shows a clear message.

### Tasks

T15-01 diagnosis note. T15-02 backend fix and hardening and tests. T15-03 blob helper. T15-04 viewer dialog. T15-05 CSP change. T15-06 mobile viewer (or the owner question). T15-07 manual test script.

---

## Package 16: Staff workspace and in-person member registration

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
