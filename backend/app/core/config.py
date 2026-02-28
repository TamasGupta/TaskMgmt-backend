from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Database (asyncpg DSN)
    DATABASE_URL: str

    # Seed admin credentials
    SUPABASE_AUTH_EMAIL: str = "user@example.com"
    SUPABASE_AUTH_PASSWORD: str = "pass"

    # App
    APP_PORT: int = 4000
    APP_ENV: str = "development"


settings = Settings()
