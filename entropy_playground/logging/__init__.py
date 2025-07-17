"""
Logging and audit module for Entropy-Playground.

Provides:
- Structured logging with JSON format
- Audit trail functionality
- CloudWatch integration
- Log aggregation and search
- Performance metrics
"""

from entropy_playground.logging.aggregator import (
    LogAggregator,
    LogEntry,
    LogQuery,
    get_log_stats,
    search_logs,
)
from entropy_playground.logging.audit import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
    configure_audit_logger,
    get_audit_logger,
)
from entropy_playground.logging.cloudwatch import (
    CloudWatchHandler,
    CloudWatchLogger,
    configure_cloudwatch,
    get_cloudwatch_logger,
)
from entropy_playground.logging.logger import (
    LogContext,
    get_logger,
    setup_logging,
)

__all__ = [
    # Logger
    "setup_logging",
    "get_logger",
    "LogContext",
    # Audit
    "AuditEvent",
    "AuditEventType",
    "AuditLogger",
    "get_audit_logger",
    "configure_audit_logger",
    # CloudWatch
    "CloudWatchHandler",
    "CloudWatchLogger",
    "get_cloudwatch_logger",
    "configure_cloudwatch",
    # Aggregator
    "LogEntry",
    "LogQuery",
    "LogAggregator",
    "search_logs",
    "get_log_stats",
]

