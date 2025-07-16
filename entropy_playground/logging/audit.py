"""Audit trail functionality for tracking agent actions and system events."""

import json
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from entropy_playground.logging.logger import get_logger


class AuditEventType(str, Enum):
    """Types of audit events."""

    # Agent lifecycle events
    AGENT_STARTED = "agent.started"
    AGENT_STOPPED = "agent.stopped"
    AGENT_ERROR = "agent.error"

    # GitHub operations
    GITHUB_ISSUE_READ = "github.issue.read"
    GITHUB_PR_CREATED = "github.pr.created"
    GITHUB_PR_REVIEWED = "github.pr.reviewed"
    GITHUB_COMMENT_POSTED = "github.comment.posted"
    GITHUB_CODE_PUSHED = "github.code.pushed"

    # Task operations
    TASK_ASSIGNED = "task.assigned"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_CONFIG_CHANGED = "system.config.changed"

    # Security events
    AUTH_SUCCESS = "auth.success"
    AUTH_FAILURE = "auth.failure"
    PERMISSION_DENIED = "permission.denied"


class AuditEvent(BaseModel):
    """Represents an audit event."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: AuditEventType
    actor_id: str  # Agent ID or system component
    actor_type: str  # e.g., "agent", "system", "user"
    resource_type: str | None = None  # e.g., "issue", "pull_request"
    resource_id: str | None = None  # e.g., issue number, PR ID
    action: str  # Specific action performed
    outcome: str = "success"  # "success", "failure", "error"
    metadata: dict[str, Any] = Field(default_factory=dict)
    error_details: str | None = None

    model_config = ConfigDict()


class AuditLogger:
    """Handles audit logging for the system."""

    def __init__(
        self,
        log_dir: Path | None = None,
        enable_file_logging: bool = True,
    ) -> None:
        """Initialize audit logger.

        Args:
            log_dir: Directory for audit logs
            enable_file_logging: Whether to write audit logs to files
        """
        self.logger = get_logger(__name__)
        self.enable_file_logging = enable_file_logging

        if self.enable_file_logging:
            self.log_dir = log_dir or Path("./logs/audit")
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.current_log_file = self._get_log_file_path()

    def _get_log_file_path(self) -> Path:
        """Get the current audit log file path."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return self.log_dir / f"audit-{date_str}.jsonl"

    def log_event(self, event: AuditEvent) -> None:
        """Log an audit event.

        Args:
            event: The audit event to log
        """
        # Log to structured logger
        self.logger.info(
            "audit_event",
            event_id=event.id,
            event_type=event.event_type,
            actor_id=event.actor_id,
            actor_type=event.actor_type,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            action=event.action,
            outcome=event.outcome,
            metadata=event.metadata,
            error_details=event.error_details,
        )

        # Write to audit log file
        if self.enable_file_logging:
            self._write_to_file(event)

    def _write_to_file(self, event: AuditEvent) -> None:
        """Write event to audit log file."""
        # Check if we need to rotate to a new file
        current_file = self._get_log_file_path()
        if current_file != self.current_log_file:
            self.current_log_file = current_file

        # Append event as JSON line
        with open(self.current_log_file, "a", encoding="utf-8") as f:
            f.write(event.model_dump_json() + "\n")

    def log_agent_start(
        self,
        agent_id: str,
        agent_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log agent startup."""
        event = AuditEvent(
            event_type=AuditEventType.AGENT_STARTED,
            actor_id=agent_id,
            actor_type="agent",
            action=f"Agent {agent_type} started",
            metadata=metadata or {},
        )
        self.log_event(event)

    def log_agent_stop(
        self,
        agent_id: str,
        agent_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log agent shutdown."""
        event = AuditEvent(
            event_type=AuditEventType.AGENT_STOPPED,
            actor_id=agent_id,
            actor_type="agent",
            action=f"Agent {agent_type} stopped",
            metadata=metadata or {},
        )
        self.log_event(event)

    def log_github_operation(
        self,
        event_type: AuditEventType,
        actor_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        outcome: str = "success",
        metadata: dict[str, Any] | None = None,
        error_details: str | None = None,
    ) -> None:
        """Log GitHub operation."""
        event = AuditEvent(
            event_type=event_type,
            actor_id=actor_id,
            actor_type="agent",
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome=outcome,
            metadata=metadata or {},
            error_details=error_details,
        )
        self.log_event(event)

    def log_task_event(
        self,
        event_type: AuditEventType,
        actor_id: str,
        task_id: str,
        action: str,
        outcome: str = "success",
        metadata: dict[str, Any] | None = None,
        error_details: str | None = None,
    ) -> None:
        """Log task-related event."""
        event = AuditEvent(
            event_type=event_type,
            actor_id=actor_id,
            actor_type="agent",
            resource_type="task",
            resource_id=task_id,
            action=action,
            outcome=outcome,
            metadata=metadata or {},
            error_details=error_details,
        )
        self.log_event(event)

    def search_events(
        self,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        event_type: AuditEventType | None = None,
        actor_id: str | None = None,
        resource_id: str | None = None,
        outcome: str | None = None,
    ) -> list[AuditEvent]:
        """Search audit events based on criteria.

        Args:
            start_date: Start of date range
            end_date: End of date range
            event_type: Filter by event type
            actor_id: Filter by actor ID
            resource_id: Filter by resource ID
            outcome: Filter by outcome

        Returns:
            List of matching audit events
        """
        events: list[AuditEvent] = []

        # Default date range if not specified
        if not start_date:
            start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        if not end_date:
            end_date = datetime.utcnow()

        # Read audit files for date range
        current_date = start_date
        while current_date <= end_date:
            file_path = self.log_dir / f"audit-{current_date.strftime('%Y-%m-%d')}.jsonl"
            if file_path.exists():
                with open(file_path, encoding="utf-8") as f:
                    for line in f:
                        try:
                            event_data = json.loads(line.strip())
                            event = AuditEvent(**event_data)

                            # Apply filters
                            if event_type and event.event_type != event_type:
                                continue
                            if actor_id and event.actor_id != actor_id:
                                continue
                            if resource_id and event.resource_id != resource_id:
                                continue
                            if outcome and event.outcome != outcome:
                                continue

                            events.append(event)
                        except (json.JSONDecodeError, ValueError) as e:
                            self.logger.warning(
                                "Failed to parse audit event",
                                error=str(e),
                                line=line,
                            )

            # Move to next day
            current_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
            current_date += timedelta(days=1)

        return events


# Global audit logger instance
_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger


def configure_audit_logger(
    log_dir: Path | None = None,
    enable_file_logging: bool = True,
) -> None:
    """Configure the global audit logger.

    Args:
        log_dir: Directory for audit logs
        enable_file_logging: Whether to write audit logs to files
    """
    global _audit_logger
    _audit_logger = AuditLogger(log_dir, enable_file_logging)

