# CLAUDE.md — FastAPI project conventions

Guidance for working in this repo. Follow these patterns when adding or changing code.

## Layered architecture (ports & adapters)

The app core (`service/`) is transport-agnostic. Everything that touches the outside world is an
**adapter**, split by direction:

```
inbound/  (driving: how the world calls in)  →  service/  →  outbound/  (driven: how we call out)
   http/ (FastAPI)                                              persistence/ (DB)
   celery/ (Celery worker)                                     queue/ (enqueue jobs)
   websocket/ ...                                              clients/ ... (future)
```

- **inbound/** — driving adapters, one folder per **transport** (`http`, `celery`, `websocket`). Thin:
  translate the incoming request/message into a service call and map the result back. **Named by transport**
  (concrete entrypoints). `inbound/http` is the only place that maps schema ↔ entity
  (`Entity(**data.model_dump())` in, `XRead.model_validate(entity)` out).
- **service/** — business logic, orchestrates repositories + outbound ports. **Operates on entities only —
  schemas never reach this layer.** Knows nothing about HTTP or Celery.
- **outbound/** — driven adapters, **named by role/port** (`persistence`, `queue`), with the concrete tech
  hidden inside (SQLModel, Celery). The service depends on the abstraction, so the tech is swappable.
  - **outbound/persistence/repository/** — data access: SQLModel `session.exec(select(...))` on **entities only**.
  - **outbound/queue/** — the `JobQueue` port + a `CeleryJobQueue` adapter (enqueue background work).
- An inbound adapter must NOT touch a repository or `Session` directly — always go through a service.

**Self-wiring DI (class-based dependencies).** There is NO central `dependencies.py`. Each class declares
its own dependencies in its `__init__` via `Annotated[..., Depends(...)]`, so it is usable as a FastAPI
dependency on its own:
- a repository self-wires the request `Session`: `def __init__(self, session: Annotated[Session, Depends(get_db)])`;
- a service self-wires its repositories: `def __init__(self, repo: Annotated[PersonRepository, Depends(PersonRepository)])`;
- a route depends on the service directly: `service: Annotated[PersonService, Depends(PersonService)]`.

FastAPI resolves the whole chain (service → repository → `get_db`) automatically. **Consequence:** `fastapi.Depends`
is imported in `service/` and `repository/` constructors — this is an accepted, deliberate coupling to the web
framework's DI, the price of deleting the wiring module. (Schemas still never appear below the route — see below.)

**Use `Annotated[T, Depends(...)]` everywhere — never bare `x: T = Depends(...)` defaults.** Route-level type
aliases (e.g. `PersonServiceDep = Annotated[PersonService, Depends(PersonService)]`) live at the top of the
route file that uses them.

**Schema ↔ entity mapping ALWAYS happens at the route level — never in the service.** Pydantic schemas are
used in `routes` ONLY. The route translates the outer-world DTO into a domain entity before calling the
service, and translates the returned entity back into a response DTO. Both `service` and `repository` work
purely with ORM entities. This keeps everything below the API boundary decoupled from web-layer DTOs.

**Cross-entity composition lives in the service.** When a response needs data from multiple entities, the
service holds multiple repositories and combines them into a small domain aggregate (a plain `@dataclass`, NOT
a schema or ORM entity) — see `PersonService.get_overview` joining Person + Membership and computing
`is_premium`. The repositories stay single-entity; the join/business logic is the service's job; the route
maps the aggregate to a response DTO.

## Folder structure

`entities/` and `schemas/` are **shared domain models** used across layers, so they sit at the top level.
Adapters are grouped by direction under `inbound/` and `outbound/`.

```
app/
  inbound/                 # driving adapters — the world calls in (named by transport)
    http/
      routes/              # one router file per entity (person.py, auth.py, ...); route-level Annotated aliases
      guards.py            # auth guards: CurrentUser → CurrentActiveUser → CurrentSuperuser
      transaction.py       # TransactionMiddleware: one tx per request (commit on 2xx, else rollback, close)
    celery/
      person_tasks.py      # @celery_app.task definitions — the worker runs these (thin: delegate to service)
  outbound/                # driven adapters — we call out (named by role/port)
    persistence/
      db/                  # session.py (engine + SessionLocal + session_scope), db.py (get_db)
      repository/          # crud_repository.py + per-entity repos
    queue/
      queue.py             # JobQueue port (Protocol) + get_job_queue() adapter binding
      celery_queue.py      # CeleryJobQueue: send_task by name
  service/                 # business logic (PersonService, AuthService) — transport-agnostic
  entities/                # SQLModel table models (person.py, ...) + base.py (Base = SQLModel)
  schemas/                 # Pydantic DTOs (person.py, auth.py, pagination.py)
  core/                    # infra bucket: settings, security, exceptions, logging, metrics, telemetry,
                           #   celery_app.py (Celery instance), task_names.py (producer/consumer contract)
  server.py                # uvicorn runner;  main.py  # create_app() factory
main.py                    # API entrypoint → app.server.run()
worker.py                  # Celery worker entrypoint (celery -A worker.celery_app worker)
alembic/                   # migrations (env.py wired to settings + Base.metadata)
tests/                     # pytest; conftest points the middleware at in-memory sqlite + fakes the queue
```

Notes:
- **inbound is named by transport** (concrete entrypoints, nothing to abstract); **outbound is named by role**
  (`persistence`, `queue`) with the tech hidden inside — that asymmetry is deliberate and enables swaps.
- **`core/` is the infrastructure bucket**: settings VALUES + cross-cutting BEHAVIOR (security, exceptions,
  logging, metrics, telemetry, the Celery instance, the task-name contract). Keep `settings.py` (values) separate
  from behavior. What does NOT belong: domain (`entities`), business logic (`service`), adapters (`inbound`/`outbound`).
- DI is self-wired in each class's `__init__` (no central wiring module).

## Repository pattern (generic CRUD)

- `app/outbound/persistence/repository/crud_repository.py` holds a generic `CRUDRepository[ORMModel]` (generic in the ORM model
  only) with `get_one`, `get_many`, `create`, `update`, `delete`.
- **The repository holds the Session** and is constructed **per request** — NOT a singleton. The generic base
  takes `(model, session)`; the per-entity subclass self-wires the session via `Depends(get_db)`.
- Each entity gets a thin subclass that binds the model: `class PersonRepository(CRUDRepository[Person])` with
  `__init__(self, session: Annotated[Session, Depends(get_db)]): super().__init__(Person, session)`. Entity-specific
  queries live there — that's the reason the subclass exists (e.g. `PersonRepository.find_by_email`, built on `get_one`).
- **No schema coupling**: `create(db_obj)` takes a ready **entity**; `update(db_obj, values: dict)` takes a
  plain dict of fields. The **route** builds the entity from a schema (`Entity(**data.model_dump())`) — neither
  service nor repo imports Pydantic schemas.
- `*args` → `.where(...)` (expressions like `Person.age < age`); `**kwargs` → `.filter_by(...)` (equality).

## Database / sessions

- **One unit of work, ONE implementation: `session_scope()`** (`app/outbound/persistence/db/session.py`).
  It opens a session, **commits on success**, **rolls back on any exception**, always **closes**. Both entry
  points use it — HTTP and Celery manage sessions identically.
- **HTTP**: `TransactionMiddleware` (`app/inbound/http/transaction.py`) is a thin shell — it runs
  `session_scope(app.state.db_sessionmaker)` around the request and exposes the session on `request.state.db`.
  The commit happens *inside* request handling (not a `yield` teardown), so a failed commit surfaces as a real
  HTTP 500 — not a `200` already sent. (Commit-on-success means a deliberately-returned 4xx commits a no-op;
  abort by raising — `HTTPException`/`AlreadyExistsError` — never write-then-return-4xx.)
- **Celery**: tasks open `with session_scope() as db:` directly (default `SessionLocal`).
- **Forget-proof + atomic by design.** Routes and services NEVER call `commit` — can't be forgotten, and every
  write in a request/task shares the one transaction, so multi-write use-cases are atomic automatically.
- `get_db()` (in `app/outbound/persistence/db/db.py`) is a tiny dependency that just returns `request.state.db`.
  Repos self-wire it (`Annotated[Session, Depends(get_db)]`); the service holds repositories, never a raw `Session`.
- **Repositories flush, they do NOT commit.** `CRUDRepository._flush()` calls `session.flush()` inside each
  `create`/`update`/`delete` — populates autogenerated PKs and surfaces unique violations immediately
  (`IntegrityError → AlreadyExistsError`, with a rollback). `session_scope` does the single commit. Reads never write.
- The session source is `app.state.db_sessionmaker` (set to `SessionLocal` in `create_app`); **tests swap it for
  an in-memory maker** via `app.state.db_sessionmaker = ...` — no `get_db` override needed.
- `Session` is **SQLModel's** `Session` (`from sqlmodel import Session`), a SQLAlchemy `Session` subclass.
- **Caveat:** request-scoped session — for DB work outside a request use Celery tasks with `session_scope()`,
  not FastAPI `BackgroundTasks` (those run after commit/close). (And `BaseHTTPMiddleware` buffers streaming
  responses; fine for the JSON API.)
- `Base` lives in `app/entities/base.py` and is just `Base = SQLModel` — the shared declarative
  base + metadata for every table model (one import site for alembic/tests). It sits in `entities/`
  (not `outbound/persistence/`) because it is the parent of the domain models, so entities never reach down
  into the storage layer for it.
- **ORM is SQLModel.** Entities are `class X(Base, table=True)` with `Field(...)`; the PK is
  `id: int = Field(default=None, primary_key=True)`. Repository reads use `session.exec(select(Model)...)`
  (SQLModel's typed `exec`, NOT the deprecated `session.query`).
- **Engine/pool** (`app/outbound/persistence/db/session.py:get_engine`): production pool hardening from settings —
  `pool_pre_ping`, `pool_recycle`, `pool_size`, `max_overflow`, `pool_timeout`, `pool_reset_on_return="rollback"`,
  `pool_use_lifo`. QueuePool tuning is applied only for real servers; sqlite gets `check_same_thread=False` +
  pre_ping/recycle. All knobs are env-driven (`APP_DB_*`).

## Schemas (Pydantic)

- DTOs are separate from ORM entities. Define **only what the API actually uses**: `XCreate` (POST body) and
  `XRead` (response). Add `XUpdate` (all-optional input) ONLY when a real update endpoint exists — don't create
  schemas just to satisfy a generic signature.
- `XRead` sets `model_config = ConfigDict(from_attributes=True)`; convert with `XRead.model_validate(entity)`.
- Validation belongs in the schema (`Field(ge=0)`, etc.), not in the router body.
- Schemas are imported in `routes` ONLY — never in `service` or `repository`. The route owns both directions
  of the schema ↔ entity mapping. (Note: `fastapi.Depends` *does* appear in service/repository constructors
  for self-wiring — that's DI, not schema coupling; the schema rule is unchanged.)

## Authentication & security

- **Google OAuth2** is the auth model (per the user's global default), NOT password login.
  Flow: frontend Google Sign-In → sends Google **ID token** → `POST /auth/google` →
  `app/core/security.py:verify_google_id_token` validates it against `settings.google_client_id` →
  `AuthService` get-or-creates the `User` from the verified claims → issues an **app JWT** session token.
- `app/core/security.py` owns crypto: `create_access_token` / `decode_access_token` (jose JWT, `settings.secret_key`)
  and `verify_google_id_token` (google-auth). No passwords / no bcrypt.
- Protected endpoints depend on the class-based guard chain in `app/inbound/http/guards.py`:
  `CurrentUser` → `CurrentActiveUser` → `CurrentSuperuser` (HTTPBearer → decode JWT → load user). Each guard
  resolves the user in its `__init__` and exposes it as `.user`; routes read `guard.user`.
- HTTP error helpers live in `app/core/exceptions.py` (`get_credential_exception`, `get_not_found_exception`).
- Secrets come from settings/env (`APP_GOOGLE_CLIENT_ID`, `APP_SECRET_KEY`) — the defaults are dev-only and
  MUST be overridden in prod. Never log tokens.

## Observability

- `app/core/metrics.py:setup_metrics(app)` exposes Prometheus HTTP metrics at **`/metrics`**
  (via `prometheus-fastapi-instrumentator`), wired in `create_app()`. Each app gets a fresh
  `CollectorRegistry` so re-creating the app (tests) doesn't double-register.
- `/metrics` is internal — scrape it with Prometheus inside the network, don't expose publicly.
- No Prometheus/Grafana infra in-repo yet (app-side only); add docker-compose if/when needed.

## Background jobs (Celery)

- **Celery is on both sides of the hexagon.** Consuming a task (the worker running it) is *inbound*; enqueuing
  a job (`.delay`/`send_task`) is *outbound*. Keep them apart.
- **Producing** — `outbound/queue/`: services depend on the `JobQueue` **port** (`queue.py`), never on Celery.
  The `CeleryJobQueue` adapter (`celery_queue.py`) enqueues by **task name** via `celery_app.send_task(...)`,
  so it never imports the task definition → producer and worker stay decoupled. `get_job_queue()` is the single
  place binding the port to the adapter (swap here for RabbitMQ etc.).
- **Consuming** — `inbound/celery/`: `@celery_app.task` functions, thin like routes — open a `session_scope()`,
  `resolve(Service, db)` for the service, delegate. **Never touch repositories** — go through the service.
- **Contract** — task-name constants in `core/task_names.py`, imported by both sides (no inbound↔outbound import).
- **Instance/config** — `core/celery_app.py` (broker = `settings.celery_broker_url`, Redis by default; result
  backend off unless `settings.celery_result_backend` set). Tasks listed in `include=[...]`.
- **Same DI everywhere** — `core/di.py:resolve(Service, db)` reuses FastAPI's own resolver
  (`solve_dependencies`) against a synthetic request whose `state.db = db`, so the SAME `Annotated[X, Depends(X)]`
  self-wiring that routes use also wires services for tasks. No composition root, no hand-wiring. The symmetry:
  HTTP = `TransactionMiddleware` (session_scope) + FastAPI resolves the route's deps; Celery = task opens
  `session_scope` + `resolve()` runs the same resolver. (Caveat: `resolve` uses `asyncio.run` — fine for the
  default prefork worker; revisit for async worker pools. It also leans on a FastAPI-internal API.)
- **Tests**: no broker — `conftest` overrides `get_job_queue` with `tests/fakes.py:FakeJobQueue` and asserts on it.

## Server entrypoint

- `app/server.py:run()` calls `uvicorn.run("app.main:app", ...)` with host/port from settings and reload
  enabled when `settings.env` is `dev`/`test`. Root `main.py` just delegates to it.
- **Worker**: `worker.py` exposes `celery_app`; run `poetry run celery -A worker.celery_app worker -l info`.

## Migrations (Alembic)

- The schema is owned by **Alembic**, NOT by the app. `create_app()` does NOT call `create_all()`.
- `alembic/env.py` reads `settings.database_url` and targets `Base.metadata` — never hardcode the URL in
  `alembic.ini`. Import every entity in `env.py` so autogenerate sees its table.
- Workflow after changing an ORM model: `alembic revision --autogenerate -m "..."` → review the file →
  `alembic upgrade head`. Always read the generated migration before applying (autogenerate is not perfect).
- Entities are SQLModel, so autogenerated migrations reference `sqlmodel.sql.sqltypes.*` (e.g. `AutoString`);
  `alembic/script.py.mako` already adds `import sqlmodel` so generated files import cleanly.
- Tests don't use Alembic — `conftest` builds an in-memory schema via `Base.metadata.create_all` on its own engine.

## Logging

- Config lives in `app/core/logging.py`: `configure_logging()` (root handler + format, level from
  `settings.log_level`) and `get_logger(name)`. Called once in `create_app()`.
- Every module gets `log = get_logger(__name__)`. Use it instead of `print`.
- Levels by layer: **service** logs business operations at `INFO`; **repository** and **db** session log at
  `DEBUG`; startup/errors at `INFO`/`ERROR`. Don't log sensitive values (passwords, tokens).
- `log_level` is configurable via `APP_LOG_LEVEL` env var.

## HTTP layer (inbound/http)

- **No `dependencies.py`.** DI is self-wired: services/repositories declare their deps in `__init__`, and
  routes depend on the service class directly (`Annotated[XService, Depends(XService)]`).
- Auth guards are class-based dependencies in `app/inbound/http/guards.py` (`CurrentUser` → `CurrentActiveUser` →
  `CurrentSuperuser`).
- Pagination is a **pydantic DTO** `app/schemas/pagination.py:PaginationParams` (request input, stays
  query params). FastAPI 0.100 does NOT enforce a pydantic model's `Field(ge/gt)` when the model is used
  directly as a dependency (invalid values 500, not 422), so the route wires it through a tiny
  `get_pagination(skip=Query(0,ge=0), limit=Query(10,gt=0)) -> PaginationParams` — `Query()` does the 422
  validation, the schema is just the DTO. (A FastAPI upgrade to ≥0.115 would allow `Annotated[PaginationParams,
  Query()]` directly.)
- Route-level `Annotated[...]` aliases live at the top of the route file that uses them.
- One router file per entity under `app/inbound/http/routes/`, registered in `app/main.py` via `app.include_router(...)`.

## Adding a new entity (checklist)

1. `entities/<x>.py` — ORM model.
2. `schemas/<x>.py` — `XCreate`, `XRead` (add `XUpdate` only if there's an update endpoint).
3. `outbound/persistence/repository/<x>_repository.py` — `class XRepository(CRUDRepository[X])` binding the model;
   self-wires the session via `__init__(self, session: Annotated[Session, Depends(get_db)])`.
4. `service/<x>_service.py` — business logic; self-wires its repository via
   `__init__(self, repo: Annotated[XRepository, Depends(XRepository)])`; methods accept/return **entities** (no schemas).
5. `inbound/http/routes/<x>.py` — router; add a route-level alias `XServiceDep = Annotated[XService, Depends(XService)]`;
   maps `XCreate → entity` and `entity → XRead` here; include it in `main.py`.
6. `tests/test_<x>_api.py` — write tests FIRST (TDD).

## Workflow rules

- **TDD**: write tests before the implementation. Tests define expected behavior.
- Before marking any feature done: `ruff check` + `mypy app` + `poetry run pytest` (all green), verify locally.
- Use **poetry** for dependency management. Type-hint everything.
- Comments only where the code isn't self-explanatory — short as possible.
- Config goes only in `app/core/`; secrets in config files, never in infra.

## Tooling (quality gates)

- **ruff** = linter + formatter (replaces flake8/isort/black). Config in `[tool.ruff]`.
  FastAPI's `Depends`/`Query` are allow-listed for B008 (DI idiom is fine).
- **mypy** = type checker. Config in `[tool.mypy]` (pydantic plugin on; alembic ignored).
- **pre-commit** runs ruff + ruff-format + mypy on every commit (`.pre-commit-config.yaml`).
  Run `poetry run pre-commit install` once after cloning.

## Commands

- Install: `poetry install && poetry run pre-commit install`
- Run: `poetry run uvicorn app.main:app --reload` (or `python main.py`)
- Test: `poetry run pytest -q`
- Lint/format: `poetry run ruff check --fix . && poetry run ruff format .`
- Types: `poetry run mypy app`
- All hooks: `poetry run pre-commit run --all-files`
