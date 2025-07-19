"""
Unit tests for the base agent class.
"""

import asyncio
from unittest.mock import patch

import pytest
import pytest_asyncio
from pydantic import ValidationError

from entropy_playground.agents import (
    AgentConfig,
    AgentHealth,
    AgentState,
    BaseAgent,
    HealthStatus,
)


class MockAgent(BaseAgent):
    """Mock agent implementation for testing."""

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.initialized = False
        self.running = False
        self.cleaned_up = False
        self.health_checks_called = 0
        self.metrics_called = 0

    async def initialize(self) -> None:
        self.initialized = True

    async def run(self) -> None:
        self.running = True
        await self._shutdown_event.wait()

    async def cleanup(self) -> None:
        self.cleaned_up = True

    async def perform_health_checks(self) -> dict[str, bool]:
        self.health_checks_called += 1
        return {
            "test_check": True,
            "memory_check": True,
        }

    async def collect_metrics(self) -> dict[str, float]:
        self.metrics_called += 1
        return {
            "test_metric": 42.0,
            "memory_usage": 100.0,
        }


class UnhealthyMockAgent(MockAgent):
    """Mock agent that reports unhealthy status."""

    async def perform_health_checks(self) -> dict[str, bool]:
        self.health_checks_called += 1
        return {
            "test_check": False,
            "memory_check": False,
            "cpu_check": False,
        }


class TestAgentConfig:
    """Test AgentConfig model."""

    def test_valid_config(self):
        """Test creating a valid agent configuration."""
        config = AgentConfig(
            name="test-agent",
            role="test",
            version="1.0.0",
            max_retries=5,
            timeout_seconds=60,
            health_check_interval=10,
            shutdown_timeout=15,
            metadata={"key": "value"},
        )
        assert config.name == "test-agent"
        assert config.role == "test"
        assert config.version == "1.0.0"
        assert config.max_retries == 5
        assert config.timeout_seconds == 60
        assert config.health_check_interval == 10
        assert config.shutdown_timeout == 15
        assert config.metadata == {"key": "value"}

    def test_default_values(self):
        """Test default configuration values."""
        config = AgentConfig(name="test", role="test")
        assert config.version == "1.0.0"
        assert config.max_retries == 3
        assert config.timeout_seconds == 300
        assert config.health_check_interval == 30
        assert config.shutdown_timeout == 30
        assert config.metadata == {}

    def test_name_validation(self):
        """Test agent name validation."""
        # Valid names
        AgentConfig(name="valid-name", role="test")
        AgentConfig(name="valid_name", role="test")
        AgentConfig(name="valid123", role="test")

        # Invalid names
        with pytest.raises(ValidationError):
            AgentConfig(name="", role="test")

        with pytest.raises(ValidationError):
            AgentConfig(name="invalid name", role="test")

        with pytest.raises(ValidationError):
            AgentConfig(name="invalid@name", role="test")

    def test_name_normalization(self):
        """Test that agent names are normalized to lowercase."""
        config = AgentConfig(name="Test-Agent", role="test")
        assert config.name == "test-agent"


class TestHealthStatus:
    """Test HealthStatus model."""

    def test_health_status_creation(self):
        """Test creating a health status."""
        status = HealthStatus(
            state=AgentHealth.HEALTHY,
            checks={"check1": True, "check2": True},
            message="All good",
            metrics={"cpu": 50.0},
        )
        assert status.state == AgentHealth.HEALTHY
        assert status.checks == {"check1": True, "check2": True}
        assert status.message == "All good"
        assert status.metrics == {"cpu": 50.0}
        assert status.is_healthy is True

    def test_unhealthy_status(self):
        """Test unhealthy status."""
        status = HealthStatus(
            state=AgentHealth.UNHEALTHY,
            checks={"check1": False},
        )
        assert status.is_healthy is False


@pytest.mark.asyncio
class TestBaseAgent:
    """Test BaseAgent functionality."""

    @pytest.fixture
    def config(self):
        """Create test agent configuration."""
        return AgentConfig(
            name="test-agent",
            role="test",
            health_check_interval=1,  # Short interval for testing
            shutdown_timeout=1,
        )

    @pytest_asyncio.fixture
    async def agent(self, config):
        """Create test agent instance."""
        agent = MockAgent(config)
        yield agent
        # Cleanup
        if agent.state != AgentState.STOPPED:
            await agent.stop()

    async def test_agent_initialization(self, config):
        """Test agent initialization."""
        agent = MockAgent(config)
        assert agent.config == config
        assert agent.state == AgentState.INITIALIZING
        assert agent.health == AgentHealth.HEALTHY
        assert agent.uptime == 0.0
        assert not agent.initialized
        assert not agent.running

    async def test_agent_lifecycle(self, agent):
        """Test agent lifecycle transitions."""
        # Initial state
        assert agent.state == AgentState.INITIALIZING

        # Start
        await agent.start()
        assert agent.state == AgentState.RUNNING
        assert agent.initialized
        await asyncio.sleep(0.1)  # Give run() time to execute
        assert agent.running
        assert agent.uptime > 0

        # Pause
        await agent.pause()
        assert agent.state == AgentState.PAUSED

        # Resume
        await agent.resume()
        assert agent.state == AgentState.RUNNING

        # Stop
        await agent.stop()
        assert agent.state == AgentState.STOPPED
        assert agent.cleaned_up

    async def test_agent_restart(self, agent):
        """Test agent restart."""
        await agent.start()
        await asyncio.sleep(0.1)  # Ensure some uptime
        initial_uptime = agent.uptime
        assert initial_uptime > 0  # Verify we have some uptime

        await agent.restart()
        assert agent.state == AgentState.RUNNING
        # After restart, uptime should be very small (near 0)
        assert agent.uptime < initial_uptime / 2  # More robust check

    async def test_state_change_callbacks(self, agent):
        """Test state change callbacks."""
        states = []

        def on_state_change(old_state: AgentState, new_state: AgentState):
            states.append((old_state, new_state))

        agent.on_state_change(on_state_change)

        await agent.start()
        await agent.stop()

        expected = [
            (AgentState.INITIALIZING, AgentState.READY),
            (AgentState.READY, AgentState.RUNNING),
            (AgentState.RUNNING, AgentState.STOPPING),
            (AgentState.STOPPING, AgentState.STOPPED),
        ]
        assert states == expected

    async def test_health_monitoring(self, agent):
        """Test health monitoring functionality."""
        await agent.start()

        # Wait for health check
        await asyncio.sleep(1.5)

        # Check that health checks were called
        assert agent.health_checks_called > 0
        assert agent.metrics_called > 0

        # Get health status
        status = await agent.get_health_status()
        assert status.state == AgentHealth.HEALTHY
        assert status.checks["test_check"] is True
        assert status.metrics["test_metric"] == 42.0
        assert "uptime_seconds" in status.metrics

        await agent.stop()

    async def test_unhealthy_agent(self, config):
        """Test unhealthy agent detection."""
        agent = UnhealthyMockAgent(config)
        await agent.start()

        # Wait for health check
        await asyncio.sleep(1.5)

        # Check health status
        status = await agent.get_health_status()
        assert status.state == AgentHealth.UNHEALTHY
        assert agent.health == AgentHealth.UNHEALTHY

        await agent.stop()

    async def test_health_change_callbacks(self, agent):
        """Test health change callbacks."""
        health_changes = []

        def on_health_change(status: HealthStatus):
            health_changes.append(status)

        agent.on_health_change(on_health_change)

        await agent.start()

        # Manually trigger a health change since MockAgent always returns healthy
        # Force a health status change by manually calling _set_health
        unhealthy_status = HealthStatus(
            state=AgentHealth.UNHEALTHY, checks={"test": False}, message="Test unhealthy"
        )
        agent._set_health(AgentHealth.UNHEALTHY, unhealthy_status)

        await agent.stop()

        # Should have received the health change
        assert len(health_changes) == 1
        assert health_changes[0].state == AgentHealth.UNHEALTHY

    async def test_task_management(self, agent):
        """Test task creation and tracking."""
        await agent.start()

        # Create a task
        async def test_task():
            await asyncio.sleep(0.1)
            return "done"

        task = agent.create_task(test_task())
        assert task in agent._tasks

        # Wait for task completion
        result = await task
        assert result == "done"
        assert task not in agent._tasks  # Auto-removed after completion

        await agent.stop()

    async def test_task_context(self, agent):
        """Test task context manager."""
        await agent.start()

        # Successful task
        async with agent.task_context("test_task"):
            await asyncio.sleep(0.1)

        # Failed task
        with pytest.raises(ValueError):
            async with agent.task_context("failing_task"):
                raise ValueError("Test error")

        await agent.stop()

    async def test_graceful_shutdown(self, agent):
        """Test graceful shutdown with running tasks."""
        await agent.start()

        # Create a long-running task
        async def long_task():
            await asyncio.sleep(10)

        task = agent.create_task(long_task())

        # Stop should cancel the task
        await agent.stop()
        assert task.cancelled()

    async def test_signal_handling(self, agent):
        """Test signal handler registration."""
        with patch("signal.signal") as mock_signal:
            await agent.start()

            # Should register SIGTERM and SIGINT handlers
            assert mock_signal.call_count >= 2

            await agent.stop()

    async def test_invalid_state_transitions(self, agent):
        """Test invalid state transitions."""
        # Can't pause when not running
        await agent.pause()
        assert agent.state == AgentState.INITIALIZING

        # Can't resume when not paused
        await agent.resume()
        assert agent.state == AgentState.INITIALIZING

        # Start and stop normally
        await agent.start()
        await agent.stop()

        # Can start again from stopped state (this is allowed for restart functionality)
        await agent.start()
        assert agent.state == AgentState.RUNNING
        await agent.stop()

    async def test_error_handling(self, config):
        """Test error handling during agent lifecycle."""

        class ErrorAgent(MockAgent):
            async def initialize(self):
                raise RuntimeError("Initialization failed")

        agent = ErrorAgent(config)

        with pytest.raises(RuntimeError):
            await agent.start()

        assert agent.state == AgentState.ERROR

    async def test_callback_error_handling(self, agent):
        """Test that callback errors don't crash the agent."""

        def bad_callback(*args):
            raise RuntimeError("Callback error")

        agent.on_state_change(bad_callback)
        agent.on_health_change(bad_callback)

        # Should not raise despite callback errors
        await agent.start()
        await asyncio.sleep(1.5)  # Let health check run
        await agent.stop()
