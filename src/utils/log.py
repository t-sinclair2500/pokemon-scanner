"""Logging configuration using structlog."""

import logging
import sys
import time
from typing import Any, Dict, Optional

import structlog

from .config import settings


def configure_logging():
    """Configure structured logging with JSON renderer."""

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    if not structlog.is_configured():
        configure_logging()

    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capability to any class."""

    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger for this class."""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger

    def log_start(self, event: str, **kwargs: Any) -> Dict[str, Any]:
        """Log start of operation with context and timing."""
        context = {"event": event, "start_time": time.time(), **kwargs}
        # Remove event from context to avoid duplicate parameter
        log_context = {k: v for k, v in context.items() if k != "event"}
        self.logger.info(f"{event} started", **log_context)
        return context

    def log_success(self, context: Dict[str, Any], **kwargs: Any):
        """Log successful operation completion with duration."""
        if "start_time" in context:
            duration_ms = int((time.time() - context["start_time"]) * 1000)
            kwargs["duration_ms"] = duration_ms

        # Remove event from context to avoid duplicate parameter
        log_context = {k: v for k, v in context.items() if k != "event"}
        self.logger.info(
            f"{context.get('event', 'operation')} completed", **log_context, **kwargs
        )

    def log_error(self, context: Dict[str, Any], error: Exception, **kwargs: Any):
        """Log operation error with duration."""
        if "start_time" in context:
            duration_ms = int((time.time() - context["start_time"]) * 1000)
            kwargs["duration_ms"] = duration_ms

        # Remove event from context to avoid duplicate parameter
        log_context = {k: v for k, v in context.items() if k != "event"}
        self.logger.error(
            f"{context.get('event', 'operation')} failed",
            **log_context,
            error=str(error),
            error_type=type(error).__name__,
            **kwargs,
        )
