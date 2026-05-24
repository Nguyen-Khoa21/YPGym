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
- Node.js
- Python 3.13 or another modern Python 3 version

Create local environment files from the examples:

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item frontend/.env.example frontend/.env
```

Start the Day 1-2 infrastructure services:

```powershell
docker compose up -d mongodb redis
```

Run the backend locally:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run the frontend locally in another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Check service status:

```powershell
docker compose ps
```

Stop local services:

```powershell
docker compose down
```

The full stack can also be started through the `app` Compose profile:

```powershell
docker compose --profile app up --build
```

## Local Ports

- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Backend Swagger: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/api/v1/health`
- MongoDB: `localhost:27018` by default for the Docker container
- Redis: `localhost:6379`

The MongoDB host port can be changed with `MONGODB_HOST_PORT` if needed. Inside Docker Compose, backend services should still use `mongodb://mongodb:27017/ypgym`.

## Development Rules

- Keep backend logic layered: API -> Service -> Repository -> Database.
- Keep frontend pages and components inside their feature folders.
- Use JWT and role checks for member/admin-only workflows.
- Log sensitive admin actions to audit logs once audit support is implemented.
