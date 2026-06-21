from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "dev-insecure-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    app_title: str = "Fast API Example App"
    log_level: str = "INFO"

    # DB selection is env-driven: local -> sqlite, stg/prod -> postgresql.
    # Set APP_DATABASE_URL to override the derived URL (e.g. in tests/CI); empty = derive.
    database_url: str = ""
    sqlite_path: str = "sqlite:///mydatabase.db"  # used only when env=local
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = ""
    postgres_password: str = ""
    postgres_db: str = "app"

    # DB connection pool (production hardening, ignored for sqlite). pre_ping/recycle
    # guard against stale connections after DB restarts/failover/idle reaping.
    db_echo: bool = False
    db_pool_pre_ping: bool = True
    db_pool_recycle: int = 1800  # seconds; recycle before server-side idle timeout
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_timeout: int = 30  # seconds to wait for a connection from the pool

    # Server
    env: str = "local"  # local | stg | prod — controls DB selection + auto-reload
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    # Observability (OpenTelemetry OTLP export — off unless explicitly enabled)
    otel_enabled: bool = False
    otel_service_name: str = "fastapi-example"
    otel_exporter_otlp_endpoint: str = "http://localhost:4318"  # OTLP/HTTP base URL

    # Celery (background jobs). Broker = Redis by default; result backend off
    # unless set (fire-and-forget). Swap the broker URL or the adapter for RabbitMQ.
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = ""  # empty -> no result tracking

    # Celery reliability. acks_late + reject_on_worker_lost: a task whose worker dies
    # mid-run is redelivered instead of silently lost (default acks on receipt = lost).
    # prefetch=1 keeps one unacked task per worker so redelivery is precise. Retries
    # are bounded with exponential backoff to ride out transient failures without a
    # poison loop. Caveat: a task that ALWAYS kills the worker redelivers forever.
    celery_task_acks_late: bool = True
    celery_task_reject_on_worker_lost: bool = True
    celery_worker_prefetch_multiplier: int = 1
    celery_task_max_retries: int = 3
    celery_task_retry_backoff: int = 5  # seconds; exponential base, jittered

    # Auth (Google OAuth2 sign-in -> app JWT session)
    google_client_id: str = ""  # set APP_GOOGLE_CLIENT_ID in real deployments
    secret_key: str = _DEV_SECRET  # set APP_SECRET_KEY in prod
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    @model_validator(mode="after")
    def _resolve_database_url(self) -> "Settings":
        # Only local runs on sqlite; stg/prod build a postgresql URL from APP_POSTGRES_*.
        if self.database_url:
            return self
        if self.env == "local":
            self.database_url = self.sqlite_path
        else:
            if not (self.postgres_user and self.postgres_password):
                raise ValueError(
                    f"env={self.env} requires APP_POSTGRES_USER and APP_POSTGRES_PASSWORD"
                )
            self.database_url = (
                f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
                f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
            )
        return self

    @model_validator(mode="after")
    def _require_prod_secrets(self) -> "Settings":
        # Fail fast instead of booting prod with a forgeable JWT key or no Google client.
        if self.env == "prod":
            missing = []
            if not self.secret_key or self.secret_key == _DEV_SECRET:
                missing.append("APP_SECRET_KEY")
            if not self.google_client_id:
                missing.append("APP_GOOGLE_CLIENT_ID")
            if missing:
                raise ValueError(
                    f"env=prod requires these to be set: {', '.join(missing)}"
                )
        return self


settings = Settings()
