"""
SageCommand Air Power System (Aero) — Exception Hierarchy.
Provides domain-neutral, standardized exception types with machine-readable error codes.
"""

from typing import Optional, Dict, Any, List


class AeroException(Exception):
    """Base exception for all Aero application errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "AERO_ERROR",
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}


class ConfigurationError(AeroException):
    """Raised when application configuration is invalid or missing."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            status_code=500,
            details=details,
        )


class DatabaseError(AeroException):
    """Raised when a database connection or query execution fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details,
        )


class NotFoundError(AeroException):
    """Raised when a requested resource does not exist."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details=details,
        )


class ValidationError(AeroException):
    """Raised when data contracts or domain invariants fail validation."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_FAILED",
            status_code=422,
            details=details,
        )


class AuthenticationError(AeroException):
    """Raised when identity authentication fails or is missing."""

    def __init__(self, message: str = "Authentication required", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="UNAUTHENTICATED",
            status_code=401,
            details=details,
        )


class AuthorizationError(AeroException):
    """Raised when an authenticated caller lacks required operational permissions."""

    def __init__(self, message: str = "Operation not permitted", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="PERMISSION_DENIED",
            status_code=403,
            details=details,
        )


class PolicyViolationError(AeroException):
    """Raised when an operation violates active policy engine rules."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="POLICY_VIOLATION",
            status_code=403,
            details=details,
        )


class ExecutionGatewayError(AeroException):
    """Raised when an action fails deterministic execution gateway verification."""

    def __init__(
        self,
        message: str,
        error_code: str = "GATEWAY_EXECUTION_FAILED",
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status_code,
            details=details,
        )


class ConcurrencyConflictError(AeroException):
    """Raised when a concurrent execution conflict or lock contention occurs."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONCURRENCY_CONFLICT",
            status_code=409,
            details=details,
        )


class ConflictError(AeroException):
    """Raised when an operation conflicts with the current resource state."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFLICT",
            status_code=409,
            details=details,
        )

