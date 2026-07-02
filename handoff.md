# YPGym Codex Handoff

Last updated: 2026-07-02

## Current Repo State

- Project root: `C:\Users\Admin\ypgym`
- Git branch: `main`
- Git remote: `origin` -> `https://github.com/Nguyen-Khoa21/YPGym.git`
- Current milestone: Day 11 to Day 20 completed
- Main plan file: `YPGym_60_Day_Development_Plan_Revised_PostgreSQL (1).md`
- BRD/design reference: `FYP Brief BRD - Anh Khoa - Design Architecture.docx`
- Current Alembic head: `20260702_0003 (head)`

The repo now contains the Day 5-10 PostgreSQL foundation plus the Day 11-20 authentication, membership, and billing feature slice.

The older Day 1-4 scaffold containers may still appear in Docker Desktop or `docker compose ps`. They were left untouched. The revised stack uses `5174`, `8001`, `5433`, and `6380` to avoid conflicts with the older scaffold.

## What Was Implemented Today

### Day 11: Core PostgreSQL Models and Migrations

Added SQLAlchemy models and Alembic migrations for:

- `users`
- `email_verifications`
- `password_resets`
- `membership_plans`
- `user_memberships`
- `system_configurations`
- `payments`
- `invoices`

Migration files:

- `backend/alembic/versions/20260702_0002_core_auth_membership.py`
- `backend/alembic/versions/20260702_0003_billing.py`

Important database behavior:

- UUID primary keys.
- `created_at` and `updated_at` timestamps where appropriate.
- Unique `users.email` and `users.phone`.
- Indexed email, phone, user ID relationships, membership status, and expiry date.
- Hashed email verification and password reset tokens.
- Payment idempotency via unique `(user_id, idempotency_key)`.
- Invoice metadata is immutable after creation.

### Day 12 to Day 15: Auth Flows

Backend:

- `POST /api/v1/auth/register`
- `GET /api/v1/auth/verify-email?token=...`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`

Implemented:

- Password hashing with `passlib` and bcrypt.
- `bcrypt<5` pin because `passlib==1.7.4` is not compatible with bcrypt 5.x.
- JWT access tokens with user ID, role, tier, and expiry.
- Current-user dependency and role guard helpers.
- Development-only verification and reset links logged by backend.
- Neutral forgot-password response.
- One-time-use verification and reset tokens.

Frontend:

- `/register`
- `/verify-email`
- `/verify-email/success`
- `/login`
- `/forgot-password`
- `/reset-password`
- Protected route wrapper and auth context.

### Day 16: Profile Settings

Backend:

- `GET /api/v1/users/me`
- `PATCH /api/v1/users/me`

Implemented:

- Member can update `name` and `phone`.
- Duplicate phone is rejected.
- Password change requires current password.
- Email change is intentionally blocked for now because it needs a re-verification workflow.
- Audit log TODO added for later sensitive-account-change tracking.

Frontend:

- `/profile`
- Profile form with inline validation, success toast, and account security section.

### Day 17 and Day 18: Membership Plans and Seed Data

Backend:

- `GET /api/v1/membership-plans`
- Idempotent seed command:

```powershell
docker compose --profile app exec backend-api python -m app.db.seed
```

Seeded plans:

- 1 Month
- 3 Months
- 6 Months
- 1 Year
- 2 Years
- 3 Years

Seeded system configuration:

- gym capacity
- QR token TTL
- attendance timeout
- duplicate scan window
- class cancellation window
- waitlist size

Frontend:

- `/memberships`
- Responsive plan cards with price, discount, benefits, and auth-aware CTA.

### Day 19: Mock Membership Purchase and Renewal

Backend:

- `POST /api/v1/memberships/purchase`

Implemented:

- Verified member requirement.
- Backend-owned price calculation.
- Mock payment confirmation.
- Idempotency key duplicate-submit protection.
- New membership starts today when none exists.
- Renewal extends from current expiry when active.
- Payment record creation.

Frontend:

- `/memberships/buy/:planId`
- Mock payment confirmation state and success state.

### Day 20: Invoice and Billing History

Backend:

- `GET /api/v1/billing/me/payments`
- `GET /api/v1/billing/me/invoices`
- `GET /api/v1/billing/me/invoices/{id}`
- `GET /api/v1/billing/admin/payments`

Implemented:

- ReportLab invoice PDF generation.
- Invoice metadata stored in PostgreSQL.
- Invoice PDF download endpoint.
- Member payment/invoice history.
- Lightweight admin billing placeholder endpoint.

Frontend:

- `/billing`
- Member dashboard payment/invoice summary cards.
- `/admin/billing` placeholder table for staff/manager/admin roles.
- `/pt` safe placeholder route for PT login redirect.

## Important Files Created or Modified

Backend:

- `backend/app/models/*.py`
- `backend/app/schemas/*.py`
- `backend/app/repositories/*.py`
- `backend/app/services/*.py`
- `backend/app/api/v1/endpoints/*.py`
- `backend/app/core/dependencies.py`
- `backend/app/db/seed.py`
- `backend/app/utils/security.py`
- `backend/requirements.txt`

Frontend:

- `frontend/src/features/auth/*`
- `frontend/src/features/member/pages/ProfileSettingsPage.tsx`
- `frontend/src/features/memberships/pages/*`
- `frontend/src/features/billing/pages/PaymentHistoryPage.tsx`
- `frontend/src/features/admin/pages/AdminBillingPage.tsx`
- `frontend/src/components/ui/*`
- `frontend/src/lib/apiClient.ts`
- `frontend/src/lib/format.ts`
- `frontend/src/types/api.ts`
- `frontend/src/app/router.tsx`
- `frontend/src/components/layout/AppFrame.tsx`

Docs:

- `README.md`
- `docs/design/route-screen-map.md`
- `docs/database/erd.md`
- `handoff.md`

## How To Run

From PowerShell:

```powershell
cd C:\Users\Admin\ypgym
docker compose --profile app up -d --build
docker compose --profile app exec -T backend-api alembic -c alembic.ini upgrade head
docker compose --profile app exec backend-api python -m app.db.seed
```

Open:

```text
Frontend:      http://localhost:5174
Swagger docs:  http://localhost:8001/docs
Backend API:   http://localhost:8001/api/v1
PostgreSQL:    localhost:5433
Redis:         localhost:6380
```

## How To Verify Email in Development

SMTP is not configured. Verification links are written to backend logs.

After registering, run:

```powershell
docker compose logs backend-api | Select-String "development_email_verification_link" | Select-Object -Last 1
```

Open the printed URL, for example:

```text
http://localhost:5174/verify-email?token=...
```

## How To Check PostgreSQL

```powershell
docker compose exec postgres-db psql -U ypgym -d ypgym
```

Useful SQL:

```sql
\dt

SELECT id, name, email, phone, role, tier, is_email_verified, created_at
FROM users
ORDER BY created_at DESC
LIMIT 10;

SELECT name, duration_days, base_price, discount_percent, is_active
FROM membership_plans
ORDER BY duration_days;

SELECT id, user_id, amount, status, mock_reference, created_at
FROM payments
ORDER BY created_at DESC
LIMIT 10;

SELECT invoice_number, user_id, amount, pdf_path, created_at
FROM invoices
ORDER BY created_at DESC
LIMIT 10;
```

GUI connection:

```text
Host: localhost
Port: 5433
Database: ypgym
Username: ypgym
Password: ypgym_dev_password
```

## Verification Performed

Passed:

```powershell
cd C:\Users\Admin\ypgym
docker compose --profile app up -d --build
docker compose ps
docker compose --profile app exec -T backend-api alembic -c alembic.ini current
Invoke-RestMethod http://localhost:8001/api/v1/health
Invoke-RestMethod http://localhost:8001/api/v1/health/dependencies
python -m compileall backend\app
```

Frontend:

```powershell
cd C:\Users\Admin\ypgym\frontend
npm run lint
npm run build
```

Manual API flow passed:

- Register new user.
- Duplicate email rejected.
- Duplicate phone rejected.
- Verify email via local dev log link.
- Login and receive JWT.
- `/auth/me` works with JWT.
- Member token rejected from admin billing endpoint.
- Forgot password creates reset link in logs.
- Reset password works.
- Reset token cannot be reused.
- Login works with new password.
- Profile name/phone update works.
- Membership plans return 6 seeded plans.
- Mock membership purchase works.
- Duplicate purchase request returns original payment.
- Payment history returns payment.
- Invoice history returns invoice.
- Invoice PDF download works.

HTTP checks:

```powershell
curl.exe -I http://localhost:5174
curl.exe -I http://localhost:8001/docs
```

Both returned `200 OK`.

## Known Caveats

- Old Day 1-4 containers still appear as orphans. They were not removed.
- `docker compose ps` may show old `ypgym-backend`, `ypgym-frontend`, `ypgym-mongodb`, and `ypgym-redis`.
- Development verification/reset links are logged, not emailed.
- Browser automation tool failed with `sandboxCwd must use the file URI scheme`; page serving was verified with `curl.exe`.
- Docker frontend build reported existing npm audit vulnerabilities. Package upgrades were not attempted during this Day 11-20 slice.
- Full admin billing, CRM, attendance, QR scanning, freeze/cancellation workflows, notifications, class booking, AI chatbot, and Expo mobile screens are not implemented yet.

## Recommended Next Session

Start Day 21 from the revised plan.

Likely next direction: attendance and QR foundation, only if that matches Day 21 in the plan. Do not jump to AI chatbot, full CRM, class booking, notifications, or cancellation approval unless explicitly requested.
