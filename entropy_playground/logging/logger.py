"""Structured logging setup for Entropy-Playground."""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog
from structlog.types import EventDict, Processor


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add timestamp to log events."""
    event_dict["timestamp"] = datetime.utcnow().isoformat()
    return event_dict


def add_request_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add request context to log events."""
    # Add context from bound logger if available
    if hasattr(logger, "_context") and hasattr(logger._context, "_global_context"):
        context = getattr(logger._context, "_global_context", {})
        if context:
            event_dict["context"] = context
    return event_dict


def add_agent_metadata(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add agent metadata to log events."""
    # Add agent-specific metadata
    if "agent_id" in event_dict:
        event_dict["agent"] = {
            "id": event_dict.pop("agent_id"),
            "type": event_dict.pop("agent_type", "unknown"),
            "role": event_dict.pop("agent_role", "unknown"),
        }
    return event_dict


def setup_file_handler(
    log_dir: Path,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> logging.Handler:
    """Set up rotating file handler.

    Args:
        log_dir: Directory for log files
        max_bytes: Maximum size of each log file
        backup_count: Number of backup files to keep

    Returns:
        Configured file handler
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "entropy-playground.log"

    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )

    # Use JSON formatter for file logs
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)

    return handler


def setup_logging(
    level: str = "INFO",
    log_dir: str | None = None,
    enable_file_logging: bool = True,
) -> None:
    """Configure structured logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files (defaults to ./logs)
        enable_file_logging: Whether to enable file logging
    """
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    root_logger.addHandler(console_handler)

    # Add file handler if enabled
    if enable_file_logging:
        if log_dir is None:
            log_dir = os.environ.get("ENTROPY_LOG_DIR", "./logs")
        file_handler = setup_file_handler(Path(log_dir))
        root_logger.addHandler(file_handler)

    # Configure structlog
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        add_timestamp,
        add_request_context,
        add_agent_metadata,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.FUNC_NAME,
            ]
        ),
    ]

    # Use JSON renderer in production, console renderer for development
    if os.environ.get("ENTROPY_ENV") == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str, **context: Any) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)
        **context: Additional context to bind to the logger

    Returns:
        Configured logger instance
    """
    logger = structlog.get_logger(name)
    if context:
        logger = logger.bind(**context)
    return logger


class LogContext:
    """Context manager for adding temporary logging context."""

    def __init__(self, logger: structlog.stdlib.BoundLogger, **context: Any) -> None:
        self.logger = logger
        self.context = context
        self.previous_context: dict[str, Any] = {}

    def __enter__(self) -> structlog.stdlib.BoundLogger:
        # Save current context
        for key in self.context:
            if hasattr(self.logger._context, key):
                self.previous_context[key] = getattr(self.logger._context, key)

        # Bind new context
        return self.logger.bind(**self.context)

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # Restore previous context
        for key in self.context:
            if key in self.previous_context:
                self.logger._context[key] = self.previous_context[key]
            else:
                self.logger._context.pop(key, None)


# Initialize logging on module import
log_level = os.environ.get("LOG_LEVEL", "INFO")
setup_logging(log_level)
