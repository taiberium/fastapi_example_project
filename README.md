# FastAPI Architecture — Light Hexagonal × Layered

**A production-shaped FastAPI blueprint that fuses _light hexagonal_ (ports & adapters) with _classic
layering_ — giving you the swappability and testability of hexagonal without the ceremony tax.**

One `Person` entity is the excuse; the **architecture** is the product. Copy this skeleton and ship features,
not plumbing.

> Rules an editor/agent must follow when changing code live in [`CLAUDE.md`](./CLAUDE.md).

---

## Why you'll want this

- **Three transports, one core.** HTTP, WebSocket, and Celery all funnel through the **same services** with the
  **same dependency injection**. Add gRPC, SSE, or a CLI tomorrow — your business logic doesn't move a line.
- **Swap any edge without touching the core.** Postgres → MySQL, Celery → RabbitMQ, WebSocket → SSE: change one
  *adapter*, and the service never finds out. That's the whole promise of ports & adapters, delivered.
- **One DI mechanism, everywhere.** You already know FastAPI's `Depends`. We **reuse FastAPI's own resolver**
  inside Celery workers and WebSocket handlers — no second DI framework, no hand-wiring, no surprises.
- **The service is the single source of truth for I/O.** Strictly top-down: **Input → Service → Output**. You
  always know where logic lives and where data goes.
- **Light, not dogmatic.** Full hexagonal drowns small apps in ports and mappers. This keeps the wins
  (decoupling, testability, multi-transport) with layered pragmatism — so juniors stay productive and seniors
  stay happy.
- **Production-shaped out of the box.** Hardened DB connection pool, Alembic migrations, Prometheus metrics,
  OpenTelemetry export, Google-OAuth2 + JWT, Celery retries & fork-safe engine disposal, strict typing & lint.

---

## The one rule: `Input → Service → Output`

Dependencies only ever point **inward, toward the service**. Adapters are dumb; the service orchestrates
everything — including **every outbound send**.

```
   INBOUND (driving)              CORE                 OUTBOUND (driven)
   how the world calls us                              how we call the world

   http/      (FastAPI) ─┐                       ┌─ persistence/  (SQLModel + repos)
   websocket/ (WS)       ├──►   service/   ──────┤─ queue/        (Celery jobs)
   celery/    (worker)  ─┘   business logic      └─ channel/      (push to clients)
```

- **Inbound** adapters only *receive* and call a service method. They never touch a repository, a queue, or a
  socket directly.
- The **service** holds the business logic and **invokes every output** — it writes via repositories, enqueues
  jobs via the `JobQueue` port, pushes messages via the `MessageChannel` port.
- **Outbound** adapters are named by *role* (`persistence`, `queue`, `channel`) with the concrete tech hidden
  inside — so they're swappable behind a port.

Inbound is named by **transport** (concrete entrypoints); outbound is named by **role** (abstractions the
service depends on). That asymmetry is deliberate — it's what makes the edges replaceable.

---

## What lives where

```
app/
  inbound/                 # driving adapters — the world calls in (by transport)
    http/
      routes/              #   one router per entity; the ONLY place schema ↔ entity mapping happens
      guards.py            #   auth guards (CurrentUser → CurrentActiveUser → CurrentSuperuser)
    websocket/
      person_ws.py         #   WS endpoint — same Depends(Service) DI as HTTP
    celery/
      base.py              #   @inject — resolve a task's Annotated[…, Depends(…)] deps, FastAPI-style
      person_tasks.py      #   @celery_app.task definitions the worker runs
  service/                 # the business core — transport-agnostic; drives ALL output
    person_service.py
    auth_service.py
  outbound/                # driven adapters — we call out (by role/port)
    persistence/
      db/                  #   engine + SessionLocal + get_db + session_scope
      repository/          #   generic CRUDRepository[X] + per-entity repos
    queue/
      queue.py             #   JobQueue port (Protocol) + get_job_queue() binding
      celery_queue.py      #   CeleryJobQueue: enqueue by task name
    channel/
      channel.py           #   MessageChannel port — send a reply/event to a client
      ws_channel.py        #   WebSocketChannel adapter
  entities/                # SQLModel table models — the shared domain (+ base.py = Base = SQLModel)
  schemas/                 # Pydantic DTOs — imported by routes ONLY
  core/                    # infrastructure bucket: settings, security, exceptions, logging, metrics,
                           #   telemetry, celery_app, task_names, di (reuse FastAPI DI outside requests)
  main.py                  # create_app() factory   ·   server.py  uvicorn runner
main.py                    # API entrypoint  ·  worker.py  Celery worker entrypoint
alembic/                   # migrations (schema owned here, not by the app)
tests/                     # pytest; conftest swaps in an in-memory DB and a fake queue
```

---

## How the pieces snap together

| Decision | Why it pays off |
|---|---|
| **Inbound = transport, Outbound = role** | New transport? Drop a folder in `inbound/`. New tech for an existing job? New adapter behind the same outbound port. The core is untouched either way. |
| **One DI everywhere (FastAPI `Depends`)** | `core/di.py:resolve()` runs FastAPI's own `solve_dependencies` against a session, so the exact `Annotated[X, Depends(X)]` wiring that powers routes also wires services in Celery tasks (`@inject`) and WebSockets. No composition root to maintain, no second framework. |
| **Service owns every output** | `Input → Service → Output`. Writes, job dispatch, and client pushes all originate in the service through ports — business intent and side effects live in one place. |
| **Generic `CRUDRepository[X]`** | Near-zero boilerplate per entity; the repository commits at the CRUD level and turns unique-violations into a clean `AlreadyExistsError → 409`. |
| **Ports as `Protocol`s** | `JobQueue`, `MessageChannel` are structural interfaces — the service depends on the abstraction, the adapter (`CeleryJobQueue`, `WebSocketChannel`) is swappable and trivially fakeable in tests. |
| **SQLModel + hardened pool** | One typed model for table + schema; the engine ships with `pool_pre_ping`/`pool_recycle`/sizing so it survives DB restarts and failovers — not a toy `create_engine(url)`. |
| **Schema owned by Alembic** | Versioned, reversible, auditable migrations — never silent `create_all()` drift. |

---

## Quick start

```bash
poetry install
poetry run pre-commit install     # lint + format + type hooks on every commit
poetry run alembic upgrade head   # create the schema (the app never auto-creates tables)
```

### Run the API

```bash
poetry run uvicorn app.main:app --reload     # or: poetry run python main.py
```

Docs: http://localhost:8000/docs · liveness: `GET /health` · metrics: `GET /metrics`

```bash
curl -X POST localhost:8000/persons \
  -H 'Content-Type: application/json' \
  -d '{"name":"Alice","age":25,"email":"alice@example.com"}'

curl "localhost:8000/persons?age=30&skip=0&limit=10"
```

### Run the Celery worker

Background jobs use Redis by default (`APP_CELERY_BROKER_URL`). Creating a person enqueues a follow-up job
through the `JobQueue` port; the worker runs it via the same services.

```bash
poetry run celery -A worker.celery_app worker -l info
```

### Try the WebSocket

`GET ws://localhost:8000/ws/persons` — send `{"person_id": 1}`, receive that person's overview. The handler only
receives; the **service** computes the result and pushes it back through the `MessageChannel` port.

---

## Authentication (Google OAuth2 → app JWT)

No passwords. Frontend gets a Google **ID token** → `POST /auth/google` → backend verifies it against
`APP_GOOGLE_CLIENT_ID`, provisions a `User` on first sign-in, and returns an app JWT. Call protected endpoints
with `Authorization: Bearer <jwt>` (e.g. `GET /auth/me`). Crypto lives in `core/security.py`; the
`CurrentUser → CurrentActiveUser → CurrentSuperuser` guard chain in `inbound/http/guards.py` protects routes.

---

## Add a new entity (the recipe)

1. `entities/<x>.py` — SQLModel table model.
2. `schemas/<x>.py` — `XCreate`, `XRead` (+ `XUpdate` only with a real update endpoint).
3. `outbound/persistence/repository/<x>_repository.py` — `class XRepository(CRUDRepository[X])`.
4. `service/<x>_service.py` — business logic; self-wires its repository/ports; calls outputs itself.
5. `inbound/http/routes/<x>.py` — router; map `XCreate → entity` and `entity → XRead` here; include in `main.py`.
6. Import the entity in `alembic/env.py`, then `alembic revision --autogenerate` + `upgrade head`.
7. `tests/test_<x>_api.py` — write the tests first (TDD).

Need it in the background? Add a task in `inbound/celery/` (declare deps with the same `Annotated[…, Depends]`
signature). Need to push it over a socket? Add a service method that calls a `MessageChannel`.

---

## Quality & testing

```bash
poetry run ruff check --fix . && poetry run ruff format .   # lint + format
poetry run mypy app                                         # types
poetry run pytest -q                                        # tests (in-memory DB, faked queue — no broker/DB needed)
```

`ruff` + `mypy` + `pytest` run on every commit via `pre-commit`. Tests swap the DB for in-memory SQLite (via
`get_db` override) and the queue for a no-op fake — fast, hermetic, no infra.

---

## Configuration

Settings come from `core/settings.py` (pydantic-settings); override via `APP_`-prefixed env vars or `.env`.
Highlights: `APP_ENV` (`local|stg|prod` — derives the DB URL), `APP_DATABASE_URL`, `APP_DB_POOL_*`,
`APP_CELERY_BROKER_URL`, `APP_GOOGLE_CLIENT_ID`, `APP_SECRET_KEY` (**override in prod**), `APP_OTEL_ENABLED`.

---

*Build features, not plumbing. Add transports, not rewrites. Swap tech, not your domain.*
