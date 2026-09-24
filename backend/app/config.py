from typing import List, Union, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
import os


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./wealthhub.db"
    JWT_SECRET: str = "wealthhub-dev-secret-key-do-not-use-in-prod-2026-secure"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    CORS_ORIGINS: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:3000",
        "https://wealthhub.antideploy.com",
    ]
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Groww API configuration
    GROWW_API_BASE_URL: str = "https://api.groww.in"
    GROWW_API_VERSION: str = "1.0"
    GROWW_TIMEOUT_SECONDS: float = 15.0

    # Setu Account Aggregator (AA) Sandbox configuration
    SETU_ENVIRONMENT: str = "mock"
    SETU_BASE_URL: str = "https://fiu-sandbox.setu.co"
    SETU_AUTH_URL: Optional[str] = None
    SETU_CLIENT_ID: Optional[str] = None
    SETU_CLIENT_SECRET: Optional[str] = None
    SETU_PRODUCT_INSTANCE_ID: Optional[str] = None
    SETU_TIMEOUT_SECONDS: float = 15.0
    SETU_LIVE_TEST: bool = False

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
