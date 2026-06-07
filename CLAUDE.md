# CLAUDE.md — FastAPI project conventions

Guidance for working in this repo. Follow these patterns when adding or changing code.

## Layered architecture

Three layers, each depends only on the one below — never skip or reverse direction:

```
api (routes)  →  service  →  repository  →  db (session)
```

- **api/** — incoming world: FastAPI routers + dependency wiring. **The route is the only place that maps
  schema ↔ entity** (`Entity(**data.model_dump())` on the way in, `XRead.model_validate(entity)` on the way out).
- **service/** — business logic. Holds the `Session`, orchestrates repositories. **Operates on entities only —
  schemas never reach this layer.**
- **repository/** — outgoing data access. SQLAlchemy queries on **entities only** — no business rules, no schemas.
- A router must NOT touch a repository or a `Session` directly — always go through a service.

**Schema ↔ entity mapping ALWAYS happens at the route level — never in the service.** Pydantic schemas are
used in `routes` ONLY. The route translates the outer-world DTO into a domain entity before calling the
service, and translates the returned entity back into a response DTO. Both `service` and `repository` work
purely with ORM entities. This keeps everything below the API boundary decoupled from web-layer DTOs.

## Folder structure

`entities/` and `schemas/` are **shared domain models** used across layers (service +
persistence), so they sit at the top level — NOT inside `persistence/`. `persistence/`
holds only the storage infrastructure (`db/`) and data access (`repository/`).

```
app/
  api/
    dependencies.py      # shared deps: pagination, get_<x>_service, get_current_user chain
    routes/              # one router file per entity (person.py, auth.py, ...)
  service/               # business logic (PersonService, AuthService)
  entities/              # SQLAlchemy ORM models — shared domain (person.py, user.py)
  schemas/               # Pydantic DTOs (person.py, auth.py)
  persistence/           # storage layer only
    db/
      base_class.py      # Base (DeclarativeBase) only
      session.py         # engine, SessionLocal, get_engine builder
      db.py              # get_db() generator dependency
    repository/
      base.py            # generic CRUDRepository[ORMModel] — holds the Session, built per request
      person_repository.py # class PersonRepository(CRUDRepository[Person])
      user_repository.py   # class UserRepository(CRUDRepository[User])
  core/                # infrastructure bucket (NOT just settings values)
    settings.py          #   the VALUES: pydantic-settings BaseSettings (env-driven)
    security.py          #   JWT issue/decode + Google ID-token verification
    exceptions.py        #   HTTPException helpers + app exceptions
    logging.py           #   configure_logging() + get_logger()
  server.py              # uvicorn runner (host/port/reload from settings)
  main.py                # create_app() factory, includes routers
main.py                  # entrypoint → delegates to app.server.run()
alembic/                 # migrations (env.py wired to settings + Base.metadata)
tests/                   # pytest; conftest overrides get_db with in-memory sqlite
```

Notes:
- `entities/` is top-level because `service/` references entities — a layer must not reach into
  `persistence/` internals to get them.
- **`core/` is the infrastructure bucket** (broad sense of "config" = how the app is configured/assembled):
  settings VALUES + cross-cutting BEHAVIOR (security, exceptions, logging). The one rule inside it: keep
  `settings.py` (values, from env) clearly separate from the behavior modules. What does NOT belong in
  `core/`: domain (`entities`), business logic (`service`), data access (`persistence`), routes (`api`).
- DB infrastructure (engine/session) stays in `persistence/db/`; request DI wiring stays in
  `api/dependencies.py` — those are layer-specific, not app-wide config.

## Repository pattern (generic CRUD)

- `app/persistence/repository/base.py` holds a generic `CRUDRepository[ORMModel]` (generic in the ORM model
  only) with `get_one`, `get_many`, `create`, `update`, `delete`.
- **The repository holds the Session** (`__init__(self, model, session)`) and is constructed **per request** —
  NOT a singleton. This keeps the Session a persistence detail: layers above the repository never touch SQLAlchemy.
- Each entity gets a thin subclass that binds the model: `class PersonRepository(CRUDRepository[Person])` with
  `__init__(self, session): super().__init__(Person, session)`. Entity-specific queries live there — that's the
  reason the subclass exists (e.g. `PersonRepository.find_by_email`, built on the generic `get_one`).
- **No schema coupling**: `create(db_obj)` takes a ready **entity**; `update(db_obj, values: dict)` takes a
  plain dict of fields. The **route** builds the entity from a schema (`Entity(**data.model_dump())`) — neither
  service nor repo imports Pydantic schemas.
- `*args` → `.filter(...)` (expressions like `Person.age < age`); `**kwargs` → `.filter_by(...)` (equality).

## Database / sessions

- `get_db()` (in `app/persistence/db/db.py`) is the only session dependency: `db = SessionLocal(); try: yield db; finally: db.close()`.
- **DI chain**: `get_db` → `get_<x>_repository(db)` (builds the repo with the session) → `get_<x>_service(repo)`
  (builds the service with the repo). The **service holds a repository, never a `Session`**; only the
  repository factory in `api/dependencies.py` references `Session`.
- Never create a `Session()` ad hoc inside services/repositories — always flow from `get_db`.
- `Base` lives in `app/persistence/db/base_class.py` (avoids circular imports between entities and the engine).
- Use SQLAlchemy 2.0 typed style in entities: `Mapped[...]` + `mapped_column(...)`.

## Schemas (Pydantic)

- DTOs are separate from ORM entities. Define **only what the API actually uses**: `XCreate` (POST body) and
  `XRead` (response). Add `XUpdate` (all-optional input) ONLY when a real update endpoint exists — don't create
  schemas just to satisfy a generic signature.
- `XRead` sets `model_config = ConfigDict(from_attributes=True)`; convert with `XRead.model_validate(entity)`.
- Validation belongs in the schema (`Field(ge=0)`, etc.), not in the router body.
- Schemas are imported in `routes` ONLY — never in `service` or `repository`. The route owns both directions
  of the schema ↔ entity mapping.

## Authentication & security

- **Google OAuth2** is the auth model (per the user's global default), NOT password login.
  Flow: frontend Google Sign-In → sends Google **ID token** → `POST /auth/google` →
  `app/core/security.py:verify_google_id_token` validates it against `settings.google_client_id` →
  `AuthService` get-or-creates the `User` from the verified claims → issues an **app JWT** session token.
- `app/core/security.py` owns crypto: `create_access_token` / `decode_access_token` (jose JWT, `settings.secret_key`)
  and `verify_google_id_token` (google-auth). No passwords / no bcrypt.
- Protected endpoints depend on the chain in `api/dependencies.py`:
  `get_current_user` → `get_current_active_user` → `get_current_superuser` (HTTPBearer → decode JWT → load user).
- HTTP error helpers live in `app/core/exceptions.py` (`get_credential_exception`, `get_not_found_exception`).
- Secrets come from settings/env (`APP_GOOGLE_CLIENT_ID`, `APP_SECRET_KEY`) — the defaults are dev-only and
  MUST be overridden in prod. Never log tokens.

## Observability

- `app/core/metrics.py:setup_metrics(app)` exposes Prometheus HTTP metrics at **`/metrics`**
  (via `prometheus-fastapi-instrumentator`), wired in `create_app()`. Each app gets a fresh
  `CollectorRegistry` so re-creating the app (tests) doesn't double-register.
- `/metrics` is internal — scrape it with Prometheus inside the network, don't expose publicly.
- No Prometheus/Grafana infra in-repo yet (app-side only); add docker-compose if/when needed.

## Server entrypoint

- `app/server.py:run()` calls `uvicorn.run("app.main:app", ...)` with host/port from settings and reload
  enabled when `settings.env` is `dev`/`test`. Root `main.py` just delegates to it.

## Migrations (Alembic)

- The schema is owned by **Alembic**, NOT by the app. `create_app()` does NOT call `create_all()`.
- `alembic/env.py` reads `settings.database_url` and targets `Base.metadata` — never hardcode the URL in
  `alembic.ini`. Import every entity in `env.py` so autogenerate sees its table.
- Workflow after changing an ORM model: `alembic revision --autogenerate -m "..."` → review the file →
  `alembic upgrade head`. Always read the generated migration before applying (autogenerate is not perfect).
- Tests don't use Alembic — `conftest` builds an in-memory schema via `Base.metadata.create_all` on its own engine.

## Logging

- Config lives in `app/core/logging.py`: `configure_logging()` (root handler + format, level from
  `settings.log_level`) and `get_logger(name)`. Called once in `create_app()`.
- Every module gets `log = get_logger(__name__)`. Use it instead of `print`.
- Levels by layer: **service** logs business operations at `INFO`; **repository** and **db** session log at
  `DEBUG`; startup/errors at `INFO`/`ERROR`. Don't log sensitive values (passwords, tokens).
- `log_level` is configurable via `APP_LOG_LEVEL` env var.

## API layer

- `app/api/dependencies.py` holds shared deps: `get_pagination_params(skip, limit) -> Tuple[int, int]` and
  per-service providers `get_<entity>_service(db = Depends(get_db))`.
- Auth deps (`get_token`, `get_current_user`, `get_current_active_user`, `get_current_superuser`) go here once a
  `User` model exists — not added yet.
- One router file per entity under `app/api/routes/`, registered in `app/main.py` via `app.include_router(...)`.

## Adding a new entity (checklist)

1. `entities/<x>.py` — ORM model.
2. `schemas/<x>.py` — `XCreate`, `XRead` (add `XUpdate` only if there's an update endpoint).
3. `persistence/repository/<x>_repository.py` — `class XRepository(CRUDRepository[X])` binding the model.
4. `service/<x>_service.py` — business logic, takes the **repository**; methods accept/return **entities** (no Session, no schemas).
5. `api/dependencies.py` — add `get_<x>_repository(db)` and `get_<x>_service(repo)`.
6. `api/routes/<x>.py` — router; maps `XCreate → entity` and `entity → XRead` here; include it in `main.py`.
7. `tests/test_<x>_api.py` — write tests FIRST (TDD).

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
