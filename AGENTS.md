# YPGym Coding Agent Instructions

These instructions apply to all coding-agent work performed in this repository.

## Project context

YPGym is a gym-management web application with frontend, backend, PostgreSQL, Redis, Celery, authentication, membership, attendance, class scheduling, billing, notification, administrative, personal-trainer, member-facing, and optional IoT scanner functionality.

The project already contains an established architecture and completed development work through Day 38. Preserve the current design and reuse existing implementations before introducing new ones. Keep Day 39 and later scope separate unless a newer requirement explicitly changes that boundary.

The BRD Design Architecture document, `docs/design/route-screen-map.md`, the repository's shared visual system, and current project documentation are the visual and functional sources of truth unless a newer requirement explicitly overrides them. No separate Figma file is currently documented as available.

---

## Ponytail development mode

Work like a careful senior developer.

Prefer the smallest complete and correct implementation. Minimal does not mean careless, incomplete, insecure, or poorly tested.

Before writing code:

1. Confirm that the requested change is actually required.
2. Inspect the affected user flow from the React frontend through the FastAPI API and PostgreSQL or Redis state where applicable.
3. Search the repository for an existing implementation or established pattern.
4. Reuse existing components, hooks, services, schemas, repositories, utilities, API clients, types, and configuration.
5. Prefer the language standard library and native platform features.
6. Prefer an already-installed dependency before proposing a new dependency.
7. Fix the underlying cause instead of applying several local patches.
8. Make the smallest change that fully satisfies the requirement.
9. Create a new abstraction only when repeated use or domain complexity clearly justifies it.
10. Preserve the project's existing architecture unless the requirement explicitly demands an architectural change.

---

## Repository inspection requirements

Before modifying code:

- Read this `AGENTS.md` file.
- Read the current `README.md`, `docs/HANDOFF.md`, relevant architecture or policy documents, and the applicable section of `YPGym_60_Day_Development_Plan_Revised_PostgreSQL (1).md`.
- Treat the root `handoff.md` as historical context where it differs from the newer `docs/HANDOFF.md`.
- Run `git status` and inspect current uncommitted changes.
- Review the affected existing implementation.
- Identify the exact requirement being addressed.
- Identify existing code that can be reused.
- Check whether the requested functionality may already be partially or fully implemented.
- Respect the documented Day 39+ boundaries; do not combine later features into the current task without explicit direction.

Never assume a feature is missing without searching the repository.

---

## Established architecture

- Frontend: React 19, Vite, TypeScript, Tailwind CSS, TanStack Query/Table, React Hook Form, and Zod under `frontend/`.
- Backend: FastAPI and async SQLAlchemy under `backend/app/`.
- Backend layering: API endpoint -> service -> repository -> SQLAlchemy model -> PostgreSQL.
- Database migrations: Alembic under `backend/alembic/versions/`.
- Short-lived state and caching: Redis. PostgreSQL remains the source of truth where documented.
- Background work: Celery worker and beat under `backend/app/workers/`.
- Optional scanner simulation: `iot-simulator/` using the device-authenticated API contract.
- Shared frontend code: `frontend/src/components/`, `frontend/src/hooks/`, `frontend/src/lib/`, and `frontend/src/types/`.
- Feature UI: `frontend/src/features/`; application routing and providers: `frontend/src/app/`.
- Backend reusable code: `backend/app/schemas/`, `services/`, `repositories/`, `core/`, and `utils/`.

Preserve these boundaries and conventions.

---

## Scope discipline

- Modify only files required for the current task.
- Avoid unrelated cleanup.
- Avoid renaming or moving files without a clear requirement.
- Avoid wrappers that only forward arguments.
- Avoid single-use utilities when clear local code is simpler.
- Avoid speculative interfaces, factories, managers, layers, or configuration.
- Avoid duplicating existing logic.
- Avoid placeholders, fake implementations, mock production behavior, and unfinished TODOs.
- Do not rewrite working code merely to make it stylistically different.
- Do not replace working architecture solely to reduce the number of lines.
- Preserve backward compatibility unless explicitly instructed otherwise.

When a requested change is already implemented, verify it and report the evidence instead of implementing it again.

---

## Dependency policy

Do not add a dependency until you have checked:

1. Whether the requirement can be solved with existing project code.
2. Whether the Python or JavaScript standard library can solve it.
3. Whether React, FastAPI, PostgreSQL, Redis, the browser, or another native platform feature can solve it.
4. Whether an already-installed package can solve it.

When adding a dependency is unavoidable:

- Explain why existing options are insufficient.
- Choose a maintained and appropriately scoped package.
- Avoid overlapping packages.
- Update the correct dependency and lock files.
- Document any configuration or operational impact.
- Run relevant security or dependency checks when available.

Never remove dependencies without confirming that they are unused across the entire repository.

---

## Frontend rules

- Follow the existing `frontend/src/` structure and feature/component conventions.
- Match the BRD Design Architecture, `docs/design/route-screen-map.md`, and existing YPGym visual system.
- Reuse `frontend/src/lib/apiClient.ts`, `AuthContext`, `ProtectedRoute`, TanStack Query patterns, shared components, form controls, layouts, types, and error handling.
- Preserve responsive behavior.
- Preserve accessibility, including labels, keyboard navigation, focus states, semantic HTML, and readable validation messages.
- Do not bypass backend authorization by relying only on hidden frontend controls.
- Do not duplicate server data unnecessarily in local state.
- Do not introduce a new state-management or styling system unless explicitly required.
- Keep loading, empty, error, disabled, and success states complete.
- Do not leave screens connected to mock data when a real API exists.

---

## Backend rules

- Follow the existing FastAPI endpoint, Pydantic schema, service, repository, dependency, exception, and response patterns.
- Reuse existing schemas, SQLAlchemy models, services, repositories, dependencies, and response formats.
- Keep endpoint functions focused; place domain logic in the established service layer and query logic in repositories.
- Preserve async database patterns.
- Do not silently change public API contracts.
- Do not expose internal exceptions or sensitive data.
- Maintain appropriate HTTP status codes and the existing error response shape.
- Validate all untrusted input.
- Enforce authorization on the backend for every protected action.
- Do not weaken device authentication, rate controls where present, JWT validation, password handling, or role checks.
- Avoid N+1 queries and unnecessary database calls.
- Use transactions for operations that must succeed or fail together, including their audit entries.

---

## Authentication and authorization

Security must never be reduced for minimalism.

Preserve and correctly enforce:

- OAuth2 bearer-token handling and signed JWT validation.
- JWT expiration behavior.
- Password hashing and verification.
- One-time, hashed email-verification and password-reset token behavior where applicable.
- Role-based access control for member, staff, manager, admin, and personal-trainer roles.
- Resource ownership checks.
- Protected React routes and protected FastAPI endpoints.
- Device ID and API-key checks for scanner endpoints.
- Sensitive-data filtering in API responses, audit records, and exports.
- Membership revocation and other access-denial rules.

Never trust role, user ID, price, membership status, device identity, or permission values supplied only by the frontend.

Never log passwords, access tokens, reset tokens, QR token material, device API keys, personal data, payment details, or secret values.

---

## Database and migration rules

- Reuse the existing SQLAlchemy models and repository patterns.
- Preserve foreign keys, unique constraints, indexes, and data integrity.
- Do not modify the database schema unless the requirement needs it.
- Use Alembic for schema changes.
- Never edit an already-applied migration unless the project explicitly permits it.
- Create reversible and clearly named migrations.
- Consider existing production-like data and the idempotent seed behavior.
- Avoid destructive migrations unless explicitly approved.
- Do not store derived values when they can safely be calculated, unless performance or historical accuracy requires storage.
- Keep membership, attendance, booking, billing, invoice, notification, audit, and role-related updates consistent.
- Keep PostgreSQL as the attendance source of truth; Redis projections must remain replaceable and reconcilable.

---

## YPGym domain safeguards

Treat these areas as high impact:

- Membership activation, expiration, freezing, cancellation, revocation, and renewal.
- Membership duration and pricing.
- Payment and immutable invoice generation.
- Attendance check-in, check-out, and manual closure.
- Occupancy calculation and attendance timeout.
- QR signing, rotation, expiration, supersession, and replay prevention.
- Class scheduling, overlap checks, capacity, duplicate booking prevention, and cancellation.
- Notifications, broadcasts, and expiry reminders.
- Administrator and manager actions and required audit records.
- Staff and personal-trainer access boundaries.
- Profile, export, and personal-data updates.
- Operational configuration validation and cache invalidation.

For these areas:

- Inspect the complete flow before editing.
- Preserve authorization, role, and ownership checks.
- Preserve transaction safety and audit consistency.
- Preserve idempotency where repeated requests or background jobs are possible.
- Test important success and failure paths.
- Do not simplify away domain rules.

---

## Testing and project commands

Use the existing commands relevant to the affected area. Do not invent a formatter, linter, or type-check command that the project does not define.

Backend and database verification normally run through Docker:

```powershell
docker compose config
docker compose exec -T backend-api alembic current
docker compose exec -T backend-api alembic check
docker compose exec -T backend-api pytest -q
```

Frontend commands run from `frontend/`:

```powershell
npm run dev
npm run lint
npm run build
```

`npm run build` includes TypeScript project compilation before the Vite production build. The frontend currently has no separate test or format script. The backend currently declares pytest but no separate repository-level lint, format, or static-type-check command.

Local services can be started using the documented Compose workflow:

```powershell
docker compose --profile app up -d --build
docker compose exec -T backend-api alembic upgrade head
docker compose exec -T backend-api python -m app.db.seed
```

The simulator's supported scenarios can be inspected from `iot-simulator/` with:

```powershell
python -m app.main --help
```

For every non-trivial change:

1. Identify the smallest meaningful existing test level.
2. Add or update tests for changed behavior.
3. Test the successful path.
4. Test relevant validation, permission, conflict, or failure paths.
5. Run the relevant existing tests.
6. Run linting and build/type-check commands for affected areas when available.

Do not claim a command passed unless it was actually executed successfully.

If a command cannot be executed:

- State the exact command.
- State why it could not run.
- State what remains unverified.
- Provide a manual verification procedure.

Do not delete or weaken tests simply to make the suite pass.

---

## Git safety

Before editing:

```powershell
git status
```

After editing:

```powershell
git diff --check
git diff --stat
git diff
```

Rules:

- Never run destructive Git commands without explicit approval.
- Never use `git reset --hard` or `git clean -fd`.
- Never discard, overwrite, stash, or amend user work without explicit approval.
- Never force-push.
- Keep changes narrowly scoped.
- Do not commit unless explicitly requested.
- Do not include secrets, environment files, local databases, generated invoices, build artifacts, caches, or generated dependency folders.

---

## Environment and secrets

- Do not expose or commit secrets.
- Do not print secret values from environment files.
- Use the existing Pydantic settings and Vite environment-variable patterns.
- Update example environment files only with placeholder values.
- Do not hard-code URLs, credentials, tokens, payment secrets, device keys, signing keys, or environment-specific configuration.
- Preserve Docker Compose and deployment compatibility.
- Do not make production deployment changes unless explicitly required.

---

## Required completion report

At the end of every implementation task, report:

### Requirement addressed

State the exact requirement completed.

### Existing implementation reused

List existing components, services, schemas, repositories, utilities, dependencies, or patterns that were reused.

### Files changed

List each changed file and its purpose.

### Dependencies

List any dependency added, removed, or updated. If none changed, state: `No dependencies changed.`

### Database impact

State whether models, migrations, constraints, or stored data were affected.

### Commands executed

List the exact commands that were run.

### Results

Report tests, type-checking, linting, builds, and other validation results accurately.

### Manual testing

Provide clear steps to test the change through the application.

### Risks and limitations

State remaining risks, assumptions, incomplete verification, or follow-up work.

### Suggested next task

Identify the next logical task, but do not implement it unless explicitly requested.

---

## Final decision principle

Choose the smallest solution that is:

- Correct.
- Complete.
- Secure.
- Tested.
- Accessible.
- Consistent with the existing architecture.
- Consistent with the documented design authority.
- Maintainable by the next developer.

When fewer lines would weaken any of these qualities, use the additional code required to preserve them.
