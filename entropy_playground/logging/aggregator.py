"""Log aggregation and search capabilities."""

import json
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from entropy_playground.logging.logger import get_logger


@dataclass
class LogQuery:
    """Represents a log search query."""

    start_time: datetime | None = None
    end_time: datetime | None = None
    level: str | None = None
    component: str | None = None
    agent_id: str | None = None
    message_contains: str | None = None
    metadata_filters: dict[str, Any] = field(default_factory=dict)
    limit: int = 1000
    offset: int = 0


@dataclass
class LogEntry:
    """Represents a parsed log entry."""

    timestamp: datetime
    level: str
    component: str
    message: str
    agent_id: str | None = None
    agent_type: str | None = None
    agent_role: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    raw: str | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "LogEntry":
        """Create LogEntry from JSON data."""
        # Parse timestamp
        timestamp_str = data.get("timestamp", "")
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            timestamp = datetime.utcnow()

        # Extract agent info
        agent_info = data.get("agent", {})

        return cls(
            timestamp=timestamp,
            level=data.get("level", "INFO"),
            component=data.get("logger_name", "unknown"),
            message=data.get("event", data.get("message", "")),
            agent_id=agent_info.get("id"),
            agent_type=agent_info.get("type"),
            agent_role=agent_info.get("role"),
            metadata={
                k: v
                for k, v in data.items()
                if k not in ["timestamp", "level", "logger_name", "event", "message", "agent"]
            },
            raw=json.dumps(data),
        )


class LogAggregator:
    """Aggregates and searches logs from multiple sources."""

    def __init__(self, log_dirs: list[Path] | None = None) -> None:
        """Initialize log aggregator.

        Args:
            log_dirs: List of directories to search for logs
        """
        self.logger = get_logger(__name__)
        self.log_dirs = log_dirs or [Path("./logs")]

        # Ensure all directories exist
        for log_dir in self.log_dirs:
            log_dir.mkdir(parents=True, exist_ok=True)

    def search(self, query: LogQuery) -> list[LogEntry]:
        """Search logs based on query criteria.

        Args:
            query: Search query

        Returns:
            List of matching log entries
        """
        entries: list[LogEntry] = []

        # Set default time range if not specified
        if not query.start_time:
            query.start_time = datetime.utcnow() - timedelta(hours=24)
        if not query.end_time:
            query.end_time = datetime.utcnow()

        # Search through all log files
        for log_entry in self._iterate_logs(query.start_time, query.end_time):
            # Apply filters
            if not self._matches_query(log_entry, query):
                continue

            # Apply offset
            if query.offset > 0:
                query.offset -= 1
                continue

            entries.append(log_entry)

            # Apply limit
            if len(entries) >= query.limit:
                break

        return entries

    def _iterate_logs(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> Iterator[LogEntry]:
        """Iterate through log entries in time range.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Yields:
            Log entries
        """
        # Find all log files in the time range
        for log_dir in self.log_dirs:
            for log_file in sorted(log_dir.glob("*.log*")):
                # Skip files outside the time range based on modification time
                file_mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if file_mtime < start_time:
                    continue

                # Read and parse log file
                try:
                    with open(log_file, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue

                            try:
                                # Try to parse as JSON
                                data = json.loads(line)
                                entry = LogEntry.from_json(data)

                                # Check time range
                                if entry.timestamp < start_time:
                                    continue
                                if entry.timestamp > end_time:
                                    break

                                yield entry

                            except json.JSONDecodeError:
                                # Handle non-JSON log lines
                                # Try to extract basic info
                                parsed_entry = self._parse_text_log(line)
                                if (
                                    parsed_entry
                                    and start_time <= parsed_entry.timestamp <= end_time
                                ):
                                    yield parsed_entry

                except Exception as e:
                    self.logger.warning(f"Error reading log file {log_file}: {e}")

    def _parse_text_log(self, line: str) -> LogEntry | None:
        """Parse a text log line.

        Args:
            line: Log line

        Returns:
            Parsed log entry or None
        """
        # Basic parsing for non-JSON logs
        # This is a fallback for logs that aren't in JSON format
        try:
            # Try to extract timestamp, level, and message
            parts = line.split(maxsplit=3)
            if len(parts) < 3:
                return None

            # Attempt to parse timestamp
            timestamp_str = parts[0]
            if "T" in timestamp_str:  # ISO format
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            else:
                return None

            level = parts[1].upper()
            component = parts[2].strip("[]")
            message = parts[3] if len(parts) > 3 else ""

            return LogEntry(
                timestamp=timestamp,
                level=level,
                component=component,
                message=message,
                raw=line,
            )

        except (ValueError, IndexError):
            return None

    def _matches_query(self, entry: LogEntry, query: LogQuery) -> bool:
        """Check if log entry matches query criteria.

        Args:
            entry: Log entry
            query: Search query

        Returns:
            True if entry matches query
        """
        # Check level
        if query.level and entry.level != query.level.upper():
            return False

        # Check component
        if query.component and query.component not in entry.component:
            return False

        # Check agent ID
        if query.agent_id and entry.agent_id != query.agent_id:
            return False

        # Check message content
        if query.message_contains and query.message_contains.lower() not in entry.message.lower():
            return False

        # Check metadata filters
        for key, value in query.metadata_filters.items():
            if key not in entry.metadata or entry.metadata[key] != value:
                return False

        return True

    def aggregate_by_level(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, int]:
        """Aggregate log counts by level.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary of level -> count
        """
        counts: dict[str, int] = defaultdict(int)

        query = LogQuery(start_time=start_time, end_time=end_time)
        for entry in self._iterate_logs(
            query.start_time or datetime.utcnow() - timedelta(hours=24),
            query.end_time or datetime.utcnow(),
        ):
            counts[entry.level] += 1

        return dict(counts)

    def aggregate_by_component(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, int]:
        """Aggregate log counts by component.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary of component -> count
        """
        counts: dict[str, int] = defaultdict(int)

        query = LogQuery(start_time=start_time, end_time=end_time)
        for entry in self._iterate_logs(
            query.start_time or datetime.utcnow() - timedelta(hours=24),
            query.end_time or datetime.utcnow(),
        ):
            counts[entry.component] += 1

        return dict(counts)

    def aggregate_by_agent(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, dict[str, int]]:
        """Aggregate log counts by agent.

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            Dictionary of agent_id -> {level -> count}
        """
        agent_stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        query = LogQuery(start_time=start_time, end_time=end_time)
        for entry in self._iterate_logs(
            query.start_time or datetime.utcnow() - timedelta(hours=24),
            query.end_time or datetime.utcnow(),
        ):
            if entry.agent_id:
                agent_stats[entry.agent_id][entry.level] += 1

        return {k: dict(v) for k, v in agent_stats.items()}

    def get_error_summary(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> list[LogEntry]:
        """Get summary of error logs.

        Args:
            start_time: Start of time range
            end_time: End of time range
            limit: Maximum number of errors to return

        Returns:
            List of error log entries
        """
        query = LogQuery(
            start_time=start_time,
            end_time=end_time,
            level="ERROR",
            limit=limit,
        )
        return self.search(query)

    def tail(
        self,
        follow: bool = False,
        lines: int = 10,
        filter_func: Callable[[LogEntry], bool] | None = None,
    ) -> Iterator[LogEntry]:
        """Tail logs, optionally following new entries.

        Args:
            follow: Whether to follow new log entries
            lines: Number of recent lines to show initially
            filter_func: Optional filter function

        Yields:
            Log entries
        """
        # Get recent entries
        recent_entries = []
        for entry in self._iterate_logs(
            datetime.utcnow() - timedelta(hours=1),
            datetime.utcnow(),
        ):
            if filter_func and not filter_func(entry):
                continue
            recent_entries.append(entry)

        # Yield the last N entries
        for entry in recent_entries[-lines:]:
            yield entry

        if not follow:
            return

        # Follow new entries (simplified - in production would use inotify or similar)
        import time

        last_check = datetime.utcnow()

        while True:
            time.sleep(1)  # Check every second

            current_time = datetime.utcnow()
            for entry in self._iterate_logs(last_check, current_time):
                if filter_func and not filter_func(entry):
                    continue
                yield entry

            last_check = current_time


# Convenience functions
def search_logs(
    message_contains: str | None = None,
    level: str | None = None,
    component: str | None = None,
    hours: int = 24,
    limit: int = 100,
) -> list[LogEntry]:
    """Quick search for logs.

    Args:
        message_contains: Search string in messages
        level: Log level filter
        component: Component filter
        hours: Hours to look back
        limit: Maximum results

    Returns:
        List of matching log entries
    """
    aggregator = LogAggregator()
    query = LogQuery(
        start_time=datetime.utcnow() - timedelta(hours=hours),
        message_contains=message_contains,
        level=level,
        component=component,
        limit=limit,
    )
    return aggregator.search(query)


def get_log_stats(hours: int = 24) -> dict[str, Any]:
    """Get log statistics.

    Args:
        hours: Hours to analyze

    Returns:
        Dictionary of statistics
    """
    aggregator = LogAggregator()
    start_time = datetime.utcnow() - timedelta(hours=hours)

    return {
        "time_range": {
            "start": start_time.isoformat(),
            "end": datetime.utcnow().isoformat(),
        },
        "by_level": aggregator.aggregate_by_level(start_time),
        "by_component": aggregator.aggregate_by_component(start_time),
        "by_agent": aggregator.aggregate_by_agent(start_time),
        "recent_errors": [
            {
                "timestamp": e.timestamp.isoformat(),
                "component": e.component,
                "message": e.message,
            }
            for e in aggregator.get_error_summary(start_time, limit=10)
        ],
    }
