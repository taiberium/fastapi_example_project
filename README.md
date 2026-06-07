# FastAPI Example Project

A small but **production-shaped** FastAPI application. The point of this repo is not the feature set
(one `Person` entity) — it's the **architecture**: strict layering, a generic CRUD repository, schema/entity
separation, centralized config & logging, and Alembic migrations.

> The "why" behind every directory is documented below. For the rules an editor/agent must follow when
> changing code, see [`CLAUDE.md`](./CLAUDE.md).

---

## Why this structure

The whole codebase is organized around **one idea: dependencies only ever point downward**.

```
            ┌─────────────┐
 outside →  │  api/routes │   HTTP — request/response DTOs, maps schema ↔ entity
            └──────┬──────┘
                   ▼
            ┌─────────────┐
            │   service   │   business logic — works on entities, holds the Session
            └──────┬──────┘
                   ▼
            ┌─────────────┐
            │ repository  │   data access — SQLAlchemy queries, generic CRUD
            └──────┬──────┘
                   ▼
            ┌─────────────┐
            │     db      │   engine, Session, Base, get_db
            └─────────────┘
```

A higher layer may call the one below it; a lower layer never imports a higher one. This is what keeps the
business logic testable and the persistence swappable.

---

## What lives where (and why)

```
app/
  api/                     # the "incoming world" — everything HTTP
    dependencies.py        #   shared FastAPI deps: pagination, service providers (Depends(get_db))
    routes/                #   one router file per entity; the ONLY place schema ↔ entity mapping happens
      person.py
  service/                 # business logic; operates on ENTITIES only — schemas never reach here
    person_service.py
  entities/                # SQLAlchemy ORM models — the shared domain. Top-level because BOTH
    person.py              #   service and repository use them (can't hide inside persistence/)
  schemas/                 # Pydantic DTOs (PersonCreate, PersonRead). Imported by routes ONLY
    person.py
  persistence/             # the storage layer, grouped under one parent
    db/
      base_class.py        #   Base (DeclarativeBase) — kept alone to avoid circular imports
      session.py           #   engine, SessionLocal, get_engine builder
      db.py                #   get_db() — the single session dependency (open → yield → close)
    repository/
      base.py              #   generic CRUDRepository[ORMModel]: holds the Session, built per request
      person_repository.py #   class PersonRepository(CRUDRepository[Person])
  core/                  # infrastructure bucket: settings VALUES + cross-cutting BEHAVIOR
    settings.py            #   the values: pydantic-settings BaseSettings (env-driven)
    security.py            #   JWT issue/decode + Google ID-token verification
    exceptions.py          #   HTTPException helpers + app exceptions
    logging.py             #   configure_logging() + get_logger()
  server.py                # uvicorn runner (host/port/reload from settings)
  main.py                  # create_app() factory: configures logging, mounts routers
main.py                    # entrypoint → delegates to app.server.run()
alembic/                   # database migrations (schema is owned here, not by the app)
  env.py                   #   wired to app settings.database_url + Base.metadata
  versions/                #   one migration file per schema change
alembic.ini
tests/                     # pytest; conftest overrides get_db with an in-memory SQLite
```

### Key design decisions

| Decision | Why |
|---|---|
| **`entities/` and `schemas/` are top-level**, not inside `persistence/` | `service` uses entities and `routes` use schemas — burying them in `persistence/` would force higher layers to reach into a lower package's internals. |
| **Schema ↔ entity mapping only in the route** | The route is the adapter between the outer world (DTOs) and the domain (entities). `service`/`repository` stay free of Pydantic, so persistence is decoupled from the web contract. |
| **Generic `CRUDRepository[ORMModel]`** | Near-zero boilerplate per entity: a thin `class XRepository(CRUDRepository[X])` binds the model. The repository **holds the Session** and is built per request, so the Session stays a persistence detail — the service holds a repository and never sees SQLAlchemy. |
| **`core/` is the infrastructure bucket** | "config" in the broad sense — settings *values* plus cross-cutting *behavior* (security, exceptions, logging). Inside it, keep `settings.py` (values) separate from behavior modules. Domain/business/data/routes do NOT belong here. DB engine/session stays in `persistence/db/`; request DI stays in `api/dependencies.py`. |
| **Schema owned by Alembic, not `create_all()`** | `Base.metadata.create_all()` only creates missing tables — it silently ignores column changes. Alembic gives versioned, reversible, auditable migrations. |
| **Centralized logging** | One `configure_logging()` at startup; every module uses `get_logger(__name__)` instead of `print`. |

---

## Requirements

- Python ^3.11
- [Poetry](https://python-poetry.org/)

## Setup

```bash
poetry install
poetry run pre-commit install   # enable lint/format/type hooks on commit
```

## Code quality

`ruff` (lint + format), `mypy` (types), and `pre-commit` (runs them on every commit):

```bash
poetry run ruff check --fix .     # lint + autofix
poetry run ruff format .          # format (replaces black)
poetry run mypy app               # type-check
poetry run pre-commit run --all-files
```

## Database migrations (Alembic)

The application **does not** create tables on startup. The schema is managed by Alembic.

```bash
# apply all migrations (creates the schema)
poetry run alembic upgrade head

# after changing/adding an ORM model in app/entities/, generate a migration
poetry run alembic revision --autogenerate -m "describe the change"
poetry run alembic upgrade head

# roll back the last migration
poetry run alembic downgrade -1
```

`alembic/env.py` reads the URL from `app.core.settings` and targets `Base.metadata`, so there is a single
source of truth — no DB URL duplicated in `alembic.ini`. When you add a new entity, import it in `env.py` so its
table is registered for autogenerate.

## Run

```bash
poetry run alembic upgrade head        # first time / after pulling new migrations
poetry run uvicorn app.main:app --reload
# or
poetry run python main.py
```

Interactive API docs: http://localhost:8000/docs · liveness: `GET /health` → `{"status":"ok"}` ·
Prometheus metrics: `GET /metrics` (request rate/errors/latency per handler)

### Example requests

```bash
curl -X POST localhost:8000/persons \
  -H 'Content-Type: application/json' \
  -d '{"name": "Alice", "age": 25, "email": "alice@example.com"}'

curl "localhost:8000/persons?age=30&skip=0&limit=10"
```

## Authentication (Google OAuth2)

Auth uses **Google Sign-In → app JWT session** (no passwords):

1. The frontend renders a Google Sign-In button and obtains a Google **ID token**.
2. `POST /auth/google` with `{"id_token": "<google id token>"}`. The backend verifies it against
   `APP_GOOGLE_CLIENT_ID`, provisions a `User` on first sign-in, and returns an app JWT:
   ```json
   { "access_token": "<jwt>", "token_type": "bearer" }
   ```
3. Call protected endpoints with `Authorization: Bearer <jwt>`, e.g. `GET /auth/me`.

`app/core/security.py` holds the crypto (JWT issue/decode via `python-jose`, Google verification via `google-auth`).
The `get_current_user → get_current_active_user → get_current_superuser` dependency chain in
`app/api/dependencies.py` protects routes.

## Test

```bash
poetry run pytest -q
```

Tests build their own in-memory SQLite and override `get_db`, so they run without touching a real database or
requiring migrations.

## Configuration

Settings come from `app/core/settings.py` (pydantic-settings). Override via `APP_`-prefixed env vars or a
`.env` file:

| Setting         | Env var             | Default                    |
|-----------------|---------------------|----------------------------|
| `database_url`  | `APP_DATABASE_URL`  | `sqlite:///mydatabase.db`  |
| `app_title`     | `APP_APP_TITLE`     | `Fast API Example App`     |
| `log_level`     | `APP_LOG_LEVEL`     | `INFO`                     |
| `env`           | `APP_ENV`           | `dev` (enables reload)     |
| `server_host`   | `APP_SERVER_HOST`   | `0.0.0.0`                  |
| `server_port`   | `APP_SERVER_PORT`   | `8000`                     |
| `cors_origins`  | `APP_CORS_ORIGINS`  | localhost:5173 / :3000     |
| `google_client_id` | `APP_GOOGLE_CLIENT_ID` | `""` (set in prod)    |
| `secret_key`    | `APP_SECRET_KEY`    | dev placeholder — **override in prod** |
| `algorithm`     | `APP_ALGORITHM`     | `HS256`                    |
| `access_token_expire_minutes` | `APP_ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` |

The runnable entrypoint is `app/server.py` (`run()` reads host/port/env from settings); root `main.py`
delegates to it, so `python main.py` and `python -m app.server` both work.

## Adding a new entity (the recipe)

1. `app/entities/<x>.py` — the ORM model.
2. `app/schemas/<x>.py` — `XCreate`, `XRead` (add `XUpdate` only when there's an update endpoint).
3. `app/persistence/repository/<x>_repository.py` — `class XRepository(CRUDRepository[X])` binding the model.
4. `app/service/<x>_service.py` — business logic; takes the repository; methods take/return entities.
5. `app/api/dependencies.py` — add `get_<x>_repository(db)` and `get_<x>_service(repo)`.
6. `app/api/routes/<x>.py` — the router; map `XCreate → entity` and `entity → XRead` here; include it in `main.py`.
7. Import the entity in `alembic/env.py`, then `alembic revision --autogenerate` + `upgrade head`.
8. `tests/test_<x>_api.py` — write the tests first (TDD).
