from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRET = "dev-insecure-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    database_url: str = "sqlite:///mydatabase.db"
    app_title: str = "Fast API Example App"
    log_level: str = "INFO"

    # Server
    env: str = "dev"  # dev | test | prod — controls auto-reload
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

    # Auth (Google OAuth2 sign-in -> app JWT session)
    google_client_id: str = ""  # set APP_GOOGLE_CLIENT_ID in real deployments
    secret_key: str = _DEV_SECRET  # set APP_SECRET_KEY in prod
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

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
