# YPGym Web + Mobile Application

# Revised 60-Day Development Plan

**Version:** PostgreSQL Architecture Revision  
**Planning basis:** New BRD brief with PostgreSQL, SQLAlchemy, Alembic, Redis, Dockerized services, web app, mobile app, IoT integration, error handling, UML/use-case documentation, membership policies, CRM, QR attendance, billing, notifications, analytics and the added Design Architecture screen section.  
**Existing progress:** Days 1-4 from the previous plan are treated as completed. The remaining work starts from Day 5, with a migration checkpoint to align the existing scaffold with the revised PostgreSQL architecture.

---

## 1. PM Summary

This revised plan replaces the earlier MongoDB-oriented implementation path with a PostgreSQL-based backend. It preserves the useful work completed in Days 1-4: repository setup, initial Docker work, FastAPI scaffold and React scaffold. From Day 5 onward, the plan updates the infrastructure, codebase and database layer so all later features use PostgreSQL, SQLAlchemy and Alembic consistently.

The new BRD also adds or clarifies several deliverables that must be included in the development plan:

- A web application and a mobile application.
- PostgreSQL as the main database.
- SQLAlchemy for database models and queries.
- Alembic for migrations.
- Redis for fast QR-token, occupancy and caching operations.
- Multiple Docker services rather than one combined container.
- IoT integration for gym attendance scanning.
- Explicit error handling.
- Use-case diagram, architecture diagram, UML diagram and membership state-transition diagram.
- Membership policies for cancellation, freeze, renewal, QR use and class-booking rules.
- Staff and manager roles in addition to member, admin and PT.
- Design Architecture screenshots for the main web/admin and mobile screens. From Day 5 onward, these screenshots become the UI source of truth for layout, navigation, visual hierarchy and final QA.

The previous plan included AI chatbot work and personalization/recommendation extensions. To keep the 60-day schedule focused on coding the main app, AI chatbot work is moved to a post-60-day backlog. Personalization and recommendations should also stay out of the critical path unless the lecturer explicitly requires them before submission.

---

## 2. Comparison: Previous Plan vs New Brief

| Area | Previous Plan | New Brief | Action in Revised Plan |
|---|---|---|---|
| Primary database | MongoDB with Motor or Beanie | PostgreSQL | Replace MongoDB tasks with PostgreSQL, SQLAlchemy and Alembic tasks. |
| Database structure | Collections and document indexes | Relational tables and indexes | Add ERD, foreign keys, constraints and migration scripts. |
| Cache | Redis | Redis | Keep Redis for QR tokens, occupancy cache, rate limiting and frequent reads. |
| Frontend web | React, Vite, TypeScript, Tailwind CSS, shadcn/ui | Same | Keep the existing frontend scaffold. |
| API state library | TanStack Query | Marked as `???` in the new brief | Use TanStack Query. |
| Admin table library | TanStack Table | Marked as `????` in the new brief | Use TanStack Table. |
| Mobile | Responsive web app / PWA first | Expo and PWA | Add an Expo mobile app after the API becomes stable. Keep PWA readiness for the web app. |
| Docker | Frontend, backend, MongoDB, Redis, worker | Divide components into multiple Dockers | Use separate containers for frontend, backend, PostgreSQL, Redis, Celery worker and Celery Beat. Add an optional IoT simulator container. |
| IoT | Not explicitly planned | Explicitly requested | Add an IoT scanner integration layer and simulator. Support real hardware later without changing core services. |
| Error handling | General validation | Explicitly requested | Add centralized exceptions, logging, consistent API errors and frontend error states early. |
| Architecture documents | High-level architecture near the end | Lecturer requested architecture design before review | Move architecture, use-case, UML, ERD and state diagrams to the beginning of the remaining schedule. |
| Design architecture | No fixed screen reference | Added BRD section `10. Design Architecture` | Treat the exported screenshots as the coding reference for routes, layouts, reusable components and final UI comparison. |
| Roles | Member, admin, PT | Member tiers, admin, PT, staff, manager | Add a permissions matrix and role-based access control for all roles. |
| AI chatbot | Included in earlier plan | Can be implemented later | Remove from the 60-day main-app schedule and keep as a post-submission backlog item. |
| Personalization | Included | Removed from new brief | Keep outside the 60-day critical path unless the lecturer explicitly restores it. |

---

## 3. Final Technical Direction

### 3.1 Frontend Web

```text
React + Vite + TypeScript
Tailwind CSS + shadcn/ui
React Router
TanStack Query
TanStack Table
React Hook Form + Zod
Recharts
qrcode.react
Sonner or React Toastify
```

### 3.2 Mobile App

```text
Expo + React Native + TypeScript
Expo Router
TanStack Query
React Hook Form + Zod
SecureStore for auth tokens
```

### 3.3 Backend

```text
Python FastAPI
PostgreSQL
SQLAlchemy 2.x async ORM
Alembic migrations
Pydantic
Redis
Celery + Celery Beat or APScheduler
JWT authentication
bcrypt / passlib
ReportLab or WeasyPrint
FastAPI-Mail / SMTP
```

### 3.4 Later Backlog, Not in 60-Day Main App

```text
AI chatbot with authenticated backend context
AI chatbot guardrails and monitoring
Personalization profile and rule-based class recommendations, unless restored by lecturer
```

### 3.5 Docker Services

```text
frontend-web
backend-api
postgres-db
redis-cache
celery-worker
celery-beat
optional-iot-simulator
```

---

## 4. Updated Monorepo Codebase Structure

```text
ypgym/
├── frontend-web/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── layout/
│   │   │   ├── common/
│   │   │   └── charts/
│   │   ├── features/
│   │   │   ├── auth/
│   │   │   ├── member/
│   │   │   ├── memberships/
│   │   │   ├── attendance/
│   │   │   ├── classes/
│   │   │   ├── trainers/
│   │   │   ├── billing/
│   │   │   ├── notifications/
│   │   │   └── admin/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
│   ├── Dockerfile
│   └── package.json
│
├── mobile/
│   ├── app/
│   ├── src/
│   │   ├── features/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   └── types/
│   ├── app.json
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   ├── api/v1/endpoints/
│   │   ├── core/
│   │   │   ├── security.py
│   │   │   ├── permissions.py
│   │   │   ├── exceptions.py
│   │   │   ├── logging.py
│   │   │   └── rate_limit.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   ├── base.py
│   │   │   ├── redis.py
│   │   │   └── seed.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   ├── workers/
│   │   ├── integrations/
│   │   │   ├── email/
│   │   │   ├── invoice/
│   │   │   └── iot/
│   │   ├── utils/
│   │   └── tests/
│   ├── alembic/
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
│
├── iot-simulator/
│   ├── app/
│   ├── Dockerfile
│   └── README.md
│
├── docs/
│   ├── architecture/
│   ├── design/
│   ├── diagrams/
│   ├── api/
│   ├── database/
│   ├── policies/
│   └── demo/
│
├── docker-compose.yml
├── .env.example
├── README.md
└── .gitignore
```

---

## 5. Development Rules

1. Use the layered backend pattern:

```text
API endpoint -> Service -> Repository -> SQLAlchemy model -> PostgreSQL
```

2. Do not put business logic directly inside FastAPI route files.

3. Use Alembic for every database schema change. Do not manually alter tables without a migration.

4. Use Redis only for short-lived or frequently accessed data such as QR token TTL, occupancy counters, rate limits and cached configuration.

5. Store permanent business records in PostgreSQL, including payments, invoices, attendance sessions and audit logs.

6. Add backend validation with Pydantic and frontend validation with Zod.

7. Return consistent error responses from the API.

8. Write audit logs for sensitive admin, staff and manager actions.

9. Keep the IoT scanner separate from attendance business logic. Hardware should call the attendance API rather than connect directly to PostgreSQL.

10. Implement web features before the Expo mobile screens that consume the same APIs.

11. Treat `FYP Brief BRD - Anh Khoa - Design Architecture.docx` section `10. Design Architecture` and the exported ZIP screenshots as the UI source of truth. Every screen implementation should map back to a screenshot or an explicitly documented exception.

12. For every UI route, implement loading, empty, validation-error, API-error and permission-denied states before marking the route complete.

---

## 6. Design Architecture Coding Guide

**Primary reference:** `C:\Users\Admin\ypgym\FYP Brief BRD - Anh Khoa - Design Architecture.docx`, section `10. Design Architecture`.

**Exported screenshot sources:**

- `C:\Users\Admin\Downloads\stitch_ypgym_home_page.zip`
- `C:\Users\Admin\Downloads\stitch_ypgym_home_page (1).zip`
- `C:\Users\Admin\Downloads\stitch_member_mobile_app_design.zip`

### 6.1 Screen Inventory

**Web and admin screens**

1. Membership Policies
2. YPGym Home Page
3. Membership Plans
4. Member Dashboard
5. My QR Code
6. Register for YPGym
7. Login to YPGym
8. Forgot Password
9. Email Verification Success
10. Member CRM (Updated)
11. Admin Member Details (Updated)
12. Class & Schedule Management (Updated)
13. Attendance Dashboard
14. PT Assignment Management
15. Personal Trainer Dashboard

**Mobile member app screens**

1. Member Dashboard
2. Membership Renewal Selection
3. Renewal Success
4. QR Check-in
5. Class Booking
6. Member Profile

**Known design gap:** the web Class Booking screen exists in the Figma inventory but was not included in the exported ZIP files. Build the web Class Booking route from the mobile Class Booking flow, the Class & Schedule Management visual patterns and the member dashboard navigation style. Record this as an implementation note in `docs/design/route-screen-map.md`.

### 6.2 Route and Component Map

| Screenshot | Planned route or area | Main components to build or reuse |
|---|---|---|
| YPGym Home Page | `/` | Public top nav, hero, smart-training cards, facilities cards, footer |
| Register for YPGym | `/register` | Auth shell, form fields, password rules, inline validation, submit state |
| Login to YPGym | `/login` | Split auth layout, login form, forgot-password link, error alert |
| Forgot Password | `/forgot-password` | Auth card, neutral success message, reset-request error state |
| Email Verification Success | `/verify-email/success` and verification callback state | Success card, continue-to-login action, invalid/expired alternatives |
| Membership Plans | `/memberships` or `/plans` | Plan cards, discount badges, FAQ accordion, purchase CTA |
| Membership Policies | `/policies/membership` | Policy content layout, table-of-contents sidebar, policy cards |
| Member Dashboard | `/app/dashboard` | Member sidebar/top bar, membership summary, QR card, crowdedness card, upcoming classes, recent activity |
| My QR Code | `/app/qr` | QR code panel, refresh timer, access status, attendance history summary |
| Member CRM (Updated) | `/admin/members` | Admin shell, KPI cards, TanStack Table, search/filter toolbar, pagination |
| Admin Member Details (Updated) | `/admin/members/:id` | Profile header, membership tabs/cards, billing panel, attendance and action panels |
| Class & Schedule Management (Updated) | `/admin/classes` | Admin class calendar/list, class cards, create/edit dialog, schedule controls |
| Attendance Dashboard | `/admin/attendance` | Occupancy KPI cards, facility status, daily log table, recent check-ins |
| PT Assignment Management | `/admin/pt-assignments` | Assignment deck, trainer cards, active package table |
| Personal Trainer Dashboard | `/pt/dashboard` or admin/PT summary area | PT stats cards, schedule list, client summary, earnings placeholder |
| Web Class Booking | `/app/classes` | Derived from mobile booking screen plus web member layout and class-management cards |
| Mobile Member Dashboard | `mobile/app/(tabs)/dashboard` | Mobile top bar, membership card, QR shortcut, capacity card, upcoming classes, bottom nav |
| Mobile Membership Renewal Selection | `mobile/app/membership/renew` | Renewal status card, plan cards, payment CTA |
| Mobile Renewal Success | `mobile/app/membership/success` | Success state, confirmation details, dashboard CTA |
| Mobile QR Check-in | `mobile/app/(tabs)/qr` | QR panel, countdown, access status, history link |
| Mobile Class Booking | `mobile/app/(tabs)/classes` | Search/filter controls, class cards, book/join/waitlist states |
| Mobile Member Profile | `mobile/app/(tabs)/profile` | Profile header, menu rows, plan status, logout action |

### 6.3 UI Build Conventions

- Build shared shells first: public web nav, member web shell, admin web shell and mobile tab shell.
- Reuse component families across screens: cards, KPI tiles, tables, status badges, policy panels, QR panels, class cards, profile menu rows and action dialogs.
- Use the screenshots for spacing, density, hierarchy and navigation placement, but keep implementation responsive and accessible.
- Keep business logic in API/service layers; UI components should consume typed API data and render states.
- Add `docs/design/route-screen-map.md` to track screenshot source, implemented route, API dependencies, component owner and QA status.

---

## 7. Milestone Overview

| Days | Milestone | Main Deliverables |
|---|---|---|
| Days 1-4 | Completed foundation | Existing repository, initial Docker setup, FastAPI scaffold and React scaffold |
| Days 5-10 | Architecture migration, design architecture setup and technical baseline | PostgreSQL migration, Docker service split, architecture diagrams, UI route-screen map, UML, ERD, membership policy document, error-handling foundation |
| Days 11-21 | Authentication and membership | Registration, verification, login, RBAC, password reset, profile, plans, purchase, renewal, freeze, lifecycle, invoice, screenshot-aligned auth and membership screens |
| Days 22-29 | Admin CRM, billing and notifications | CRM, cancellation, revocation, audit logs, billing history, CSV export, preferences, reminders, broadcasts and admin visual shell |
| Days 30-38 | QR attendance, IoT and crowdedness | Rotating QR, scanner API, IoT simulator, duplicate prevention, timeout, Redis occupancy, My QR Code screen, Attendance Dashboard and heatmap |
| Days 39-45 | Classes, trainers and mobile critical flows | Class CRUD, booking, cancellation window, waitlist, trainer management, PT profiles, Expo foundation and mobile screenshot-aligned flows |
| Days 46-50 | Main app completion and operational polish | Design parity pass, cross-flow integration, mobile completion, manager analytics and feature freeze |
| Days 51-60 | Testing, performance, documentation, design parity and release | Integration tests, security pass, responsive QA, design screenshot comparison, documentation, demo data, deployment package and viva preparation |

---

# 8. Day-by-Day Development Plan

## Day 1 - Monorepo and repository foundation **[Completed]**

**Codebase area:** `ypgym/`, `docs/`, `frontend-web/`, `backend/`

**What should already exist:**

- Root repository with frontend, backend and docs folders.
- `.gitignore` for Node, Python, environment files and local build artifacts.
- Root README with project purpose and local-start instructions.

**Verification checkpoint:** Repository opens cleanly and the current folder structure is understandable.

---

## Day 2 - Initial Docker development environment **[Completed, revise on Day 5]**

**Codebase area:** `docker-compose.yml`, `.env.example`

**What should already exist:**

- Initial Docker Compose file.
- Environment variables for backend and frontend.
- Redis container or placeholder.

**Important migration note:** The previous setup may include MongoDB. Do not build more database-dependent features until Day 5 replaces MongoDB with PostgreSQL.

**Verification checkpoint:** Existing Docker files are committed so changes can be reviewed safely.

---

## Day 3 - FastAPI backend scaffold **[Completed]**

**Codebase area:** `backend/app/main.py`, `backend/app/api/v1/router.py`

**What should already exist:**

- FastAPI app entry point.
- CORS middleware.
- Swagger documentation at `/docs`.
- Health endpoint such as `GET /api/v1/health`.

**Verification checkpoint:** FastAPI launches and the health endpoint returns success.

---

## Day 4 - React frontend scaffold and base routing **[Completed]**

**Codebase area:** `frontend-web/src/app/`, `frontend-web/src/features/`

**What should already exist:**

- React + Vite + TypeScript project.
- Tailwind CSS and shadcn/ui setup or installation baseline.
- React Router routes for public, member and admin areas.
- Placeholder home page.

**Verification checkpoint:** Web frontend starts and renders the public route.

---

## Day 5 - Replace MongoDB setup with PostgreSQL and split Docker services

**Codebase area:** `docker-compose.yml`, `.env.example`, `backend/requirements.txt`, `docs/design/`

**Implementation instructions:**

- Remove MongoDB service and MongoDB-related environment variables from the old Docker setup.
- Add a `postgres-db` Docker service using PostgreSQL 16.
- Keep a separate `redis-cache` service.
- Add separate `backend-api`, `frontend-web`, `celery-worker` and `celery-beat` services.
- Add an optional `iot-simulator` service entry but keep it disabled by default using a Docker Compose profile.
- Add environment variables: `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `FRONTEND_URL`, email placeholders, QR token duration, attendance timeout and gym capacity.
- Add PostgreSQL health checks and make backend startup depend on database readiness.
- Create `docs/design/` and copy or reference the exported design screenshots there without committing unnecessary generated ZIPs.
- Start `docs/design/route-screen-map.md` using the Design Architecture screen inventory from section 6.

**Done when:** `docker compose up --build` starts PostgreSQL, Redis, backend and frontend successfully. Celery services may run with placeholder tasks without crashing.

---

## Day 6 - Add SQLAlchemy async database layer and Alembic migrations

**Codebase area:** `backend/app/db/session.py`, `backend/app/db/base.py`, `backend/alembic/`, `backend/alembic.ini`

**Implementation instructions:**

- Install `sqlalchemy`, `asyncpg`, `alembic` and `psycopg` or equivalent required packages.
- Create an async SQLAlchemy engine from `DATABASE_URL`.
- Add `AsyncSession` dependency for FastAPI routes.
- Initialize Alembic and configure it to import the SQLAlchemy Base metadata.
- Create a small test table or initial empty migration to validate the migration workflow.
- Add a backend/API dependency column to `docs/design/route-screen-map.md` so each screen records which endpoints it will need.
- Document the commands:

```bash
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

**Done when:** The backend connects to PostgreSQL, `alembic upgrade head` completes without errors and the design route map has API dependency placeholders.

---

## Day 7 - Prepare architecture, use-case and role-permission design for lecturer review

**Codebase area:** `docs/architecture/`, `docs/diagrams/`, `docs/design/route-screen-map.md`, `docs/policies/roles.md`

**Implementation instructions:**

- Draw a high-level architecture diagram showing web frontend, Expo mobile app, IoT scanner, FastAPI API layer, service layer, PostgreSQL, Redis, worker services, email and invoice integrations.
- Draw a use-case diagram covering Member, Admin, Staff, Manager and Personal Trainer.
- Define a role-permission matrix:
  - `member`: self-service membership, QR, booking and notifications.
  - `staff`: limited scanner, attendance and member-verification operations.
  - `manager`: reporting, configuration, approvals and operational dashboards.
  - `admin`: full CRM and account management.
  - `pt`: profile visibility and assigned-class access; limited dashboard only if time allows.
- Add an architecture description explaining why services are split into multiple Docker containers.
- Add route groups for public web, member web, admin web, PT web and mobile tabs.
- Define shared UI shells before coding feature screens: public layout, member layout, admin layout and mobile bottom-tab layout.

**Done when:** The lecturer can review a clear diagram package and the developer has a screen-by-screen coding checklist before deeper implementation begins.

---

## Day 8 - Create ERD, UML class diagram and membership state-transition diagram

**Codebase area:** `docs/diagrams/`, `docs/database/erd.md`, `docs/policies/membership-lifecycle.md`

**Implementation instructions:**

- Draw an ERD for the core PostgreSQL tables.
- Draw a UML class diagram for the core backend entities and service relationships.
- Draw a membership state-transition diagram covering:

```text
Pending Verification -> Active -> Expiring Soon -> Expired
Active -> Frozen -> Active
Active -> Cancellation Requested -> Cancelled
Active -> Revoked
```

- Document allowed and forbidden transitions.
- Include who can trigger each transition: member, staff, manager, admin or scheduled worker.
- Cross-reference the membership lifecycle with the Membership Plans, Membership Policies, My QR Code and mobile renewal screens.

**Done when:** The database and membership lifecycle are understandable before table implementation starts.

---

## Day 9 - Write membership, class, QR and cancellation policy document

**Codebase area:** `docs/policies/`

**Implementation instructions:**

Create policy files for:

- Membership durations and volume discounts.
- Freeze eligibility, maximum freeze period and whether expiry extends after freeze.
- Cancellation request flow and refund, account-credit or forfeit outcomes.
- Renewal rules before and after expiry.
- QR token expiry duration and duplicate scan window.
- Attendance timeout period and optional exit scanning.
- Class cancellation window and waitlist promotion rule.
- Member tiers: Normal, Advance and VIP. Define whether tiers change price, class access, PT access or only CRM labels.
- UI policy notes for which messages appear on Membership Policies, My QR Code, Membership Renewal Selection and mobile QR Check-in screens.

Do not leave these decisions inside code comments only. The backend services should later read configurable values where suitable.

**Done when:** Business rules are explicit enough to implement without guessing.

---

## Day 10 - Centralized error handling, structured logging and frontend error states

**Codebase area:** `backend/app/core/exceptions.py`, `backend/app/core/logging.py`, `frontend-web/src/lib/`, `frontend-web/src/components/common/`, `mobile/src/components/`

**Implementation instructions:**

- Define API error response format:

```json
{
  "error": {
    "code": "MEMBERSHIP_INACTIVE",
    "message": "Your membership is not active.",
    "details": null
  }
}
```

- Add FastAPI exception handlers for validation errors, authentication failures, permission failures, missing resources and business-rule conflicts.
- Add structured logs for request failures and sensitive actions.
- Create frontend error helpers that map API errors to toast messages and inline form errors.
- Add reusable loading, empty-state and error-state components.
- Add matching mobile loading, empty and API-error patterns so Expo screens follow the same business-state language.
- Record expected states in `docs/design/route-screen-map.md` for each screenshot-backed route.

**Done when:** Errors are predictable and understandable instead of raw stack traces or inconsistent messages, and every planned UI screen has documented loading, empty and error states.

---

## Day 11 - Create core PostgreSQL models and first real migration

**Codebase area:** `backend/app/models/`, `backend/alembic/versions/`

**Implementation instructions:**

Create SQLAlchemy models for:

- `users`
- `email_verifications`
- `password_resets`
- `membership_plans`
- `user_memberships`
- `system_configurations`

Add:

- UUID primary keys.
- Timestamps.
- Unique constraints for email and phone.
- Indexes for user ID, membership status and expiry date.
- Enums or validated strings for role, tier and membership status.

Generate and run an Alembic migration.
- Update the route-screen map with which screens depend on users, memberships, plans and system configuration data.

**Done when:** Core account and membership tables exist in PostgreSQL and are visible through a database client.

---

## Day 12 - Registration backend and frontend form

**Codebase area:** `backend/app/api/v1/endpoints/auth.py`, `backend/app/services/auth_service.py`, `backend/app/repositories/user_repository.py`, `frontend-web/src/features/auth/`

**Implementation instructions:**

- Create `POST /auth/register`.
- Validate required fields, duplicate email and duplicate phone.
- Hash passwords using bcrypt or passlib.
- Default new accounts to `member`, `normal` tier and pending email verification.
- Build the registration form with React Hook Form and Zod.
- Display backend validation errors cleanly.
- Match the Register for YPGym screenshot for layout, centered form card, field order, submit state and login link.

**Done when:** A new member account can be registered from the web UI and duplicate users are rejected safely.

---

## Day 13 - Email verification flow

**Codebase area:** `email_verifications`, auth service, `VerifyEmailPage.tsx`

**Implementation instructions:**

- Generate a time-limited verification token after registration.
- Store a hashed token and expiry date in PostgreSQL.
- Send a verification email using a development SMTP tool or log the link during local development.
- Create `POST /auth/verify-email` or `GET /auth/verify-email?token=...`.
- Add success, invalid-token and expired-token UI states.
- Match the Email Verification Success screenshot for the successful verification state.

**Done when:** An unverified user becomes verified only after using a valid token.

---

## Day 14 - Login, JWT and complete RBAC foundation

**Codebase area:** `backend/app/core/security.py`, `permissions.py`, `frontend-web/src/hooks/useAuth.ts`

**Implementation instructions:**

- Create `POST /auth/login`.
- Generate JWT with user ID, role and tier.
- Add FastAPI dependencies for current user and role checks.
- Implement role guards for member, staff, manager, admin and PT.
- Add protected route components on the web frontend.
- Block full access for unverified accounts.
- Match the Login to YPGym screenshot for auth layout, visual hierarchy and error placement.

**Done when:** Different roles can sign in and protected APIs reject unauthorized access.

---

## Day 15 - Forgot password and password reset

**Codebase area:** `password_resets`, auth endpoints, web auth pages

**Implementation instructions:**

- Create `POST /auth/forgot-password` and `POST /auth/reset-password`.
- Store hashed reset token and expiry.
- Return a neutral response even if the email does not exist.
- Invalidate reset token after successful use.
- Build Forgot Password and Reset Password pages.
- Match the Forgot Password screenshot for desktop layout and neutral success messaging.

**Done when:** A verified user can securely reset the password and log in with the new credential.

---

## Day 16 - Profile self-update and account security

**Codebase area:** `backend/app/api/v1/endpoints/users.py`, member profile feature

**Implementation instructions:**

- Create `GET /users/me` and `PATCH /users/me`.
- Allow updates to name and phone.
- Require current password for password changes.
- Require email re-verification when email changes.
- Add web Profile Settings page and update confirmation messages.
- Prepare shared profile-menu data for the later mobile Member Profile screen.

**Done when:** Members can update profile fields without bypassing sensitive-change validation.

---

## Day 17 - Membership plans, tiers and configuration seed

**Codebase area:** membership models, seed script, `system_configurations`

**Implementation instructions:**

- Seed plans: 1 month, 3 months, 6 months, 1 year, 2 years and 3 years.
- Store price, duration, discount and active status in PostgreSQL.
- Seed gym capacity, QR token TTL, attendance timeout, duplicate-scan window, class cancellation window and waitlist size.
- Add member tier values: `normal`, `advance`, `vip`.
- Define tier-specific rules only where approved by policy.
- Seed plan names and values so they can populate the Membership Plans and mobile Membership Renewal Selection screens.

**Done when:** A clean database can be populated with plans and operational configuration using one seed command.

---

## Day 18 - Membership plan display and tier-aware UI

**Codebase area:** membership API and web membership feature

**Implementation instructions:**

- Create `GET /membership-plans`.
- Build responsive plan cards with duration, price and discount.
- Show any approved tier benefits clearly.
- Route guests to login/register and verified members to purchase.
- Match the Membership Plans screenshot for plan-card hierarchy, discount badges, FAQ area and primary CTA placement.

**Done when:** Users can browse plans cleanly on desktop and phone widths.

---

## Day 19 - Membership purchase, renewal and mock payment

**Codebase area:** `membership_service.py`, `billing_service.py`, purchase UI

**Implementation instructions:**

- Create `POST /memberships/purchase`.
- Use plan prices from the database, never from frontend totals.
- Implement mock payment first.
- If membership is active, renew from current expiry date. Otherwise, start from today.
- Use a database transaction to create payment and membership records safely.
- Protect against duplicate payment submissions with an idempotency key or request reference.
- Implement renewal UI states needed by the mobile Membership Renewal Selection and Renewal Success screens, even if the Expo screens are built later.

**Done when:** Purchase and renewal update membership correctly without duplicate records.

---

## Day 20 - Invoice generation and payment history

**Codebase area:** invoice integration, invoice service, billing pages

**Implementation instructions:**

- Generate invoice PDFs with ReportLab or WeasyPrint.
- Store immutable invoice metadata in PostgreSQL.
- Add member endpoints for payment and invoice history.
- Add invoice download/view link.
- Add an admin billing table placeholder for later expansion.
- Ensure member dashboard and admin member-detail screens can show latest invoice/payment summary cards.

**Done when:** Every successful membership purchase creates a retrievable invoice.

---

## Day 21 - Membership lifecycle, freeze and expiry worker

**Codebase area:** `membership_service.py`, worker tasks, membership status tests

**Implementation instructions:**

- Implement status calculation for Active, Expiring Soon, Expired, Frozen, Cancelled, Revoked and Pending Verification.
- Add membership freeze request and approval logic according to the policy document.
- Add a scheduled worker to mark memberships as expiring soon or expired.
- Ensure frozen, cancelled and revoked members cannot use QR attendance or class booking.
- Make the status messages reusable by My QR Code, Membership Policies, mobile QR Check-in and mobile dashboard screens.

**Done when:** Membership transitions follow the state diagram and access control respects status.

---

## Day 22 - Admin CRM member list and member detail view

**Codebase area:** admin endpoints, `MembersCRMPage.tsx`, TanStack Table

**Implementation instructions:**

- Create paginated admin member-list endpoint with search and filters.
- Add filters for role, tier, membership status and expiry date.
- Use TanStack Table in the web admin dashboard.
- Add a member-detail drawer or page with profile, membership, billing, attendance and booking tabs.
- Match the Member CRM (Updated) screenshot for admin shell, KPI cards, filters, table density and pagination.
- Start the Admin Member Details route using the updated screenshot as the target layout.

**Done when:** Admin can find a user and review the complete customer record.

---

## Day 23 - Cancellation approval, revocation and audit trail

**Codebase area:** cancellation models, audit-log model, admin member actions

**Implementation instructions:**

- Create member cancellation request endpoint.
- Create manager/admin approval endpoint.
- Require outcome selection: refund, account credit or forfeit.
- Add membership revocation with mandatory reason.
- Write audit logs for cancellation, revocation, approval and sensitive profile changes.
- Surface cancellation and revocation actions inside the Admin Member Details layout rather than as disconnected admin-only forms.

**Done when:** Sensitive membership actions are traceable and cannot be performed silently.

---

## Day 24 - Notification preferences and in-app notification records

**Codebase area:** notification models, notification service, member preferences page

**Implementation instructions:**

- Add notification and preference tables.
- Build `GET/PATCH /notifications/preferences/me`.
- Support email and in-app preferences.
- Add in-app notification list endpoint.
- Build Notification Preferences page.
- Keep preference UI consistent with the mobile Member Profile menu row and settings pattern.

**Done when:** Members can control supported notification channels and see in-app notifications.

---

## Day 25 - Expiry reminders and admin broadcasts

**Codebase area:** notification workers, broadcast announcements table, admin broadcast page

**Implementation instructions:**

- Schedule expiry reminders for 7 days, 3 days and 1 day before expiry.
- Prevent duplicate sends using notification history.
- Create broadcast announcements with audience, title, message, active period and creator.
- Display active broadcasts on the member dashboard.
- Audit broadcast creation.
- Render active broadcasts in the member dashboard card system shown in the Member Dashboard screenshot.

**Done when:** Members receive reminders and admins can publish gym-wide announcements.

---

## Day 26 - Admin billing view and CSV export

**Codebase area:** billing admin endpoints, CSV utility, billing dashboard

**Implementation instructions:**

- Create admin payment and invoice endpoints with filters.
- Add CSV export for billing results and filtered member list.
- Ensure export uses the same filters as the visible tables.
- Audit exports if the exported data includes personal information.
- Reuse the admin table toolbar and card visual language from Member CRM and Admin Member Details.

**Done when:** Admin can review and export CRM and billing data.

---

## Day 27 - Audit-log admin page and manager operations

**Codebase area:** audit endpoints, `AdminAuditLogPage.tsx`, manager permissions

**Implementation instructions:**

- Add audit log list endpoint with date, action, actor and target filters.
- Create manager/admin-only audit-log page.
- Confirm staff cannot access full CRM or sensitive billing data.
- Confirm manager can access approvals, analytics and configuration if that matches the approved matrix.
- Use the admin shell/sidebar/topbar pattern from the CRM screenshots for audit and manager-only pages.

**Done when:** Auditability and role separation are visible in the UI.

---

## Day 28 - System configuration management

**Codebase area:** configuration endpoints, admin settings page, Redis cache

**Implementation instructions:**

- Add manager/admin settings page for gym capacity, QR token TTL, attendance timeout, duplicate-scan window, class-cancellation window and waitlist limit.
- Validate unsafe values.
- Cache frequently read settings in Redis.
- Invalidate cache after update.
- Audit every configuration change.
- Match admin settings controls to the Class & Schedule Management and Admin Member Details visual patterns.

**Done when:** Operational values can be changed without editing source code.

---

## Day 29 - Attendance database tables and migration

**Codebase area:** attendance models, Alembic migration, attendance repositories

**Implementation instructions:**

Create tables for:

- `qr_tokens` if server-side token tracking is used.
- `attendance_sessions`.
- `attendance_events` for check-in, check-out, timeout and manual-close events.
- Optional `iot_devices` for registered scanner devices.

Add indexes for active session checks, user ID, event timestamp and device ID.
- Update `docs/design/route-screen-map.md` with attendance fields needed by the My QR Code, Attendance Dashboard and mobile QR Check-in screens.

**Done when:** Attendance persistence is migration-controlled and optimized for frequent queries.

---

## Day 30 - Rotating QR token generation

**Codebase area:** `backend/app/services/qr_service.py`, Redis, web QR page

**Implementation instructions:**

- Create `GET /attendance/qr-token/me`.
- Generate signed short-lived token with user ID, issued-at, expiry and token ID.
- Store token ID or hash in Redis with TTL.
- Block generation for inactive, frozen, cancelled, revoked or expired memberships.
- Build web QR page with automatic refresh before expiry.
- Match the My QR Code screenshot for QR panel hierarchy, refresh timer, membership status and attendance-history summary.

**Done when:** Eligible members receive rotating QR codes instead of a permanent static image.

---

## Day 31 - Scanner API and IoT integration contract

**Codebase area:** `backend/app/integrations/iot/`, attendance endpoints, `docs/api/iot-scanner.md`

**Implementation instructions:**

- Define the scanner request contract.
- Create a scanner authentication method such as device API key or signed device token.
- Create `POST /attendance/check-in` accepting QR token and device ID.
- Return machine-readable success and error responses.
- Document how a future ESP32, Raspberry Pi or tablet scanner will call the API.
- Ensure success and failure responses can drive the mobile QR Check-in screen states cleanly.

**Done when:** Attendance scanning is hardware-agnostic and documented.

---

## Day 32 - IoT scanner simulator

**Codebase area:** `iot-simulator/`, optional Docker service

**Implementation instructions:**

- Build a simple simulator CLI or small web page that submits scanned QR tokens to the check-in endpoint.
- Include device ID and API key.
- Support success, invalid token, expired token and inactive membership scenarios.
- Add optional Docker profile:

```bash
docker compose --profile iot up --build
```
- Include demo scenarios that prove the My QR Code screen and mobile QR Check-in screen respond correctly.

**Done when:** You can demo IoT-style scanning without needing physical hardware during every development session.

---

## Day 33 - Duplicate prevention, check-out and attendance timeout worker

**Codebase area:** attendance service, Celery worker, attendance endpoints

**Implementation instructions:**

- Prevent duplicate active sessions for the same member.
- Add optional `POST /attendance/check-out`.
- Add scheduled timeout task for sessions older than configured timeout.
- Create attendance events for check-out and timeout.
- Allow staff/admin manual closure with required reason and audit log.
- Feed active/closed session status into the Attendance Dashboard screen and member attendance summaries.

**Done when:** Occupancy decreases correctly and abnormal sessions can be resolved safely.

---

## Day 34 - Redis occupancy counter and crowdedness calculation

**Codebase area:** crowdedness service, Redis, dashboard API

**Implementation instructions:**

- Calculate active attendance-session count.
- Store or cache occupancy in Redis.
- Read gym capacity from configuration.
- Return percentage and status:
  - Low: 0%-30%
  - Moderate: 31%-60%
  - Busy: 61%-85%
  - Very Crowded: 86%+
- Reconcile Redis cache from PostgreSQL if cache is missing or stale.
- Shape the crowdedness response for the Member Dashboard, mobile Member Dashboard and Attendance Dashboard cards.

**Done when:** Member and admin dashboards show accurate capacity-based crowdedness.

---

## Day 35 - Member attendance UI and staff attendance-management UI

**Codebase area:** web attendance feature, staff routes, admin attendance page

**Implementation instructions:**

- Add Attendance History page for members.
- Add active-session and historical-session table for staff and admin.
- Add filters by date, status and member.
- Add manual-close action only for permitted roles.
- Show device ID or event source where useful.
- Match the Attendance Dashboard screenshot for KPI cards, facility status, recent check-ins and daily log table.

**Done when:** Attendance is visible and manageable from the correct role-specific pages.

---

## Day 36 - Peak-hours heatmap and attendance analytics

**Codebase area:** analytics endpoint, Recharts heatmap component

**Implementation instructions:**

- Aggregate attendance check-ins by weekday and hour.
- Add `GET /admin/analytics/peak-hours`.
- Render a day-by-hour heatmap or grid chart.
- Add KPI cards for current occupancy, daily visits and busiest hour.
- Keep analytics cards visually consistent with the Attendance Dashboard and later manager dashboard.

**Done when:** Managers can visually understand gym usage patterns.

---

## Day 37 - Class, trainer and booking database tables

**Codebase area:** class models, trainer models, migrations

**Implementation instructions:**

Create tables for:

- `personal_trainers`
- `classes`
- `class_bookings`
- `class_waitlists`

Add foreign keys, capacity validation, trainer relationship and useful indexes.
- Add route-screen dependencies for Class & Schedule Management, Web Class Booking, mobile Class Booking, PT Assignment Management and Personal Trainer Dashboard.

**Done when:** Class operations have a clean relational schema.

---

## Day 38 - Admin class CRUD

**Codebase area:** class endpoints, class service, admin class page

**Implementation instructions:**

- Create admin endpoints to create, update, cancel and list classes.
- Validate time, capacity and trainer assignment.
- Build admin table and create/edit dialog.
- Add confirmation before class cancellation.
- Match the Class & Schedule Management (Updated) screenshot for admin layout, schedule controls, right-side cards and action placement.

**Done when:** Admin can manage the class schedule without direct database edits.

---

## Day 39 - PT profile management and member-facing PT cards

**Codebase area:** trainer endpoints, admin PT page, PT card component

**Implementation instructions:**

- Create PT profile fields: name, bio, specialty, availability summary, active status and assigned classes.
- Add admin create, update and deactivate actions.
- Display PT profile card on member class pages.
- Keep PT dashboard lightweight unless lecturer requests a larger PT workflow.
- Match PT Assignment Management and Personal Trainer Dashboard screenshots for admin/PT layout decisions.

**Done when:** Members see trainer information and admins can maintain it.

---

## Day 40 - Member class listing and booking

**Codebase area:** member class pages, class booking service

**Implementation instructions:**

- Add upcoming-class list endpoint with remaining capacity and trainer summary.
- Create `POST /classes/{class_id}/book`.
- Block inactive memberships, duplicate bookings, cancelled classes and over-capacity bookings.
- Build responsive class-list page.
- Build the web Class Booking route from the mobile Class Booking screenshot plus web member-shell patterns because the web screenshot export is missing.

**Done when:** Active members can browse and book available classes.

---

## Day 41 - Class cancellation window and waitlist

**Codebase area:** booking service, waitlist service, My Bookings page

**Implementation instructions:**

- Add cancellation endpoint that checks the configured cancellation window.
- Add waitlist join endpoint when class is full.
- Preserve queue order using timestamp and position.
- On cancellation, notify or auto-enrol first waitlisted member according to policy.
- Add My Bookings page with booking and waitlist state.
- Match mobile Class Booking states for full, joined, waitlisted and available classes.

**Done when:** Class capacity and cancellation are handled fairly and consistently.

---

## Day 42 - Member dashboard integration

**Codebase area:** member dashboard page, dashboard backend endpoint

**Implementation instructions:**

- Build one dashboard payload combining membership status, QR eligibility, crowdedness, upcoming bookings, unread notifications and active broadcasts.
- Show quick actions for Buy/Renew, QR Code, Classes and Profile.
- Add loading, empty and error states.
- Ensure the dashboard works on mobile width.
- Match the Member Dashboard screenshot on web and prepare the same payload for the mobile Member Dashboard screen.

**Done when:** A member can understand the account state immediately after login.

---

## Day 43 - Expo mobile-app scaffold and shared API conventions

**Codebase area:** `mobile/`, mobile router, mobile API client

**Implementation instructions:**

- Create Expo TypeScript app.
- Add Expo Router, TanStack Query and SecureStore.
- Create mobile auth token handling.
- Reuse backend endpoint contracts rather than creating a separate backend.
- Create placeholder screens for Dashboard, QR Check-in, Classes, Membership Renewal, Renewal Success and Profile based on the mobile screenshots.

**Done when:** The Expo app launches and can call the backend health endpoint.

---

## Day 44 - Mobile authentication, dashboard and QR critical flow

**Codebase area:** mobile auth, dashboard and attendance features

**Implementation instructions:**

- Connect mobile login to JWT API.
- Store token using SecureStore.
- Render member dashboard summary.
- Render rotating QR code with refresh timer.
- Handle expired, frozen and revoked membership messages clearly.
- Match the mobile Member Dashboard and QR Check-in screenshots for layout, bottom nav and status messages.

**Done when:** A member can log in on the Expo app and display a valid rotating QR code.

---

## Day 45 - Mobile classes, notifications and PWA readiness

**Codebase area:** mobile class and notification screens, web manifest/meta

**Implementation instructions:**

- Add mobile class browsing and booking.
- Add My Bookings and notification list screens.
- Add mobile Membership Renewal Selection, Renewal Success and Member Profile screens.
- Add basic PWA-ready metadata to the web app.
- Verify that core member features still work in responsive mobile browser view.

**Done when:** Mobile users can perform the most important self-service tasks.

---

## Day 46 - Web design-architecture parity pass

**Codebase area:** web routes, shared layouts, `docs/design/route-screen-map.md`

**Implementation instructions:**

- Compare implemented public, auth, member and admin web routes against the Design Architecture screenshots.
- Fix spacing, navigation, card hierarchy, table density, button placement and status badges.
- Ensure each web/admin screen has loading, empty, error and permission states.
- Mark each web/admin route as `implemented`, `partial` or `blocked` in the route-screen map.
- Keep AI chatbot and personalization out of this pass; they remain later backlog items.

**Done when:** The available web/admin Design Architecture screens have matching implemented routes or documented exceptions.

---

## Day 47 - Mobile app completion and design parity

**Codebase area:** Expo mobile screens, mobile components, mobile API client

**Implementation instructions:**

- Complete the six mobile Design Architecture screens: Dashboard, Membership Renewal Selection, Renewal Success, QR Check-in, Class Booking and Member Profile.
- Reuse backend endpoint contracts and shared response types from the web app.
- Verify token storage, logout, expired session handling and API-error presentation.
- Match the bottom navigation, dark theme, green accent states and profile/menu row layout from the screenshots.

**Done when:** The Expo app supports the screenshot-backed member flows without needing a separate backend.

---

## Day 48 - Cross-flow integration and end-to-end main-app journey

**Codebase area:** web app, mobile app, backend services, seed data

**Implementation instructions:**

- Run the main member journey from registration through verification, login, membership purchase/renewal, invoice, QR display, check-in, crowdedness update and class booking.
- Run the admin journey through member CRM, member details, class scheduling, attendance dashboard and PT assignment management.
- Fix API contract mismatches between backend, web and mobile.
- Confirm all main-app routes work with seeded data and empty data.

**Done when:** The main app works as a connected product rather than isolated pages.

---

## Day 49 - Manager analytics and operational dashboard

**Codebase area:** analytics services, admin dashboard, manager dashboard cards

**Implementation instructions:**

- Add membership trends, class popularity, attendance patterns and revenue summaries.
- Add manager dashboard cards using the admin visual shell and Attendance Dashboard card style.
- Cache expensive summaries or compute them through scheduled worker tasks.
- Ensure manager permissions differ from staff and normal admin actions where documented.

**Done when:** Managers can see useful operational insights without running manual reports.

---

## Day 50 - Feature freeze, backlog split and implementation cleanup

**Codebase area:** whole monorepo, `docs/design/`, backlog notes

**Implementation instructions:**

- Freeze the main-app scope for final testing.
- Move AI chatbot, personalization and rule-based recommendations to a clearly labelled post-60-day backlog.
- Remove unused placeholder routes, TODO-only pages and dead API stubs from the main demo path.
- Update `docs/design/route-screen-map.md` with final status for every screenshot-backed route.
- Create a bug list grouped by backend, web, mobile, data, Docker and documentation.

**Done when:** The main application is feature-complete enough for testing, and later/backlog features cannot distract from release preparation.

---

## Day 51 - Backend tests: authentication, roles and membership

**Codebase area:** backend tests

**Implementation instructions:**

- Test registration, duplicate account, verification, login and password reset.
- Test role permissions for member, staff, manager, admin and PT.
- Test membership purchase, renewal, freeze, cancellation and revocation.
- Use a dedicated test database.

**Done when:** Core account and membership logic passes repeatable automated tests.

---

## Day 52 - Backend tests: attendance, IoT and crowdedness

**Codebase area:** attendance and IoT tests

**Implementation instructions:**

- Test valid, invalid and expired QR tokens.
- Test duplicate check-in prevention.
- Test check-out and timeout.
- Test scanner-device authentication.
- Test Redis cache reconciliation from PostgreSQL.
- Test percentage-based crowdedness mapping.

**Done when:** Attendance logic behaves correctly under normal and edge cases.

---

## Day 53 - Backend tests: classes, billing, audit and configuration

**Codebase area:** class, billing, audit and configuration tests

**Implementation instructions:**

- Test capacity, booking cancellation window and waitlist promotion.
- Test invoice creation and CSV export.
- Test audit logs for sensitive actions.
- Test configuration validation.

**Done when:** High-risk business rules are protected by tests.

---

## Day 54 - Performance pass for 1000+ registered users

**Codebase area:** PostgreSQL indexes, query optimization, Redis cache, docs

**Implementation instructions:**

- Add and verify indexes for frequent filters and joins.
- Add pagination to CRM, billing, audit and attendance lists.
- Avoid N+1 queries using relationship loading strategy.
- Cache crowdedness and configuration values in Redis.
- Run a small load test for login, crowdedness and class-list endpoints.
- Document the results and limitations honestly.

**Done when:** The system has a credible scalability story for 1000+ registered users.

---

## Day 55 - Security hardening

**Codebase area:** security core, rate limiting, Docker secrets, CORS

**Implementation instructions:**

- Add Redis-backed rate limits for login, forgot password and scanner endpoints.
- Review JWT expiry and role checks.
- Confirm no secrets are committed.
- Validate CORS configuration.
- Review CSV export permissions.
- Confirm error responses do not leak stack traces or sensitive data.

**Done when:** Common security mistakes are removed and sensitive routes are protected.

---

## Day 56 - Responsive UI, accessibility and end-to-end error-state QA

**Codebase area:** web and mobile UI

**Implementation instructions:**

- Test desktop, tablet and phone layouts.
- Prioritize dashboard, QR, class booking, login and admin tables.
- Fix overflow and table scrolling.
- Add labels, readable contrast, keyboard usability and clear validation messages.
- Verify loading, empty, offline and API-error states.
- Compare implemented routes against the Design Architecture screenshots and record pass/fail notes in `docs/design/route-screen-map.md`.

**Done when:** Main flows remain usable even when data is empty or an API request fails, and screenshot-backed screens have documented design-parity status.

---

## Day 57 - Final architecture and documentation update

**Codebase area:** `docs/architecture/`, `docs/api/`, `docs/database/`, `docs/design/`, README files

**Implementation instructions:**

- Update diagrams so they match the implemented code.
- Add API summary and Swagger link.
- Add ERD and migration instructions.
- Add Docker service description.
- Add IoT scanner integration notes.
- Add role-permission matrix and policy files.
- Add the final route-screen map with implemented routes, screenshot references and documented exceptions.

**Done when:** Another developer or examiner can understand the architecture without opening every code file.

---

## Day 58 - Demo seed data and examiner demo script

**Codebase area:** seed script, `docs/demo/demo-script.md`

**Implementation instructions:**

Seed:

- Admin, manager, staff, PT and member accounts.
- VIP, Advance and Normal members.
- Active, Frozen, Expired, Revoked and Cancelled memberships.
- Plans, payments, invoices and notifications.
- PT profiles, classes, bookings and waitlist entries.
- Attendance logs for the heatmap.
- Broadcast messages.

Prepare a demo sequence:

1. Member login.
2. Membership purchase or renewal.
3. Invoice view.
4. Rotating QR display.
5. IoT simulator check-in.
6. Crowdedness update.
7. Class booking and waitlist.
8. Admin CRM action with audit log.
9. Analytics heatmap.
10. Mobile dashboard, QR check-in and profile review.

**Done when:** Demo data can be recreated reliably from a clean database.

---

## Day 59 - Integration bug fixing and deployment rehearsal

**Codebase area:** whole monorepo

**Implementation instructions:**

- Run the full demo from a clean database.
- Fix navigation, migration, Docker, validation and API errors.
- Rebuild all containers from scratch.
- Confirm Alembic migrations run automatically or through documented steps.
- Test Expo app against the same backend.
- Confirm SMTP development mode and PDF generation work.
- Confirm all Design Architecture routes either match the screenshot target or have a documented exception.

**Done when:** The project can be started and demonstrated without manual emergency fixes.

---

## Day 60 - Final release package and viva checklist

**Codebase area:** final build, docs, screenshots, release tag

**Implementation instructions:**

- Create final screenshots of web, mobile and admin flows.
- Place final screenshots next to the Design Architecture references for examiner comparison.
- Tag a final Git commit.
- Create a backup archive.
- Prepare viva notes explaining:
  - Why PostgreSQL is used.
  - Why Redis is still needed.
  - Why Docker services are separated.
  - How IoT scanners communicate safely.
  - How rotating QR prevents screenshot sharing.
  - How occupancy decreases through check-out or timeout.
  - How audit logs support accountability.
  - How JWT and RBAC protect different roles.
  - How the implemented UI follows the Design Architecture screenshots.
  - How the application can scale to 1000+ registered users.

**Done when:** The system is submission-ready and you can explain every major design choice clearly.

---

# 9. Revised PostgreSQL Table Checklist

| Table | Purpose |
|---|---|
| `users` | Account, role, tier and profile data |
| `email_verifications` | Verification tokens and expiry |
| `password_resets` | Password-reset tokens and expiry |
| `membership_plans` | Plan durations, prices and discounts |
| `user_memberships` | Membership lifecycle and freeze information |
| `payments` | Payment or mock-payment records |
| `invoices` | Immutable invoice metadata and PDF references |
| `notifications` | In-app notifications and delivery status |
| `notification_preferences` | Member communication choices |
| `broadcast_announcements` | Gym-wide notices |
| `cancellation_requests` | Cancellation request and refund/credit/forfeit outcome |
| `audit_logs` | Sensitive-action trail |
| `system_configurations` | Capacity, timeout and policy configuration |
| `qr_tokens` | Optional persistent QR-token metadata |
| `attendance_sessions` | Active and historical visits |
| `attendance_events` | Check-in, check-out, timeout and manual-close events |
| `iot_devices` | Registered scanner devices |
| `personal_trainers` | PT profile information |
| `classes` | Class schedule, capacity and trainer relationship |
| `class_bookings` | Confirmed bookings |
| `class_waitlists` | Waitlist queue |
| `fitness_forms` | Member-submitted fitness information |

---

# 10. Final Submission Checklist

- [ ] Days 1-4 existing work has been reviewed and committed before migration.
- [ ] MongoDB dependencies have been removed from the revised backend path.
- [ ] PostgreSQL and Redis run through Docker Compose.
- [ ] SQLAlchemy async session and Alembic migration workflow work correctly.
- [ ] Architecture diagram, use-case diagram, ERD, UML class diagram and membership state diagram are included.
- [ ] Design Architecture route-screen map is complete and references the updated BRD screenshots.
- [ ] Membership policies are documented.
- [ ] Error handling uses a consistent API response format.
- [ ] Registration, verification, login, forgot password and profile update work.
- [ ] Member, staff, manager, admin and PT permissions are documented and enforced.
- [ ] Membership purchase, renewal, freeze, cancellation, revocation and expiry work.
- [ ] Invoice, billing history and CSV export work.
- [ ] Notification preferences, reminders and broadcasts work.
- [ ] Rotating QR, scanner endpoint, IoT simulator, duplicate prevention and timeout work.
- [ ] Crowdedness is capacity-based and decreases correctly.
- [ ] Class CRUD, booking, cancellation window, waitlist and PT cards work.
- [ ] Expo app supports the most important member flows.
- [ ] Implemented web/admin/mobile screens have been compared against Design Architecture screenshots.
- [ ] Automated tests pass.
- [ ] Docker rebuild and demo rehearsal succeed from a clean environment.
- [ ] README and viva notes are complete.

---

# 11. Immediate Next Action

Because the previous project has reached approximately Day 3-4, start with **Day 5**. Do not continue with MongoDB-specific tasks from the old schedule. The first priority is to update Docker Compose, install PostgreSQL dependencies, initialize SQLAlchemy and Alembic, create `docs/design/route-screen-map.md`, and prepare the early architecture diagrams requested by the lecturer. AI chatbot, personalization and recommendation features are post-60-day backlog unless the lecturer explicitly restores them to the required scope.
