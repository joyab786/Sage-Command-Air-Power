"""Unit tests for Aero configuration loading."""

import os
from app.core.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.APP_NAME == "SageCommand Air Power System — Aero"
    assert settings.APP_VERSION == "0.1.0"
    assert settings.ENV == "development"
    assert not settings.is_production
    assert not settings.is_testing
    assert "sqlite" in settings.DATABASE_URL
    assert settings.DATABASE_WAL_MODE is True


def test_custom_settings_override():
    settings = Settings(
        APP_NAME="Custom Aero",
        ENV="production",
        DATABASE_URL="sqlite:///./prod.sqlite",
        DATABASE_WAL_MODE=True,
    )
    assert settings.APP_NAME == "Custom Aero"
    assert settings.is_production is True
    assert settings.is_testing is False
    assert settings.DATABASE_URL == "sqlite:///./prod.sqlite"


def test_cors_origins_parsing():
    settings_str = Settings(CORS_ORIGINS="http://localhost:3000, https://aero.command.mil")
    assert "http://localhost:3000" in settings_str.CORS_ORIGINS
    assert "https://aero.command.mil" in settings_str.CORS_ORIGINS

    settings_json = Settings(CORS_ORIGINS='["http://domain1.com", "http://domain2.com"]')
    assert settings_json.CORS_ORIGINS == ["http://domain1.com", "http://domain2.com"]
