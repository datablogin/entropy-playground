"""Structured logging setup for Entropy-Playground."""

import logging
import os
import sys
from typing import Any, Dict

import structlog
from structlog.types import EventDict, Processor


def add_timestamp(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add timestamp to log events."""
    from datetime import datetime
    event_dict["timestamp"] = datetime.utcnow().isoformat()
    return event_dict


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
    )
    
    # Configure structlog
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        add_timestamp,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
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


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return structlog.get_logger(name)


# Initialize logging on module import
log_level = os.environ.get("LOG_LEVEL", "INFO")
setup_logging(log_level)