from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_")

    database_url: str = "sqlite:///mydatabase.db"
    app_title: str = "Fast API Example App"
    log_level: str = "INFO"


settings = Settings()
