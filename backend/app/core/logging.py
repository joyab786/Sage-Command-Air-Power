"""
SageCommand Air Power System (Aero) — Structured Logging Framework.
Provides asynchronous-safe context correlation, UTC ISO timestamps, and structured JSON formatting.
"""

import sys
import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Optional, Any, Dict
from app.core.config import Settings, get_settings

# Correlation ID context variable for distributed request tracking
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="")


def get_correlation_id() -> str:
    """Retrieves current correlation ID from context."""
    return correlation_id_ctx.get()


def bind_correlation_id(correlation_id: str) -> None:
    """Binds correlation ID to current execution context."""
    correlation_id_ctx.set(correlation_id)


class JsonLogFormatter(logging.Formatter):
    """Encodes log records into deterministic, structured JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }

        # Include correlation ID if present
        cid = get_correlation_id()
        if cid:
            log_payload["correlation_id"] = cid

        # Include structured extra fields if supplied
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_payload.update(record.extra)

        # Include exception traceback if present
        if record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload, default=str)


class ConsoleLogFormatter(logging.Formatter):
    """Human-readable console log formatter for development debugging."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        cid = get_correlation_id()
        cid_str = f" [{cid[:8]}]" if cid else ""
        msg = record.getMessage()

        base = f"[{timestamp}] [{record.levelname:<8}] [{record.name}]{cid_str}: {msg}"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def setup_logging(settings: Optional[Settings] = None) -> None:
    """Configures root logger with Aero structured formatters and level."""
    resolved_settings = settings or get_settings()
    log_level = getattr(logging, resolved_settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplication
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)

    if resolved_settings.LOG_FORMAT.lower() == "json":
        stream_handler.setFormatter(JsonLogFormatter())
    else:
        stream_handler.setFormatter(ConsoleLogFormatter())

    root_logger.addHandler(stream_handler)

    # Quiet overly chatty third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Returns configured logger instance for a given module."""
    return logging.getLogger(name)
