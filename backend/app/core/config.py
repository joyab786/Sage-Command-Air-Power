"""
SageCommand Air Power System (Aero) — Configuration System.
Provides type-safe, environment-variable-backed application settings.
"""

import json
from functools import lru_cache
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Authoritative Aero application settings."""

    model_config = SettingsConfigDict(
        env_prefix="AERO_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application Info
    APP_NAME: str = Field(
        default="SageCommand Air Power System — Aero",
        description="Canonical application name",
    )
    APP_VERSION: str = Field(
        default="0.1.0",
        description="SemVer application version",
    )
    ENV: str = Field(
        default="development",
        description="Runtime environment: development | testing | production",
    )
    DEBUG: bool = Field(
        default=False,
        description="Enable debug mode and verbose diagnostic output",
    )

    # Server Network Bindings
    API_HOST: str = Field(
        default="0.0.0.0",
        description="Host interface for API server binding",
    )
    API_PORT: int = Field(
        default=8000,
        ge=1,
        le=65535,
        description="TCP port for API server binding",
    )
    API_PREFIX: str = Field(
        default="/api/v1",
        description="API route prefix for versioned endpoints",
    )

    # Database Configuration
    DATABASE_URL: str = Field(
        default="sqlite:///./aero_datacore.sqlite",
        description="SQLAlchemy database connection URL",
    )
    DATABASE_ECHO: bool = Field(
        default=False,
        description="Echo SQL statements to standard logger",
    )
    DATABASE_WAL_MODE: bool = Field(
        default=True,
        description="Enable Write-Ahead Logging (WAL) for high-concurrency SQLite telemetry",
    )
    DATABASE_BUSY_TIMEOUT_MS: int = Field(
        default=5000,
        ge=500,
        description="SQLite busy timeout in milliseconds to prevent lock contention",
    )

    # Structured Logging
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level: DEBUG | INFO | WARNING | ERROR | CRITICAL",
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="Logging output format: json | console",
    )

    # CORS Allowlist
    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="Permitted CORS origins",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[List[str], str]) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @property
    def is_production(self) -> bool:
        return self.ENV.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.ENV.lower() == "testing"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Returns singleton cached instance of Aero application settings."""
    return Settings()
