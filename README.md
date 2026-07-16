# YPGym

YPGym is a full-stack gym management application for membership management, attendance tracking, class booking, billing, CRM, mobile check-in flows, and operational dashboards.

This repository follows the revised PostgreSQL 60-day development plan in `YPGym_60_Day_Development_Plan_Revised_PostgreSQL (1).md`. Days 5-10 establish a PostgreSQL/FastAPI baseline, design-architecture route map, policy docs, diagrams, and shared error-state foundations. Days 11-20 add authentication, email verification, profile management, membership plans, mock purchases, invoices, and billing history.

## Tech Stack

- Frontend: React, Vite, TypeScript, Tailwind CSS, shadcn/ui
- Backend: Python, FastAPI, PostgreSQL, SQLAlchemy, Alembic, Redis, JWT authentication
- Architecture: Monorepo with feature-based frontend and layered backend
- Local services: Docker Compose for PostgreSQL, Redis, backend, frontend and worker services

## Current Web Routes

The frontend now uses canonical application routes while preserving the Day 11-20 links:

- Member dashboard: `/app/dashboard` (`/member` redirects here)
- Profile: `/app/profile` (`/profile` redirects here)
- Billing: `/app/billing` (`/billing` redirects here)
- PT dashboard: `/pt/dashboard` (`/pt` redirects here)
- Membership policies: `/policies/membership`
- Future member routes: `/app/qr` and `/app/classes` are explicit planned states, not mocked features.
- Future admin routes such as `/admin/members` and `/admin/attendance` use the shared admin shell but remain intentionally unconnected until their APIs are built.

All protected routes wait for authentication resolution before rendering private content. A blocked role is sent to `/permission-denied`.

## Folder Structure

```text
ypgym/
|-- frontend/
|   `-- src/
|       |-- app/
|       |-- components/
|       |-- features/
|       |   |-- auth/
|       |   |-- member/
|       |   |-- memberships/
|       |   |-- attendance/
|       |   |-- classes/
|       |   |-- billing/
|       |   `-- admin/
|       |-- hooks/
|       |-- lib/
|       `-- types/
|-- backend/
|   `-- app/
|       |-- api/v1/endpoints/
|       |-- core/
|       |-- db/
|       |-- models/
|       |-- schemas/
|       |-- repositories/
|       |-- services/
|       |-- workers/
|       |-- utils/
|       `-- tests/
|-- docs/
|   |-- architecture/
|   |-- api/
|   |-- database/
|   |-- design/
|   |-- diagrams/
|   |-- policies/
|   `-- demo/
|-- docker-compose.yml
`-- README.md
```

## Run Locally

Prerequisites:

- Docker Desktop
- Git
- Node.js
- Python 3.13 or another modern Python 3 version

Create local environment files from the examples:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Start the Day 5-10 infrastructure services:

```powershell
docker compose up -d postgres-db redis-cache
```

Run the backend locally:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

Run the frontend locally in another terminal:

```powershell
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5174
```

Check service status:

```powershell
docker compose ps
```

Stop local services:

```powershell
docker compose down
```

Run database migrations from the backend folder after PostgreSQL is running:

```powershell
cd backend
alembic upgrade head
```

Seed default membership plans and system configuration values:

```powershell
cd backend
python -m app.db.seed
```

Inside Docker Compose, run the same seed command through the backend service:

```powershell
docker compose --profile app exec backend-api python -m app.db.seed
```

The full stack can also be started through the `app` Compose profile:

```powershell
docker compose --profile app up -d --build
```

## Local Ports

- Frontend: `http://localhost:5174`
- Backend API: `http://localhost:8001`
- Backend Swagger: `http://localhost:8001/docs`
- Health Check: `http://localhost:8001/api/v1/health`
- PostgreSQL: `localhost:5433` by default for the Docker container
- Redis: `localhost:6380` by default for the Docker container

The PostgreSQL host port can be changed with `POSTGRES_HOST_PORT` if needed. The Redis host port can be changed with `REDIS_HOST_PORT`. The backend and frontend host ports can be changed with `BACKEND_HOST_PORT` and `FRONTEND_HOST_PORT`. Inside Docker Compose, backend services should use the `postgres-db` and `redis-cache` service names.

## Development Rules

- Keep backend logic layered: API -> Service -> Repository -> Database.
- Keep frontend pages and components inside their feature folders.
- Use JWT and role checks for member/admin-only workflows.
- Log sensitive admin actions to audit logs once audit support is implemented.
- Use `docs/design/route-screen-map.md` and the updated BRD Design Architecture section as the UI source of truth.
- Keep AI chatbot, personalization, and recommendations as post-60-day backlog unless the lecturer restores them to required scope.
