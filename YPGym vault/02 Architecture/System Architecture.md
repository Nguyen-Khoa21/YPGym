---
type: architecture
status: current
date: 2026-11-10
tags:
  - architecture
related:
  - "[[Home]]"
  - "[[Decisions Log]]"
  - "[[Packages 01-04 Summary]]"
---

# System architecture

Short map of YPGym. The full documents live in the repo: `docs/architecture/system-architecture.md`, `docs/architecture/multigym-flows.md`, `docs/architecture/state-transitions.md`. See also the visual version in [[YPGym Architecture.canvas]] and the business-flow diagrams in [[Archify Diagrams]].

## Stack

- Web: React 19, Vite, TypeScript, Tailwind CSS, TanStack Query and Table, React Hook Form, Zod (`frontend/`).
- Backend: FastAPI with async SQLAlchemy (`backend/app/`). Migrations with Alembic (`backend/alembic/versions/`).
- Data: PostgreSQL is the source of truth. Redis is a cache and message transport only.
- Background work: Celery worker and beat (`backend/app/workers/`).
- Other apps: member mobile app (`mobile/`), scanner app (`scanner-mobile/`), optional IoT simulator (`iot-simulator/`).

## Layering

Endpoint, then service, then repository, then SQLAlchemy model, then PostgreSQL. Do not skip layers.

## Rules that do not change

- Backend authorization decides access. Hiding a control in React is not security.
- Branch (gym) selection is never an authorization mechanism.
- Reuse existing components, hooks and services before adding new ones. Add no dependency unless the installed ones cannot do the job.
- Multi-gym: every gym has its own manager, staff and PT accounts; only the owner (`admin`) is cross-gym ([[Decisions Log]], D-15).

## Where to read more

- Packages and their status: [[Packages 01-04 Summary]] and the notes in `03 Specs`.
- Routes and screens: `docs/design/route-screen-map.md`.
- Database: `docs/database/erd.md`, `docs/database/multigym-migrations.md`.
- API notes: `docs/api/`.
