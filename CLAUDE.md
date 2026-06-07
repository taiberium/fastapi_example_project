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
    dependencies.py      # shared deps: get_pagination_params, get_<x>_service
    routes/              # one router file per entity (person.py, ...)
  service/               # one service per entity (PersonService)
  entities/              # SQLAlchemy ORM models — shared domain, used by service + repository
  schemas/               # Pydantic DTOs: <X>Create, <X>Update, <X>Read
  persistence/           # storage layer only
    db/
      base_class.py      # Base (DeclarativeBase) only
      session.py         # engine, SessionLocal, get_engine/get_local_session builders
      db.py              # get_db() generator dependency
    repository/
      base.py            # generic CRUDRepository
      person_repository.py # singleton: person_repository = CRUDRepository[...](model=Person)
  config/
    settings.py          # pydantic-settings BaseSettings — ONLY app config lives here, nothing else
  main.py                # create_app() factory, includes routers
main.py                  # uvicorn entrypoint → app.main:app
tests/                   # pytest; conftest overrides get_db with in-memory sqlite
```

Notes:
- `entities/` is top-level because `service/` references entities — a layer must not reach into
  `persistence/` internals to get them.
- `config/` holds settings only. Infrastructure (engine/session) and DI wiring are NOT config —
  they live in `persistence/db/` and `api/dependencies.py` respectively.

## Repository pattern (generic CRUD)

- `app/persistence/repository/base.py` holds a generic `CRUDRepository[ORMModel]` (generic in the ORM model
  only) with `get_one`, `get_many`, `create`, `update`, `delete`.
- Repositories are **stateless** — the `db: Session` is passed per method call, never stored on the instance.
- **No schema coupling**: `create(db, db_obj)` takes a ready **entity**; `update(db, db_obj, values: dict)` takes a
  plain dict of fields. The **route** builds the entity from a schema (`Entity(**data.model_dump())`) and passes
  the entity through the service — neither service nor repo imports Pydantic schemas.
- `*args` → `.filter(...)` (expressions like `Person.age < age`); `**kwargs` → `.filter_by(...)` (equality).
- Each entity = one **module-level singleton**: `person_repository = CRUDRepository(model=Person)` (no schema
  type params — gymhero style).

## Database / sessions

- `get_db()` (in `app/persistence/db/db.py`) is the only session dependency: `db = SessionLocal(); try: yield db; finally: db.close()`.
- Inject it via `Depends(get_db)` — never create a `Session()` ad hoc inside services/repositories.
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

## Logging

- Config lives in `app/config/logging.py`: `configure_logging()` (root handler + format, level from
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
3. `persistence/repository/<x>_repository.py` — `x_repository = CRUDRepository(model=X)`.
4. `service/<x>_service.py` — business logic, takes a `Session`; methods accept/return **entities** (no schemas).
5. `api/dependencies.py` — add `get_<x>_service`.
6. `api/routes/<x>.py` — router; maps `XCreate → entity` and `entity → XRead` here; include it in `main.py`.
7. `tests/test_<x>_api.py` — write tests FIRST (TDD).

## Workflow rules

- **TDD**: write tests before the implementation. Tests define expected behavior.
- Before marking any feature done: import-check the app, run `poetry run pytest` (all green), verify locally.
- Use **poetry** for dependency management. Type-hint everything.
- Comments only where the code isn't self-explanatory — short as possible.
- Config goes only in `app/config/`; secrets in config files, never in infra.

## Commands

- Install: `poetry install`
- Run: `poetry run uvicorn app.main:app --reload` (or `python main.py`)
- Test: `poetry run pytest -q`
