from pydantic_settings import BaseSettings
from pydantic import AnyUrl, Field, field_validator


class Settings(BaseSettings):
    # Core
    APP_NAME: str = "GRAVIX Backend"
    API_PREFIX: str = "/api"
    SECRET_KEY: str = Field(..., description="Secret key for signing sessions and CSRF tokens")
    DEBUG: bool = False

    # Database and Redis
    DATABASE_URL: AnyUrl = Field(..., description="Postgres URL, e.g. postgresql+asyncpg://user:pass@db:5432/gravix")
    REDIS_URL: str = "redis://redis:6379/0"

    # Security and Auth
    SESSION_COOKIE_NAME: str = "gravix_session"
    CSRF_COOKIE_NAME: str = "gravix_csrf"
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_SAMESITE: str = "strict"
    SESSION_EXPIRE_MINUTES: int = 60 * 24

    # CORS (comma-separated string supported)
    CORS_ORIGINS: list[str] | str = ["http://localhost:5173"]

    # Master bot integration
    MASTER_COMMANDS_CHANNEL: str = "gravix:commands"
    REDIS_EVENTS_CHANNELS: list[str] = [
        "events:containers",
        "events:builds",
        "events:support",
        "events:metrics",
    ]
    MASTER_BOT_API_TOKEN: str | None = None  # if HTTP integration is used

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, v):
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()