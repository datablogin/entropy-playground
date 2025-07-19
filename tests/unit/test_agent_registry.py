"""
Unit tests for agent registry and factory.
"""

from unittest.mock import MagicMock

import pytest

from entropy_playground.agents import AgentConfig, BaseAgent
from entropy_playground.runtime import (
    AgentFactory,
    AgentRegistry,
    AgentRegistryError,
    get_registry,
    register_agent,
)


class TestAgent(BaseAgent):
    """Test agent implementation."""

    async def initialize(self) -> None:
        pass

    async def run(self) -> None:
        pass

    async def cleanup(self) -> None:
        pass

    async def perform_health_checks(self) -> dict[str, bool]:
        return {"test": True}

    async def collect_metrics(self) -> dict[str, float]:
        return {"test_metric": 1.0}


class AnotherTestAgent(TestAgent):
    """Another test agent implementation."""

    pass


class NotAnAgent:
    """Class that is not an agent."""

    pass


class TestAgentRegistry:
    """Test AgentRegistry functionality."""

    @pytest.fixture
    def registry(self):
        """Create a fresh registry for each test."""
        reg = AgentRegistry()
        yield reg
        reg.clear()

    def test_register_agent(self, registry):
        """Test registering an agent."""
        registry.register("test", TestAgent)

        assert "test" in registry.list_roles()
        assert registry.get("test") == TestAgent

    def test_register_with_validator(self, registry):
        """Test registering an agent with a validator."""

        def validator(config: AgentConfig):
            if config.metadata.get("required") != "value":
                raise ValueError("Missing required metadata")

        registry.register("test", TestAgent, validator)

        # Valid config
        config = AgentConfig(name="test-agent", role="test", metadata={"required": "value"})
        registry.validate_config("test", config)

        # Invalid config
        bad_config = AgentConfig(name="test-agent", role="test")
        with pytest.raises(AgentRegistryError) as exc_info:
            registry.validate_config("test", bad_config)
        assert "validation failed" in str(exc_info.value)

    def test_register_invalid_agent(self, registry):
        """Test registering invalid agent classes."""
        # Empty role
        with pytest.raises(AgentRegistryError) as exc_info:
            registry.register("", TestAgent)
        assert "cannot be empty" in str(exc_info.value)

        # Not a class
        with pytest.raises(AgentRegistryError):
            registry.register("test", "not a class")

        # Not an agent subclass
        with pytest.raises(AgentRegistryError) as exc_info:
            registry.register("test", NotAnAgent)
        assert "subclass of BaseAgent" in str(exc_info.value)

    def test_overwrite_registration(self, registry):
        """Test overwriting an existing registration."""
        registry.register("test", TestAgent)
        registry.register("test", AnotherTestAgent)

        assert registry.get("test") == AnotherTestAgent

    def test_unregister_agent(self, registry):
        """Test unregistering an agent."""
        registry.register("test", TestAgent)
        registry.unregister("test")

        assert "test" not in registry.list_roles()

        with pytest.raises(AgentRegistryError):
            registry.get("test")

    def test_unregister_nonexistent(self, registry):
        """Test unregistering a non-existent agent."""
        with pytest.raises(AgentRegistryError) as exc_info:
            registry.unregister("nonexistent")
        assert "not registered" in str(exc_info.value)

    def test_get_nonexistent_agent(self, registry):
        """Test getting a non-existent agent."""
        with pytest.raises(AgentRegistryError) as exc_info:
            registry.get("nonexistent")
        assert "not registered" in str(exc_info.value)
        assert "Available roles:" in str(exc_info.value)

    def test_list_roles(self, registry):
        """Test listing registered roles."""
        assert registry.list_roles() == []

        registry.register("test1", TestAgent)
        registry.register("test2", AnotherTestAgent)

        roles = registry.list_roles()
        assert len(roles) == 2
        assert "test1" in roles
        assert "test2" in roles

    def test_get_info(self, registry):
        """Test getting agent information."""
        registry.register("test", TestAgent)

        info = registry.get_info("test")
        assert info["role"] == "test"
        assert info["class"] == "TestAgent"
        assert info["module"] == "tests.unit.test_agent_registry"
        assert "Test agent implementation" in info["docstring"]
        assert not info["has_validator"]
        assert "initialize" in info["methods"]
        assert "run" in info["methods"]
        assert "cleanup" in info["methods"]

    def test_get_info_with_validator(self, registry):
        """Test getting info for agent with validator."""
        registry.register("test", TestAgent, lambda c: None)

        info = registry.get_info("test")
        assert info["has_validator"]

    def test_validate_config_role_mismatch(self, registry):
        """Test config validation with role mismatch."""
        registry.register("test", TestAgent)

        config = AgentConfig(name="agent", role="wrong_role")
        with pytest.raises(AgentRegistryError) as exc_info:
            registry.validate_config("test", config)
        assert "does not match" in str(exc_info.value)

    def test_clear_registry(self, registry):
        """Test clearing the registry."""
        registry.register("test1", TestAgent)
        registry.register("test2", AnotherTestAgent)

        registry.clear()
        assert registry.list_roles() == []


class TestAgentFactory:
    """Test AgentFactory functionality."""

    @pytest.fixture
    def registry(self):
        """Create a registry with test agents."""
        reg = AgentRegistry()
        reg.register("test", TestAgent)
        reg.register("another", AnotherTestAgent)
        yield reg
        reg.clear()

    @pytest.fixture
    def factory(self, registry):
        """Create a factory with the test registry."""
        return AgentFactory(registry)

    def test_create_agent(self, factory):
        """Test creating an agent instance."""
        config = AgentConfig(name="test-agent", role="test")
        agent = factory.create(config)

        assert isinstance(agent, TestAgent)
        assert agent.config == config

    def test_create_with_kwargs(self, factory):
        """Test creating an agent with additional kwargs."""
        config = AgentConfig(name="test-agent", role="test")

        # Mock the agent class to check kwargs
        original_class = factory.registry.get("test")
        mock_instance = MagicMock(spec=TestAgent)
        mock_class = MagicMock(return_value=mock_instance)
        mock_class.__name__ = "MockTestAgent"  # Add __name__ attribute
        factory.registry._agents["test"] = mock_class

        result = factory.create(config, custom_param="value")

        assert result is mock_instance
        mock_class.assert_called_once_with(config, custom_param="value")

        # Restore original
        factory.registry._agents["test"] = original_class

    def test_create_singleton(self, factory):
        """Test creating singleton agents."""
        config = AgentConfig(name="singleton", role="test")

        # Create first instance
        agent1 = factory.create(config, singleton=True)

        # Create second instance - should return same
        agent2 = factory.create(config, singleton=True)

        assert agent1 is agent2
        assert factory.get_instance("singleton") is agent1

    def test_create_non_singleton(self, factory):
        """Test creating non-singleton agents."""
        config = AgentConfig(name="regular", role="test")

        agent1 = factory.create(config, singleton=False)
        agent2 = factory.create(config, singleton=False)

        assert agent1 is not agent2
        assert factory.get_instance("regular") is None

    def test_create_with_invalid_role(self, factory):
        """Test creating an agent with invalid role."""
        config = AgentConfig(name="test", role="invalid")

        with pytest.raises(AgentRegistryError) as exc_info:
            factory.create(config)
        assert "not registered" in str(exc_info.value)

    def test_create_with_validation_error(self, factory):
        """Test creating an agent that fails validation."""

        def validator(config: AgentConfig):
            raise ValueError("Validation failed")

        factory.registry.register("validated", TestAgent, validator)
        config = AgentConfig(name="test", role="validated")

        with pytest.raises(AgentRegistryError) as exc_info:
            factory.create(config)
        assert "validation failed" in str(exc_info.value)

    def test_get_instance(self, factory):
        """Test getting singleton instances."""
        config = AgentConfig(name="singleton", role="test")
        agent = factory.create(config, singleton=True)

        assert factory.get_instance("singleton") is agent
        assert factory.get_instance("nonexistent") is None

    def test_list_instances(self, factory):
        """Test listing all singleton instances."""
        config1 = AgentConfig(name="agent1", role="test")
        config2 = AgentConfig(name="agent2", role="another")

        agent1 = factory.create(config1, singleton=True)
        agent2 = factory.create(config2, singleton=True)

        instances = factory.list_instances()
        assert len(instances) == 2
        assert instances["agent1"] is agent1
        assert instances["agent2"] is agent2

    def test_remove_instance(self, factory):
        """Test removing singleton instances."""
        config = AgentConfig(name="singleton", role="test")
        factory.create(config, singleton=True)

        assert factory.remove_instance("singleton") is True
        assert factory.get_instance("singleton") is None
        assert factory.remove_instance("singleton") is False

    def test_clear_instances(self, factory):
        """Test clearing all instances."""
        config1 = AgentConfig(name="agent1", role="test")
        config2 = AgentConfig(name="agent2", role="another")

        factory.create(config1, singleton=True)
        factory.create(config2, singleton=True)

        factory.clear_instances()
        assert len(factory.list_instances()) == 0

    def test_create_with_constructor_error(self, factory):
        """Test handling constructor errors."""

        class FailingAgent(TestAgent):
            def __init__(self, config):
                raise RuntimeError("Constructor failed")

        factory.registry.register("failing", FailingAgent)
        config = AgentConfig(name="fail", role="failing")

        with pytest.raises(AgentRegistryError) as exc_info:
            factory.create(config)
        assert "Failed to create agent" in str(exc_info.value)
        assert "Constructor failed" in str(exc_info.value)


class TestGlobalRegistry:
    """Test global registry functionality."""

    def test_get_global_registry(self):
        """Test getting the global registry."""
        reg1 = get_registry()
        reg2 = get_registry()
        assert reg1 is reg2  # Should be same instance

    def test_register_agent_decorator(self):
        """Test the register_agent decorator."""
        registry = get_registry()

        # Clear any existing registrations
        if "decorated" in registry.list_roles():
            registry.unregister("decorated")

        @register_agent("decorated")
        class DecoratedAgent(TestAgent):
            """Decorated test agent."""

            pass

        assert registry.get("decorated") == DecoratedAgent

        # Cleanup
        registry.unregister("decorated")

    def test_register_agent_decorator_with_validator(self):
        """Test decorator with validator."""
        registry = get_registry()

        def validator(config: AgentConfig):
            assert config.metadata.get("validated") is True

        # Clear any existing registrations
        if "validated" in registry.list_roles():
            registry.unregister("validated")

        @register_agent("validated", validator=validator)
        class ValidatedAgent(TestAgent):
            pass

        # Test validation
        config = AgentConfig(name="test", role="validated", metadata={"validated": True})
        registry.validate_config("validated", config)

        # Cleanup
        registry.unregister("validated")

    def test_register_agent_direct(self):
        """Test direct registration using register_agent."""
        registry = get_registry()

        # Clear any existing registrations
        if "direct" in registry.list_roles():
            registry.unregister("direct")

        register_agent("direct", TestAgent)
        assert registry.get("direct") == TestAgent

        # Cleanup
        registry.unregister("direct")
