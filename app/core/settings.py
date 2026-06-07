from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    database_url: str = "sqlite:///mydatabase.db"
    app_title: str = "Fast API Example App"
    log_level: str = "INFO"

    # Server
    env: str = "dev"  # dev | test | prod — controls auto-reload
    server_host: str = "0.0.0.0"
    server_port: int = 8000

    # Auth (Google OAuth2 sign-in -> app JWT session)
    google_client_id: str = ""  # set APP_GOOGLE_CLIENT_ID in real deployments
    secret_key: str = "dev-insecure-change-me"  # set APP_SECRET_KEY in prod
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24


settings = Settings()
