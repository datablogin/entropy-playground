"""Tests for the logging framework."""

import json
import os
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import structlog

from entropy_playground.logging.logger import (
    setup_logging,
    get_logger,
    LogContext,
    add_timestamp,
    add_request_context,
    add_agent_metadata,
)
from entropy_playground.logging.audit import (
    AuditEvent,
    AuditEventType,
    AuditLogger,
    get_audit_logger,
    configure_audit_logger,
)
from entropy_playground.logging.aggregator import (
    LogEntry,
    LogQuery,
    LogAggregator,
    search_logs,
    get_log_stats,
)


class TestStructuredLogging:
    """Test structured logging functionality."""
    
    def test_setup_logging_console_only(self, monkeypatch):
        """Test logging setup without file logging."""
        monkeypatch.setenv("ENTROPY_ENV", "development")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(
                level="DEBUG",
                log_dir=temp_dir,
                enable_file_logging=False,
            )
            
            logger = get_logger("test")
            logger.info("test message", key="value")
            
            # Verify no log files were created
            log_files = list(Path(temp_dir).glob("*.log"))
            assert len(log_files) == 0
    
    def test_setup_logging_with_file(self):
        """Test logging setup with file logging."""
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(
                level="INFO",
                log_dir=temp_dir,
                enable_file_logging=True,
            )
            
            logger = get_logger("test")
            logger.info("test message", key="value")
            
            # Verify log file was created
            log_file = Path(temp_dir) / "entropy-playground.log"
            assert log_file.exists()
            
            # Verify log content
            with open(log_file, "r") as f:
                content = f.read()
                assert "test message" in content
                assert "key" in content
    
    def test_json_formatting_in_production(self, monkeypatch):
        """Test JSON formatting in production mode."""
        monkeypatch.setenv("ENTROPY_ENV", "production")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            setup_logging(log_dir=temp_dir)
            
            logger = get_logger("test")
            logger.info("test message", number=42, flag=True)
            
            # Read and parse log file
            log_file = Path(temp_dir) / "entropy-playground.log"
            with open(log_file, "r") as f:
                line = f.readline()
                data = json.loads(line)
                
                assert data["event"] == "test message"
                assert data["number"] == 42
                assert data["flag"] is True
                assert "timestamp" in data
                assert "logger" in data
    
    def test_log_rotation(self):
        """Test log file rotation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Setup logging with small max bytes to trigger rotation
            setup_logging(
                log_dir=temp_dir,
                enable_file_logging=True,
            )
            
            # Get the root logger and add our small rotation handler
            import logging
            from entropy_playground.logging.logger import setup_file_handler
            
            handler = setup_file_handler(
                Path(temp_dir),
                max_bytes=100,  # Very small to trigger rotation
                backup_count=2,
            )
            root_logger = logging.getLogger()
            root_logger.addHandler(handler)
            
            # Write enough to trigger rotation
            logger = get_logger("test")
            for i in range(20):
                logger.info(f"Message {i}" * 10)  # Long messages
            
            # Force handler to flush
            handler.flush()
            
            # Check that backup files were created
            log_files = list(Path(temp_dir).glob("entropy-playground.log*"))
            assert len(log_files) > 1
    
    def test_logger_with_context(self):
        """Test logger with bound context."""
        logger = get_logger("test", agent_id="agent-123", task_id="task-456")
        
        # Context should be included in all log messages
        with patch("structlog.get_logger") as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            mock_logger.bind.return_value = mock_logger
            
            logger = get_logger("test", agent_id="agent-123")
            mock_logger.bind.assert_called_with(agent_id="agent-123")
    
    def test_log_context_manager(self):
        """Test LogContext context manager."""
        logger = get_logger("test")
        
        with LogContext(logger, request_id="req-123", user="alice") as ctx_logger:
            # Inside context, logger should have additional fields
            assert ctx_logger == logger.bind(request_id="req-123", user="alice")
    
    def test_custom_processors(self):
        """Test custom log processors."""
        # Test timestamp processor
        event_dict = {}
        result = add_timestamp(None, None, event_dict)
        assert "timestamp" in result
        assert isinstance(result["timestamp"], str)
        
        # Test agent metadata processor
        event_dict = {
            "agent_id": "agent-123",
            "agent_type": "coder",
            "agent_role": "developer",
        }
        result = add_agent_metadata(None, None, event_dict)
        assert "agent" in result
        assert result["agent"]["id"] == "agent-123"
        assert result["agent"]["type"] == "coder"
        assert result["agent"]["role"] == "developer"
        assert "agent_id" not in result


class TestAuditLogging:
    """Test audit logging functionality."""
    
    def test_audit_event_creation(self):
        """Test creating audit events."""
        event = AuditEvent(
            event_type=AuditEventType.AGENT_STARTED,
            actor_id="agent-123",
            actor_type="agent",
            action="Agent started",
            metadata={"version": "1.0"},
        )
        
        assert event.id is not None
        assert event.timestamp is not None
        assert event.outcome == "success"
        assert event.metadata["version"] == "1.0"
    
    def test_audit_logger_initialization(self):
        """Test audit logger initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_logger = AuditLogger(
                log_dir=Path(temp_dir),
                enable_file_logging=True,
            )
            
            # Verify audit directory was created
            audit_dir = Path(temp_dir)
            assert audit_dir.exists()
    
    def test_audit_logger_file_writing(self):
        """Test writing audit events to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_logger = AuditLogger(log_dir=Path(temp_dir))
            
            # Log an event
            event = AuditEvent(
                event_type=AuditEventType.GITHUB_PR_CREATED,
                actor_id="agent-123",
                actor_type="agent",
                resource_type="pull_request",
                resource_id="PR-456",
                action="Created pull request",
            )
            audit_logger.log_event(event)
            
            # Verify file was created with correct name
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            audit_file = Path(temp_dir) / f"audit-{date_str}.jsonl"
            assert audit_file.exists()
            
            # Verify content
            with open(audit_file, "r") as f:
                line = f.readline()
                data = json.loads(line)
                assert data["id"] == event.id
                assert data["event_type"] == "github.pr.created"
                assert data["actor_id"] == "agent-123"
    
    def test_audit_logger_convenience_methods(self):
        """Test audit logger convenience methods."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_logger = AuditLogger(log_dir=Path(temp_dir))
            
            # Test agent start
            audit_logger.log_agent_start(
                agent_id="agent-123",
                agent_type="coder",
                metadata={"version": "1.0"},
            )
            
            # Test GitHub operation
            audit_logger.log_github_operation(
                event_type=AuditEventType.GITHUB_ISSUE_READ,
                actor_id="agent-123",
                resource_type="issue",
                resource_id="123",
                action="Read issue #123",
                metadata={"labels": ["bug", "urgent"]},
            )
            
            # Test task event
            audit_logger.log_task_event(
                event_type=AuditEventType.TASK_COMPLETED,
                actor_id="agent-123",
                task_id="task-456",
                action="Completed code review task",
                metadata={"duration": 300},
            )
            
            # Verify all events were logged
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            audit_file = Path(temp_dir) / f"audit-{date_str}.jsonl"
            with open(audit_file, "r") as f:
                lines = f.readlines()
                assert len(lines) == 3
    
    def test_audit_event_search(self):
        """Test searching audit events."""
        with tempfile.TemporaryDirectory() as temp_dir:
            audit_logger = AuditLogger(log_dir=Path(temp_dir))
            
            # Log various events
            for i in range(5):
                audit_logger.log_agent_start(
                    agent_id=f"agent-{i}",
                    agent_type="coder",
                )
            
            audit_logger.log_github_operation(
                event_type=AuditEventType.GITHUB_PR_CREATED,
                actor_id="agent-0",
                resource_type="pull_request",
                resource_id="PR-123",
                action="Created PR",
                outcome="failure",
                error_details="Permission denied",
            )
            
            # Search by event type
            events = audit_logger.search_events(
                event_type=AuditEventType.AGENT_STARTED
            )
            assert len(events) == 5
            
            # Search by actor
            events = audit_logger.search_events(actor_id="agent-0")
            assert len(events) == 2
            
            # Search by outcome
            events = audit_logger.search_events(outcome="failure")
            assert len(events) == 1
            assert events[0].error_details == "Permission denied"
    
    def test_global_audit_logger(self):
        """Test global audit logger functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            configure_audit_logger(log_dir=Path(temp_dir))
            
            logger = get_audit_logger()
            assert logger is not None
            
            # Log an event
            logger.log_agent_start("agent-123", "coder")
            
            # Verify it was logged
            date_str = datetime.utcnow().strftime("%Y-%m-%d")
            audit_file = Path(temp_dir) / f"audit-{date_str}.jsonl"
            assert audit_file.exists()


class TestLogAggregation:
    """Test log aggregation and search functionality."""
    
    def test_log_entry_parsing(self):
        """Test parsing log entries from JSON."""
        json_data = {
            "timestamp": "2024-01-15T10:30:00",
            "level": "INFO",
            "logger_name": "test.component",
            "event": "Test message",
            "agent": {
                "id": "agent-123",
                "type": "coder",
                "role": "developer",
            },
            "custom_field": "value",
        }
        
        entry = LogEntry.from_json(json_data)
        assert entry.timestamp.year == 2024
        assert entry.level == "INFO"
        assert entry.component == "test.component"
        assert entry.message == "Test message"
        assert entry.agent_id == "agent-123"
        assert entry.agent_type == "coder"
        assert entry.metadata["custom_field"] == "value"
    
    def test_log_aggregator_search(self):
        """Test searching logs with aggregator."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            log_file = log_dir / "test.log"
            
            # Write test logs
            logs = [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "logger_name": "agent.coder",
                    "event": "Starting task",
                    "agent": {"id": "agent-1"},
                },
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "ERROR",
                    "logger_name": "agent.reviewer",
                    "event": "Review failed",
                    "agent": {"id": "agent-2"},
                },
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "logger_name": "agent.coder",
                    "event": "Task completed",
                    "agent": {"id": "agent-1"},
                },
            ]
            
            with open(log_file, "w") as f:
                for log in logs:
                    f.write(json.dumps(log) + "\n")
            
            aggregator = LogAggregator([log_dir])
            
            # Search by level
            query = LogQuery(level="ERROR")
            results = aggregator.search(query)
            assert len(results) == 1
            assert results[0].message == "Review failed"
            
            # Search by component
            query = LogQuery(component="coder")
            results = aggregator.search(query)
            assert len(results) == 2
            
            # Search by message content
            query = LogQuery(message_contains="task")
            results = aggregator.search(query)
            assert len(results) == 2
    
    def test_log_aggregation_by_level(self):
        """Test aggregating logs by level."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            log_file = log_dir / "test.log"
            
            # Write logs with different levels
            levels = ["INFO", "INFO", "WARNING", "ERROR", "INFO", "ERROR"]
            with open(log_file, "w") as f:
                for level in levels:
                    log = {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": level,
                        "logger_name": "test",
                        "event": f"{level} message",
                    }
                    f.write(json.dumps(log) + "\n")
            
            aggregator = LogAggregator([log_dir])
            stats = aggregator.aggregate_by_level()
            
            assert stats["INFO"] == 3
            assert stats["WARNING"] == 1
            assert stats["ERROR"] == 2
    
    def test_log_aggregation_by_agent(self):
        """Test aggregating logs by agent."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            log_file = log_dir / "test.log"
            
            # Write logs from different agents
            with open(log_file, "w") as f:
                for i in range(3):
                    for level in ["INFO", "ERROR"]:
                        log = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "level": level,
                            "logger_name": "test",
                            "event": f"Message from agent-{i}",
                            "agent": {"id": f"agent-{i}"},
                        }
                        f.write(json.dumps(log) + "\n")
            
            aggregator = LogAggregator([log_dir])
            stats = aggregator.aggregate_by_agent()
            
            assert len(stats) == 3
            assert stats["agent-0"]["INFO"] == 1
            assert stats["agent-0"]["ERROR"] == 1
    
    def test_convenience_functions(self):
        """Test convenience search functions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = Path(temp_dir)
            log_file = log_dir / "test.log"
            
            # Write a test log
            log = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "ERROR",
                "logger_name": "test.component",
                "event": "Test error message",
            }
            with open(log_file, "w") as f:
                f.write(json.dumps(log) + "\n")
            
            # Patch the default log directory
            with patch("entropy_playground.logging.aggregator.LogAggregator") as mock_agg:
                mock_instance = LogAggregator([log_dir])
                mock_agg.return_value = mock_instance
                
                # Test search_logs
                results = search_logs(
                    message_contains="error",
                    level="ERROR",
                )
                assert len(results) > 0
                
                # Test get_log_stats
                stats = get_log_stats(hours=1)
                assert "by_level" in stats
                assert "by_component" in stats
                assert "recent_errors" in stats