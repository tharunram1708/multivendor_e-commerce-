from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Multi Vendor E-Commerce API"
    debug: bool = False

    database_url: str = Field(
        default="mysql+pymysql://root:password@localhost:3306/multivendor_db",
        description="SQLAlchemy database URL",
    )

    secret_key: str = "change-this-secret-key-before-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    reset_token_expire_minutes: int = 20
    algorithm: str = "HS256"

    create_tables_on_startup: bool = False
    first_super_admin_email: str | None = None
    first_super_admin_password: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()

