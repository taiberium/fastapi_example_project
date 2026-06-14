# Single-stage image; poetry installs main deps into the system env (no venv).
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=1.8.5 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

RUN pip install "poetry==${POETRY_VERSION}"

# Resolve + install deps first so this layer caches across code changes.
COPY pyproject.toml poetry.lock* ./
RUN poetry lock --no-update && poetry install --only main --no-root

COPY . .

EXPOSE 8000

# Alembic owns the schema — apply migrations, then serve.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
