# YPGym System Architecture

## Runtime topology through Day 49 (web and native member clients)

| Service | Responsibility |
|---|---|
| `frontend-web` | React web application for public, member, staff, manager, admin, and limited PT routes, with PWA metadata. |
| `mobile` | Expo SDK57 member client using the same versioned FastAPI contracts and secure native token storage. |
| `backend-api` | Versioned FastAPI endpoints, authentication, RBAC, request validation, and orchestration. |
| `postgres-db` | Source of truth for identity, membership, billing, notifications, audit, attendance, trainers, classes, bookings, and waitlists. |
| `redis-cache` | Rotating QR JTI state, duplicate-scan guards, 30-second occupancy snapshot, configuration and 60-second analytics cache, sensitive-endpoint rate limits, and Celery transport. |
| `celery-worker` | Membership-status synchronization, 7/3/1-day reminders, and attendance timeout closure. |
| `celery-beat` | Recurring task schedule. |
| `iot-simulator` | Optional scanner client using the same device-authenticated HTTP contract as future hardware. |

```text
Web client --------------------------> FastAPI API
Scanner/simulator -- device API key -> Attendance API
FastAPI -> service -> repository ----> PostgreSQL
                 |-------------------> Redis
Celery Beat -> Celery Worker --------> PostgreSQL + Redis
Billing service ---------------------> immutable invoice PDF files
Manager analytics -------------------> PostgreSQL aggregates -> bounded Redis response cache
```

## Layering and transaction boundaries

Backend feature code follows:

```text
API endpoint -> Service -> Repository -> SQLAlchemy model -> PostgreSQL
```

- Endpoints own HTTP parsing, dependencies, and role gates.
- Services own lifecycle transitions, validation, audit creation, and transaction commit/rollback.
- Repositories own query shape, locks, pagination, aggregation, and persistence helpers.
- Sensitive decisions, manual attendance closure, class changes, configuration changes, broadcasts, and personal-data exports write audit records in the same transaction as their business change.

## Source-of-truth rules

- PostgreSQL active attendance sessions are the occupancy source of truth.
- Redis occupancy is a replaceable 30-second projection and is force-reconciled after check-in, check-out, timeout, or manual close.
- QR tokens are signed JWTs, while current JTI state is stored in Redis with a configurable TTL. Issuing a new token supersedes the previous JTI.
- Configuration values are persisted in PostgreSQL, validated centrally, cached for five minutes, and invalidated after an audited update.
- Manager analytics are computed from persisted membership, class, attendance, and successful payment rows. The summary range is capped at 366 days and its Redis response cache is capped at 60 seconds.
- Login, password-reset requests, and scanner mutations use Redis fixed-window limits and fail closed if abuse protection is unavailable.
- Billing invoices are immutable database metadata linked one-to-one to payments; PDFs are generated artifacts referenced by the invoice row.

## Access boundaries

- Members: own lifecycle requests, preferences, notifications, QR, attendance, billing, and broadcasts.
- Staff: attendance history and reasoned manual closure only.
- Managers: attendance analytics, limited membership approval queue, broadcasts, audit, and configuration.
- Admins: manager capabilities plus full CRM, billing/export, revocation, and class administration.
- PT role: current limited dashboard; full profile/assignment work begins Day 39.

See `docs/policies/roles.md` for the endpoint/route matrix and `docs/api/iot-scanner.md` for the device boundary.
See `docs/policies/security.md` for sensitive endpoint limits and `docs/release/viva-notes.md` for release explanations of source-of-truth boundaries.

## UI authority

The recovery used the BRD Design Architecture document, its embedded reference screenshots, `docs/design/route-screen-map.md`, and the repository design system as visual authority. No additional Figma file was available. Day42 web evidence and the Day47 Android evidence index record the responsive and native checks; full WCAG, physical-phone and iOS validation remain outside the recorded scope.
