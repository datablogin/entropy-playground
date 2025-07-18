"""
Base agent abstract class for the Entropy-Playground framework.

This module provides the foundation for all agent implementations with:
- Lifecycle management (start, stop, restart)
- Health monitoring and reporting
- Configuration management
- Graceful shutdown handling
- Event-driven communication
"""

import asyncio
import signal
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

from entropy_playground.logging.logger import get_logger


class AgentState(str, Enum):
    """Agent lifecycle states."""

    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class AgentHealth(str, Enum):
    """Agent health states."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class AgentConfig(BaseModel):
    """Base configuration for all agents."""

    name: str = Field(description="Unique agent name")
    role: str = Field(description="Agent role (e.g., issue_reader, coder, reviewer)")
    version: str = Field(default="1.0.0", description="Agent version")
    max_retries: int = Field(default=3, ge=0, description="Maximum retry attempts")
    timeout_seconds: int = Field(default=300, gt=0, description="Operation timeout in seconds")
    health_check_interval: int = Field(
        default=30, gt=0, description="Health check interval in seconds"
    )
    shutdown_timeout: int = Field(
        default=30, gt=0, description="Graceful shutdown timeout in seconds"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional agent metadata")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate agent name format."""
        if not v or not v.replace("-", "").replace("_", "").isalnum():
            raise ValueError("Agent name must be alphanumeric with hyphens or underscores")
        return v.lower()


class HealthStatus(BaseModel):
    """Agent health status information."""

    state: AgentHealth
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: dict[str, bool] = Field(default_factory=dict)
    message: str | None = None
    metrics: dict[str, float] = Field(default_factory=dict)

    @property
    def is_healthy(self) -> bool:
        """Check if agent is healthy."""
        return self.state == AgentHealth.HEALTHY


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the Entropy-Playground framework.

    This class provides:
    - Lifecycle management with state transitions
    - Health monitoring and reporting
    - Configuration management
    - Graceful shutdown handling
    - Event hooks for extensibility
    """

    def __init__(self, config: AgentConfig):
        """Initialize the base agent."""
        self.config = config
        self.logger = get_logger(f"agent.{config.role}.{config.name}")
        self._state = AgentState.INITIALIZING
        self._health = AgentHealth.HEALTHY
        self._start_time: float | None = None
        self._tasks: set[asyncio.Task] = set()
        self._shutdown_event = asyncio.Event()
        self._health_check_task: asyncio.Task | None = None
        self._run_task: asyncio.Task | None = None

        # Event callbacks
        self._on_state_change: list[Callable[[AgentState, AgentState], None]] = []
        self._on_health_change: list[Callable[[HealthStatus], None]] = []

        self.logger.info(
            "Agent initialized",
            agent_name=self.config.name,
            agent_role=self.config.role,
            agent_version=self.config.version,
        )

    @property
    def state(self) -> AgentState:
        """Get current agent state."""
        return self._state

    @property
    def health(self) -> AgentHealth:
        """Get current agent health."""
        return self._health

    @property
    def uptime(self) -> float:
        """Get agent uptime in seconds."""
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    def on_state_change(self, callback: Callable[[AgentState, AgentState], None]) -> None:
        """Register a state change callback."""
        self._on_state_change.append(callback)

    def on_health_change(self, callback: Callable[[HealthStatus], None]) -> None:
        """Register a health change callback."""
        self._on_health_change.append(callback)

    async def start(self) -> None:
        """Start the agent."""
        if self._state not in (AgentState.INITIALIZING, AgentState.STOPPED):
            self.logger.warning(
                "Cannot start agent in current state",
                current_state=self._state,
                agent_name=self.config.name,
            )
            return

        try:
            self._set_state(AgentState.READY)

            # Initialize the agent
            await self.initialize()

            # Start health monitoring
            self._health_check_task = asyncio.create_task(self._health_monitor())
            self._tasks.add(self._health_check_task)

            # Register signal handlers for graceful shutdown
            self._register_signal_handlers()

            # Start the agent
            self._start_time = time.time()
            self._set_state(AgentState.RUNNING)

            self.logger.info(
                "Agent started successfully",
                agent_name=self.config.name,
                agent_role=self.config.role,
            )

            # Run the agent in the background
            self._run_task = self.create_task(self.run())

        except Exception as e:
            self.logger.error(
                "Agent start failed", agent_name=self.config.name, error=str(e), exc_info=True
            )
            self._set_state(AgentState.ERROR)
            raise

    async def stop(self) -> None:
        """Stop the agent gracefully."""
        if self._state == AgentState.STOPPED:
            return

        self.logger.info("Stopping agent", agent_name=self.config.name, current_state=self._state)

        self._set_state(AgentState.STOPPING)
        self._shutdown_event.set()

        # Cancel health monitoring
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Wait for all tasks to complete with timeout
        if self._tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._tasks, return_exceptions=True),
                    timeout=self.config.shutdown_timeout,
                )
            except asyncio.TimeoutError:
                self.logger.warning(
                    "Some tasks did not complete within shutdown timeout",
                    agent_name=self.config.name,
                    timeout=self.config.shutdown_timeout,
                )
                # Force cancel remaining tasks
                for task in self._tasks:
                    if not task.done():
                        task.cancel()

        # Cleanup
        await self.cleanup()

        self._set_state(AgentState.STOPPED)
        self.logger.info("Agent stopped", agent_name=self.config.name, uptime_seconds=self.uptime)

    async def restart(self) -> None:
        """Restart the agent."""
        self.logger.info("Restarting agent", agent_name=self.config.name)
        await self.stop()
        await asyncio.sleep(1)  # Brief pause before restart
        await self.start()

    async def pause(self) -> None:
        """Pause agent execution."""
        if self._state != AgentState.RUNNING:
            self.logger.warning(
                "Cannot pause agent in current state",
                current_state=self._state,
                agent_name=self.config.name,
            )
            return

        self._set_state(AgentState.PAUSED)
        self.logger.info("Agent paused", agent_name=self.config.name)

    async def resume(self) -> None:
        """Resume agent execution."""
        if self._state != AgentState.PAUSED:
            self.logger.warning(
                "Cannot resume agent in current state",
                current_state=self._state,
                agent_name=self.config.name,
            )
            return

        self._set_state(AgentState.RUNNING)
        self.logger.info("Agent resumed", agent_name=self.config.name)

    async def get_health_status(self) -> HealthStatus:
        """Get current health status."""
        checks = await self.perform_health_checks()

        # Determine overall health based on checks
        failed_checks = [name for name, passed in checks.items() if not passed]
        if not failed_checks:
            health = AgentHealth.HEALTHY
            message = "All health checks passed"
        elif len(failed_checks) < len(checks) / 2:
            health = AgentHealth.DEGRADED
            message = f"Some health checks failed: {', '.join(failed_checks)}"
        else:
            health = AgentHealth.UNHEALTHY
            message = f"Multiple health checks failed: {', '.join(failed_checks)}"

        # Collect metrics
        metrics = await self.collect_metrics()
        metrics["uptime_seconds"] = self.uptime

        return HealthStatus(state=health, checks=checks, message=message, metrics=metrics)

    def create_task(self, coro: Any) -> asyncio.Task:
        """Create and track an async task."""
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return task

    @asynccontextmanager
    async def task_context(self, name: str) -> AsyncGenerator[None, None]:
        """Context manager for task execution with error handling."""
        task_logger = self.logger.bind(task_name=name)
        task_logger.debug("Task started")

        try:
            yield
            task_logger.debug("Task completed")
        except asyncio.CancelledError:
            task_logger.debug("Task cancelled")
            raise
        except Exception as e:
            task_logger.error("Task failed", error=str(e), exc_info=True)
            raise

    def _set_state(self, new_state: AgentState) -> None:
        """Set agent state and trigger callbacks."""
        old_state = self._state
        if old_state == new_state:
            return

        self._state = new_state
        self.logger.info(
            "Agent state changed",
            agent_name=self.config.name,
            old_state=old_state,
            new_state=new_state,
        )

        # Trigger state change callbacks
        for callback in self._on_state_change:
            try:
                callback(old_state, new_state)
            except Exception as e:
                self.logger.error("State change callback failed", error=str(e), exc_info=True)

    def _set_health(self, new_health: AgentHealth, status: HealthStatus) -> None:
        """Set agent health and trigger callbacks."""
        old_health = self._health
        if old_health == new_health:
            return

        self._health = new_health
        self.logger.info(
            "Agent health changed",
            agent_name=self.config.name,
            old_health=old_health,
            new_health=new_health,
            message=status.message,
        )

        # Trigger health change callbacks
        for callback in self._on_health_change:
            try:
                callback(status)
            except Exception as e:
                self.logger.error("Health change callback failed", error=str(e), exc_info=True)

    async def _health_monitor(self) -> None:
        """Monitor agent health periodically."""
        while not self._shutdown_event.is_set():
            try:
                # Perform health check
                status = await self.get_health_status()
                self._set_health(status.state, status)

                # Wait for next check
                await asyncio.wait_for(
                    self._shutdown_event.wait(), timeout=self.config.health_check_interval
                )
            except asyncio.TimeoutError:
                # Normal timeout, continue monitoring
                continue
            except Exception as e:
                self.logger.error("Health monitoring error", error=str(e), exc_info=True)

    def _register_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""

        def signal_handler(signum: int, frame: Any) -> None:
            self.logger.info(
                "Received shutdown signal",
                signal=signal.Signals(signum).name,
                agent_name=self.config.name,
            )
            asyncio.create_task(self.stop())

        # Register handlers for common shutdown signals
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal_handler)

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def run(self) -> None:
        """Run the agent. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def perform_health_checks(self) -> dict[str, bool]:
        """
        Perform health checks.

        Returns:
            Dictionary mapping check names to pass/fail status
        """
        pass

    @abstractmethod
    async def collect_metrics(self) -> dict[str, float]:
        """
        Collect agent metrics.

        Returns:
            Dictionary mapping metric names to values
        """
        pass
