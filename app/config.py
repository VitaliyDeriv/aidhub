"""Конфігурація застосунку.

Усі налаштування читаються зі змінних оточення. Для локального запуску
додатково підхоплюється файл `.env.<APP_ENV>` (`.env.sandbox`,
`.env.production`). Реальні змінні оточення мають пріоритет над файлом,
тому в Docker достатньо передати їх через `env_file` / `environment`.
У коді немає жодних hardcoded-паролів чи ключів.
"""

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_SECRETS = {"change-me", "changeme", "secret"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")

    app_env: Literal["sandbox", "production", "test"] = "sandbox"
    debug: bool = False

    database_url: str
    db_pool_size: int = 5
    db_max_overflow: int = 10

    secret_key: str = Field(min_length=16)
    access_token_expire_minutes: int = 60
    cookie_secure: bool = False

    # Початковий адміністратор (створюється при старті, якщо задано обидва поля)
    admin_email: str | None = None
    admin_password: str | None = None

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.app_env == "production":
            if self.debug:
                raise ValueError("DEBUG must be false in production")
            if self.secret_key.lower() in INSECURE_SECRETS:
                raise ValueError("SECRET_KEY must be changed in production")
        return self


@lru_cache
def get_settings() -> Settings:
    env = os.getenv("APP_ENV", "sandbox")
    return Settings(_env_file=f".env.{env}")
