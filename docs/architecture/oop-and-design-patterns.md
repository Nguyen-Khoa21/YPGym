# YPGym OOP and Design Patterns

## Scope and architectural position

YPGym's MVP means its **Minimum Viable Product**: the smallest complete gym-management release that supports the required member, staff, manager, administrator, personal-trainer, billing, attendance, notification, and optional scanner journeys.

The project uses a layered, Clean Architecture-inspired structure. Backend dependencies flow from FastAPI endpoints through services and repositories to SQLAlchemy models and PostgreSQL. The React and Expo clients use feature modules, shared API adapters, contexts, hooks, and reusable presentation components. YPGym does not claim a strict textbook Clean Architecture implementation and does not rewrite the frontend into MVC, because the current feature-based React structure already separates view, state, and API concerns without adding duplicate controller classes.

## Object-oriented principles

### Encapsulation

Encapsulation keeps state and the operations that protect it together behind a stable public interface.

Current evidence includes:

- `VNPaySigner` in `backend/app/services/vnpay_service.py`, which owns payment signing and verification rules instead of exposing secret-handling details to endpoints.
- `MembershipLifecycleService` in `backend/app/services/lifecycle_service.py` and `UserMembershipRepository` in `backend/app/repositories/membership_repository.py`, which keep domain transitions and database operations out of route handlers.
- React `AuthContext` in `frontend/src/features/auth/AuthContext.tsx`, which owns session state and exposes authenticated actions to the component tree.

This reduces accidental misuse of security-sensitive and transactional behavior. The limit is intentional: simple, stateless transformations remain plain functions because wrapping them in classes would not improve safety.

### Abstraction

Abstraction exposes the capability callers need while hiding implementation details.

Current evidence includes:

- `EmailTransport` in `backend/app/services/email_service.py`, which describes mail delivery without coupling callers to SMTP.
- `PaymentRepository` in `backend/app/repositories/billing_repository.py`, which gives payment services domain-focused persistence operations rather than raw SQL construction.
- Pydantic request and response schemas under `backend/app/schemas/`, which define the supported API contract independently of ORM internals.
- Web and mobile `apiRequest` functions in `frontend/src/lib/apiClient.ts` and `mobile/src/lib/api.ts`, which hide headers, JSON parsing, backend error translation, and network-error handling.

These boundaries make implementations replaceable and keep HTTP, storage, and provider details from spreading across features. They are kept close to real variation points; YPGym avoids interfaces with only speculative future value.

### Inheritance

Inheritance is used where a shared runtime contract already exists.

Current evidence includes:

- `AppError` subclasses in `backend/app/core/exceptions.py`, which share safe error metadata and FastAPI translation behavior.
- SQLAlchemy's declarative `Base` in `backend/app/db/base.py` and shared `TimestampMixin` in `backend/app/models/mixins.py`.
- Pydantic `BaseModel` used by API schemas.
- The React `AppErrorBoundary` in `frontend/src/app/AppErrorBoundary.ts`, which extends `Component` because React's render error-boundary contract requires the class lifecycle API.

The benefit is consistent framework integration and error behavior. YPGym avoids deep domain class hierarchies; composition is preferred when objects only need to collaborate.

### Polymorphism

Polymorphism lets callers use one contract with different valid implementations.

Current evidence includes:

- `EmailDeliveryService` in `backend/app/services/email_service.py` accepting an `EmailTransport`, allowing configured SMTP delivery and test transports to be used through the same methods.
- FastAPI dependencies in `backend/app/core/dependencies.py` supplying authenticated users and database sessions to endpoints through declared contracts.
- React components receiving typed props and callbacks, allowing reusable controls and layouts to serve multiple feature views.

This improves testability and permits provider or presentation changes without rewriting callers. New implementations still have to preserve authorization, validation, and response contracts.

## Named design patterns

### Repository pattern

**Definition:** a repository provides domain-oriented access to persistent data and hides query construction from business logic.

**YPGym use:** repositories under `backend/app/repositories/` own SQLAlchemy queries, locking, pagination, aggregation, and persistence helpers. Concrete examples are `PaymentRepository` in `billing_repository.py` and `AttendanceRepository` in `attendance_repository.py`.

**Benefit:** services can express business rules without duplicating database mechanics, and query behavior can be tested at its proper boundary.

**Limit:** repositories do not make authorization or lifecycle decisions; those remain in dependencies and services.

### Service Layer pattern

**Definition:** a service layer coordinates domain rules and transaction-level operations for an application use case.

**YPGym use:** services under `backend/app/services/` coordinate membership, attendance, booking, payment, notification, OAuth, training, and administrative workflows. Examples include `BookingService` in `class_service.py` and `VNPayPaymentService` in `payment_service.py`.

**Benefit:** endpoints stay focused on HTTP concerns while high-impact state changes, audits, and related writes are kept together.

**Limit:** trivial read-only endpoint shaping may remain local when moving it would only create a forwarding wrapper.

### Dependency Injection pattern

**Definition:** dependencies are supplied to a consumer instead of constructed throughout its business logic.

**YPGym use:** `backend/app/core/dependencies.py` provides authenticated principals and role checks, while `backend/app/db/session.py` provides database sessions. Tests replace these boundaries with controlled inputs.

**Benefit:** security and lifecycle wiring is consistent, and tests can isolate provider or persistence behavior.

**Limit:** dependency injection does not weaken backend authorization; every protected action still verifies identity, role, and ownership at the API boundary.

### Strategy pattern

**Definition:** interchangeable implementations perform the same capability through a common contract.

**YPGym use:** `EmailTransport`, `ConfiguredEmailTransport`, and `EmailDeliveryService` in `backend/app/services/email_service.py` let configured SMTP delivery and test implementations follow the same sending contract.

**Benefit:** registration, billing, and notification flows do not depend directly on SMTP mechanics and can be tested without sending mail.

**Limit:** strategies are introduced for demonstrated variation only; each third-party integration does not automatically receive a new interface hierarchy.

### Adapter pattern

**Definition:** an adapter translates an external or framework-specific interface into the application's internal contract.

**YPGym use:** `ConfiguredEmailTransport` in `backend/app/services/email_service.py` adapts SMTP to `EmailTransport`; `OAuthService` in `backend/app/services/oauth_service.py` translates Google and Facebook profile responses into the `ExternalIdentity` model in `backend/app/models/identity.py`; web and mobile API clients translate HTTP responses into typed application errors.

**Benefit:** provider-specific payloads and failure formats remain at integration boundaries.

**Limit:** adapters validate and translate provider data but do not bypass account-linking, email-verification, or authorization policy.

### Exception Translation pattern

**Definition:** low-level or domain failures are converted at a boundary into a stable, safe error contract.

**YPGym use:** handlers in `backend/app/core/exceptions.py` translate `AppError` subclasses and validation failures into `{ error: { code, message, details } }`; `frontend/src/lib/apiClient.ts`, `frontend/src/lib/apiErrors.ts`, and `mobile/src/lib/api.ts` convert HTTP failures into typed `ApiError` instances that preserve status, safe details, and request IDs.

**Benefit:** every client receives predictable errors without leaking stack traces, submitted secrets, raw provider responses, or database exceptions.

**Limit:** unexpected failures deliberately return a generic message. Detailed diagnosis belongs in protected server logs and request correlation, not the user response.

### Outbox and Retry pattern

**Definition:** durable work is recorded with application state and retried asynchronously until it succeeds or reaches a controlled failure state.

**YPGym use:** `EmailDelivery` in `backend/app/models/email_delivery.py` and `EmailDeliveryRepository` in `backend/app/repositories/email_delivery_repository.py` persist delivery work. `EmailDeliveryService` in `backend/app/services/email_service.py` applies retry state, and `send_membership_emails` in `backend/app/workers/celery_app.py` processes pending work outside the user's request.

**Benefit:** temporary SMTP or worker failures do not corrupt the primary registration, billing, or notification transaction and can be inspected operationally.

**Limit:** asynchronous delivery can be delayed, so the UI reports the accepted application action rather than claiming that an external mailbox already received the message.

## Composition preference

YPGym generally composes endpoints, services, repositories, transports, and utilities instead of building deep inheritance trees. Inheritance remains limited to framework contracts and closely related error types. This keeps the implementation easier to trace and allows each boundary to be tested independently.

## Finite State Machine / State Transition Table pattern

YPGym centralizes permitted membership, payment, class, booking, waitlist, attendance, approval, and refund changes in `backend/app/services/state_transitions.py`. Small domain functions validate each mutation before services apply their existing transactional side effects. The complete inventory and legacy-payment compatibility decision are documented in [`state-transitions.md`](state-transitions.md).

The implementation deliberately avoids a class-per-state hierarchy. State behavior remains small enough for explicit tables, while the established services continue to own row locks, audits, notifications, capacity changes, invoices, and outbox work.
