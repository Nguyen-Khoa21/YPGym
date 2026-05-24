# YPGym

YPGym is a full-stack gym management web application for membership management, attendance tracking, class booking, billing, CRM, personalization, and AI-assisted member support.

This repository follows the 60-day development plan in `YPGym_60_Day_Development_Plan.md`. The first milestone establishes a monorepo foundation with a React frontend, FastAPI backend, MongoDB, Redis, and documentation folders.

## Tech Stack

- Frontend: React, Vite, TypeScript, Tailwind CSS, shadcn/ui
- Backend: Python, FastAPI, MongoDB, Redis, JWT authentication
- Architecture: Monorepo with feature-based frontend and layered backend
- Local services: Docker Compose for MongoDB and Redis

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
|       |   |-- personalization/
|       |   |-- chatbot/
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
|   `-- database/
|-- docker-compose.yml
`-- README.md
```

## Run Locally

Prerequisites:

- Docker Desktop
- Git
- Node.js and Python will be needed from Days 3-4 onward

Create local environment files from the examples:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Start the Day 1-2 infrastructure services:

```powershell
docker compose up -d mongodb redis
```

Check service status:

```powershell
docker compose ps
```

Stop local services:

```powershell
docker compose down
```

The `backend` and `frontend` Compose services are included under the `app` profile for the later scaffolding days. After the FastAPI and Vite projects are created, the full stack can be started with:

```powershell
docker compose --profile app up --build
```

## Local Ports

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- MongoDB: `localhost:27018` by default for the Docker container
- Redis: `localhost:6379`

The MongoDB host port can be changed with `MONGODB_HOST_PORT` if needed. Inside Docker Compose, backend services should still use `mongodb://mongodb:27017/ypgym`.

## Development Rules

- Keep backend logic layered: API -> Service -> Repository -> Database.
- Keep frontend pages and components inside their feature folders.
- Use JWT and role checks for member/admin-only workflows.
- Log sensitive admin actions to audit logs once audit support is implemented.
