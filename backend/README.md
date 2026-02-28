# LinkDem Backend

Production-quality FastAPI backend for LinkDem – a prescriptive event/task management platform for small teams.

## Project Structure

```
backend/
├── app/
│   ├── core/           # Config, DB, Security, Deps
│   ├── models/         # SQLAlchemy ORM models
│   ├── schemas/        # Pydantic v2 DTOs
│   ├── crud/           # DB query primitives (no business logic)
│   ├── services/       # Business logic + RBAC + workflow orchestration
│   ├── routes/         # FastAPI router definitions (thin)
│   └── scripts/        # Seed script
├── alembic/            # Migrations
│   └── versions/
│       └── 0001_initial_schema.py
├── alembic.ini
├── requirements.txt
├── .env                # Fill in before running!
└── run.py
```

## Setup

### 1. Fill in credentials

Edit `backend/.env` with your real Supabase values.

### 2. Install dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Run Alembic migrations

```bash
cd backend
alembic upgrade head
```

### 4. Seed sample data

```bash
cd backend
python -m app.scripts.seed
```

### 5. Start the server

```bash
cd backend
python run.py
# or
uvicorn app.main:app --port 4000 --reload
```

### 6. Open Swagger UI

Visit: http://localhost:4000/docs

## API Endpoints

| Method | Path                       | Description                              |
| ------ | -------------------------- | ---------------------------------------- |
| POST   | /api/auth/login            | Authenticate (no auth required)          |
| GET    | /api/users                 | List users                               |
| GET    | /api/events                | List events                              |
| POST   | /api/events                | Create event                             |
| GET    | /api/tasks                 | List tasks (filter: eventId, assigneeId) |
| POST   | /api/tasks/{id}/transition | Transition task state                    |
| GET    | /api/audit/{eventId}       | Event audit timeline                     |
| GET    | /docs                      | Swagger UI                               |
| GET    | /health                    | Health check                             |

## Architecture

- **`/routes`** – Thin orchestration only; no business logic
- **`/services`** – RBAC checks + workflow DAG validation + atomic transactions
- **`/crud`** – Query primitives with eager loading; no N+1 queries
- **`/schemas`** – Pydantic v2 DTOs matching OpenAPI spec verbatim
- **`/models`** – SQLAlchemy ORM mirroring DB tables

## Key Design Decisions

- **Service-role DB connection** bypasses Supabase RLS; all RBAC enforced in Python
- **JWT validation** uses Supabase JWKS endpoint (RS256)
- **Atomic transitions**: state update + remark + audit + auto-task creation in single transaction
- **Task locking** via `app_acquire_task_lock()` DB function prevents race conditions
- **Auto-created tasks** triggered from `workflow_transitions.auto_create_tasks` JSONB on state change
- **OpenAPI verbatim**: `/openapi.json` serves the exact `docs/openapi.json` provided
