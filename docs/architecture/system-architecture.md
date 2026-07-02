# YPGym System Architecture

## Purpose

This document captures the Day 7 architecture baseline for the PostgreSQL revision. It supports the BRD and the Design Architecture section by describing how the web app, mobile app, API, database, Redis cache, workers and IoT scanner integration fit together.

## Service Boundaries

| Service | Responsibility |
|---|---|
| `frontend-web` | React web app for public pages, member self-service, staff/admin CRM and manager dashboards. |
| `mobile` | Expo app planned later for member dashboard, renewal, QR check-in, class booking and profile flows. |
| `backend-api` | FastAPI application exposing versioned APIs and enforcing validation, permissions and business rules. |
| `postgres-db` | Permanent system of record for users, memberships, payments, invoices, attendance, classes and audit logs. |
| `redis-cache` | Short-lived QR token state, occupancy cache, rate limits and frequently read operational settings. |
| `celery-worker` | Background jobs for email, invoice generation, reminders and attendance timeout reconciliation. |
| `celery-beat` | Scheduled trigger service for recurring jobs. |
| `iot-simulator` | Optional local scanner simulator that calls the same attendance API future hardware will use. |

## Backend Layering

```text
API endpoint -> Service -> Repository -> SQLAlchemy model -> PostgreSQL
```

Routes should stay thin. Business rules belong in services. Repositories should own query shape and persistence details. Permanent records go to PostgreSQL; temporary or frequently recalculated values go to Redis.

## Design Architecture Source

The implementation source of truth for UI routes is:

- `FYP Brief BRD - Anh Khoa - Design Architecture.docx`
- `docs/design/route-screen-map.md`

Each screen should be implemented against the route map before it is considered done.

