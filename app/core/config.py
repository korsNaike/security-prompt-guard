from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "UniClassify Platform"
    app_version: str = "0.1.0"
    environment: str = "local"
    database_url: str = Field(
        default="postgresql+asyncpg://uniclassify:uniclassify@postgres:5432/uniclassify"
    )
    redis_url: str = "redis://redis:6379/0"
    model_config_path: str = "config/models.yml"
    jwt_secret_key: str = "change-me-change-me-change-me-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    initial_credits: int = 100
    cache_hit_cost: int = 1

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
