"""CloudWatch Logs integration for centralized logging."""

import json
import os
import time
from datetime import datetime
from queue import Empty, Queue
from threading import Event, Thread
from typing import Any

import boto3
from botocore.exceptions import ClientError

from entropy_playground.logging.logger import get_logger


class CloudWatchHandler:
    """Handler for sending logs to AWS CloudWatch."""

    def __init__(
        self,
        log_group_name: str,
        log_stream_name: str | None = None,
        region_name: str | None = None,
        buffer_size: int = 100,
        flush_interval: float = 5.0,
    ) -> None:
        """Initialize CloudWatch handler.

        Args:
            log_group_name: CloudWatch log group name
            log_stream_name: CloudWatch log stream name (auto-generated if None)
            region_name: AWS region (uses default if None)
            buffer_size: Number of logs to buffer before sending
            flush_interval: Seconds between automatic flushes
        """
        self.logger = get_logger(__name__)
        self.log_group_name = log_group_name
        self.log_stream_name = log_stream_name or self._generate_stream_name()
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval

        # Initialize CloudWatch client
        self.region_name = region_name or os.environ.get("AWS_REGION", "us-east-1")
        self.client = boto3.client("logs", region_name=self.region_name)

        # Create log group and stream if they don't exist
        self._ensure_log_group_exists()
        self._ensure_log_stream_exists()

        # Initialize buffer and worker thread
        self.buffer: Queue[dict[str, Any]] = Queue()
        self.sequence_token: str | None = None
        self.stop_event = Event()
        self.worker_thread = Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

        self.logger.info(
            "CloudWatch handler initialized",
            log_group=self.log_group_name,
            log_stream=self.log_stream_name,
        )

    def _generate_stream_name(self) -> str:
        """Generate a unique log stream name."""
        hostname = os.environ.get("HOSTNAME", "unknown")
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"entropy-playground/{hostname}/{timestamp}"

    def _ensure_log_group_exists(self) -> None:
        """Create log group if it doesn't exist."""
        try:
            self.client.create_log_group(logGroupName=self.log_group_name)
            self.logger.info(f"Created log group: {self.log_group_name}")
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceAlreadyExistsException":
                self.logger.error(f"Error creating log group: {e}")
                raise

    def _ensure_log_stream_exists(self) -> None:
        """Create log stream if it doesn't exist."""
        try:
            self.client.create_log_stream(
                logGroupName=self.log_group_name,
                logStreamName=self.log_stream_name,
            )
            self.logger.info(f"Created log stream: {self.log_stream_name}")
        except ClientError as e:
            if e.response["Error"]["Code"] != "ResourceAlreadyExistsException":
                self.logger.error(f"Error creating log stream: {e}")
                raise

    def emit(self, record: dict[str, Any]) -> None:
        """Add a log record to the buffer.

        Args:
            record: Log record to send
        """
        # Add timestamp if not present
        if "timestamp" not in record:
            record["timestamp"] = datetime.utcnow().isoformat()

        self.buffer.put(record)

    def _worker(self) -> None:
        """Worker thread that sends buffered logs to CloudWatch."""
        logs_to_send: list[dict[str, Any]] = []
        last_flush = time.time()

        while not self.stop_event.is_set():
            try:
                # Collect logs from buffer
                timeout = max(0.1, self.flush_interval - (time.time() - last_flush))

                try:
                    log = self.buffer.get(timeout=timeout)
                    logs_to_send.append(log)

                    # Collect more logs if available
                    while len(logs_to_send) < self.buffer_size and not self.buffer.empty():
                        logs_to_send.append(self.buffer.get_nowait())
                except Empty:
                    pass

                # Send logs if buffer is full or flush interval reached
                should_flush = (
                    len(logs_to_send) >= self.buffer_size or
                    (time.time() - last_flush) >= self.flush_interval
                )

                if should_flush and logs_to_send:
                    self._send_logs(logs_to_send)
                    logs_to_send.clear()
                    last_flush = time.time()

            except Exception as e:
                self.logger.error(f"Error in CloudWatch worker: {e}")
                time.sleep(1)  # Back off on error

        # Flush remaining logs on shutdown
        if logs_to_send:
            self._send_logs(logs_to_send)

    def _send_logs(self, logs: list[dict[str, Any]]) -> None:
        """Send logs to CloudWatch.

        Args:
            logs: List of log records to send
        """
        if not logs:
            return

        # Convert logs to CloudWatch format
        log_events = []
        for log in logs:
            # Extract timestamp
            timestamp_str = log.get("timestamp", datetime.utcnow().isoformat())
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.utcnow()

            # Convert to milliseconds since epoch
            timestamp_ms = int(timestamp.timestamp() * 1000)

            # Convert log to JSON string
            message = json.dumps(log, default=str)

            log_events.append({
                "timestamp": timestamp_ms,
                "message": message,
            })

        # Sort by timestamp (CloudWatch requirement)
        log_events.sort(key=lambda x: x["timestamp"])

        # Send to CloudWatch
        try:
            kwargs = {
                "logGroupName": self.log_group_name,
                "logStreamName": self.log_stream_name,
                "logEvents": log_events,
            }

            if self.sequence_token:
                kwargs["sequenceToken"] = self.sequence_token

            response = self.client.put_log_events(**kwargs)
            self.sequence_token = response.get("nextSequenceToken")

            self.logger.debug(f"Sent {len(log_events)} logs to CloudWatch")

        except ClientError as e:
            error_code = e.response["Error"]["Code"]

            if error_code == "InvalidSequenceTokenException":
                # Extract the correct sequence token from the error message
                self.sequence_token = e.response["Error"]["Message"].split(" ")[-1]
                # Retry with correct token
                self._send_logs(logs)
            elif error_code == "DataAlreadyAcceptedException":
                # Logs already sent, update sequence token
                self.sequence_token = e.response["Error"]["Message"].split(" ")[-1]
            else:
                self.logger.error(f"Error sending logs to CloudWatch: {e}")
                # Re-queue logs on error
                for log in logs:
                    self.buffer.put(log)

    def flush(self) -> None:
        """Force flush all buffered logs."""
        # Send a flush signal by temporarily setting flush interval to 0
        original_interval = self.flush_interval
        self.flush_interval = 0
        time.sleep(0.1)  # Give worker time to process
        self.flush_interval = original_interval

    def close(self) -> None:
        """Close the handler and flush remaining logs."""
        self.logger.info("Closing CloudWatch handler")
        self.stop_event.set()
        self.worker_thread.join(timeout=5.0)

    def __enter__(self) -> "CloudWatchHandler":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()


class CloudWatchLogger:
    """High-level CloudWatch logging interface."""

    def __init__(
        self,
        log_group_name: str,
        log_stream_prefix: str | None = None,
        region_name: str | None = None,
    ) -> None:
        """Initialize CloudWatch logger.

        Args:
            log_group_name: CloudWatch log group name
            log_stream_prefix: Prefix for log stream names
            region_name: AWS region
        """
        self.log_group_name = log_group_name
        self.log_stream_prefix = log_stream_prefix or "entropy-playground"
        self.region_name = region_name
        self.handlers: dict[str, CloudWatchHandler] = {}

    def get_handler(self, component: str) -> CloudWatchHandler:
        """Get or create a handler for a component.

        Args:
            component: Component name (e.g., "agent", "coordinator")

        Returns:
            CloudWatch handler for the component
        """
        if component not in self.handlers:
            stream_name = f"{self.log_stream_prefix}/{component}/{datetime.utcnow().strftime('%Y%m%d')}"
            self.handlers[component] = CloudWatchHandler(
                log_group_name=self.log_group_name,
                log_stream_name=stream_name,
                region_name=self.region_name,
            )
        return self.handlers[component]

    def log(self, component: str, level: str, message: str, **kwargs: Any) -> None:
        """Log a message to CloudWatch.

        Args:
            component: Component name
            level: Log level
            message: Log message
            **kwargs: Additional log fields
        """
        handler = self.get_handler(component)

        record = {
            "level": level,
            "component": component,
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }

        handler.emit(record)

    def close(self) -> None:
        """Close all handlers."""
        for handler in self.handlers.values():
            handler.close()
        self.handlers.clear()


# Global CloudWatch logger instance
_cloudwatch_logger: CloudWatchLogger | None = None


def get_cloudwatch_logger() -> CloudWatchLogger | None:
    """Get the global CloudWatch logger instance."""
    return _cloudwatch_logger


def configure_cloudwatch(
    log_group_name: str,
    log_stream_prefix: str | None = None,
    region_name: str | None = None,
) -> None:
    """Configure CloudWatch logging.

    Args:
        log_group_name: CloudWatch log group name
        log_stream_prefix: Prefix for log stream names
        region_name: AWS region
    """
    global _cloudwatch_logger

    # Close existing logger if any
    if _cloudwatch_logger:
        _cloudwatch_logger.close()

    _cloudwatch_logger = CloudWatchLogger(
        log_group_name=log_group_name,
        log_stream_prefix=log_stream_prefix,
        region_name=region_name,
    )
