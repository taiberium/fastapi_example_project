# FastAPI Example Project

A small, cleanly **layered** FastAPI application demonstrating production-style structure:
API → Service → Repository → DB, with Pydantic schemas, a generic CRUD repository, and centralized logging.

## Architecture

```
app/
  api/
    dependencies.py      # shared deps: get_pagination_params, get_<x>_service
    routes/              # one router file per entity (person.py)
  service/               # business logic — operates on entities only
  entities/              # SQLAlchemy ORM models (shared domain)
  schemas/               # Pydantic DTOs (used in routes only)
  persistence/           # storage layer
    db/                  # base_class (Base), session (engine), db (get_db)
    repository/          # generic CRUDRepository + per-entity singletons
  config/                # settings (pydantic-settings) + logging
  main.py                # create_app() factory
main.py                  # uvicorn entrypoint
tests/                   # pytest
```

Key conventions (see `CLAUDE.md` for the full list):

- **Three layers**, dependencies only point downward: `api → service → repository → db`.
- **Schema ↔ entity mapping happens in the route only** — service and repository work with entities.
- **Generic `CRUDRepository[ORMModel]`** instantiated per entity as a singleton; stateless (session passed per call).
- **`config/` holds settings only**; infrastructure and DI wiring live elsewhere.
- **Centralized logging** via `app/config/logging.py` (`get_logger(__name__)`).

## Requirements

- Python ^3.11
- [Poetry](https://python-poetry.org/)

## Setup

```bash
poetry install
```

## Run

```bash
poetry run uvicorn app.main:app --reload
# or
poetry run python main.py
```

API docs at http://localhost:8000/docs

### Example

```bash
curl -X POST localhost:8000/persons \
  -H 'Content-Type: application/json' \
  -d '{"name": "Alice", "age": 25, "email": "alice@example.com"}'

curl "localhost:8000/persons?age=30"
```

## Test

```bash
poetry run pytest -q
```

## Configuration

Settings (via `app/config/settings.py`, overridable with `APP_`-prefixed env vars or a `.env` file):

| Setting        | Env var            | Default                      |
|----------------|--------------------|------------------------------|
| `database_url` | `APP_DATABASE_URL` | `sqlite:///mydatabase.db`    |
| `app_title`    | `APP_APP_TITLE`    | `Fast API Example App`       |
| `log_level`    | `APP_LOG_LEVEL`    | `INFO`                       |
