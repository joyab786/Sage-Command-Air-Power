"""Core infrastructure module for Aero."""
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging, get_logger, bind_correlation_id
from app.core.exceptions import (
    AeroException,
    ConfigurationError,
    DatabaseError,
    NotFoundError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    PolicyViolationError,
    ExecutionGatewayError,
    ConcurrencyConflictError,
)

__all__ = [
    "Settings",
    "get_settings",
    "setup_logging",
    "get_logger",
    "bind_correlation_id",
    "AeroException",
    "ConfigurationError",
    "DatabaseError",
    "NotFoundError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "PolicyViolationError",
    "ExecutionGatewayError",
    "ConcurrencyConflictError",
]
