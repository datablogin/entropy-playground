"""
Agent registry and factory for managing agent instances.

This module provides:
- Central registry for agent types
- Factory pattern for agent creation
- Agent instance management
- Discovery and listing of available agents
"""

import inspect
from collections.abc import Callable
from typing import Any

from entropy_playground.agents.base import AgentConfig, BaseAgent
from entropy_playground.logging.logger import get_logger


class AgentRegistryError(Exception):
    """Agent registry specific errors."""

    pass


class AgentRegistry:
    """
    Central registry for agent types.

    This registry maintains a mapping of agent roles to their implementations,
    allowing for dynamic agent creation and discovery.
    """

    def __init__(self) -> None:
        """Initialize the agent registry."""
        self._agents: dict[str, type[BaseAgent]] = {}
        self._validators: dict[str, Callable[[AgentConfig], None]] = {}
        self.logger = get_logger("agent.registry")

    def register(
        self,
        role: str,
        agent_class: type[BaseAgent],
        validator: Callable[[AgentConfig], None] | None = None,
    ) -> None:
        """
        Register an agent class with the registry.

        Args:
            role: The role identifier for the agent
            agent_class: The agent class implementation
            validator: Optional configuration validator

        Raises:
            AgentRegistryError: If registration fails
        """
        if not role:
            raise AgentRegistryError("Agent role cannot be empty")

        if not inspect.isclass(agent_class) or not issubclass(agent_class, BaseAgent):
            raise AgentRegistryError(
                f"Agent class must be a subclass of BaseAgent, got {agent_class}"
            )

        if role in self._agents:
            self.logger.warning(
                "Overwriting existing agent registration",
                role=role,
                old_class=self._agents[role].__name__,
                new_class=agent_class.__name__,
            )

        self._agents[role] = agent_class
        if validator:
            self._validators[role] = validator

        self.logger.info("Agent registered", role=role, agent_class=agent_class.__name__)

    def unregister(self, role: str) -> None:
        """
        Unregister an agent from the registry.

        Args:
            role: The role identifier to unregister

        Raises:
            AgentRegistryError: If the role is not registered
        """
        if role not in self._agents:
            raise AgentRegistryError(f"Agent role '{role}' is not registered")

        agent_class = self._agents.pop(role)
        self._validators.pop(role, None)

        self.logger.info("Agent unregistered", role=role, agent_class=agent_class.__name__)

    def get(self, role: str) -> type[BaseAgent]:
        """
        Get an agent class by role.

        Args:
            role: The role identifier

        Returns:
            The agent class

        Raises:
            AgentRegistryError: If the role is not registered
        """
        if role not in self._agents:
            available = ", ".join(self._agents.keys())
            raise AgentRegistryError(
                f"Agent role '{role}' is not registered. Available roles: {available}"
            )

        return self._agents[role]

    def list_roles(self) -> list[str]:
        """Get a list of all registered agent roles."""
        return list(self._agents.keys())

    def get_info(self, role: str) -> dict[str, Any]:
        """
        Get information about a registered agent.

        Args:
            role: The role identifier

        Returns:
            Dictionary with agent information

        Raises:
            AgentRegistryError: If the role is not registered
        """
        agent_class = self.get(role)

        return {
            "role": role,
            "class": agent_class.__name__,
            "module": agent_class.__module__,
            "docstring": inspect.getdoc(agent_class),
            "has_validator": role in self._validators,
            "methods": [
                name
                for name, _ in inspect.getmembers(
                    agent_class, predicate=lambda x: inspect.ismethod(x) or inspect.isfunction(x)
                )
                if not name.startswith("_")
            ],
        }

    def validate_config(self, role: str, config: AgentConfig) -> None:
        """
        Validate agent configuration.

        Args:
            role: The agent role
            config: The agent configuration

        Raises:
            AgentRegistryError: If validation fails
        """
        if role not in self._agents:
            raise AgentRegistryError(f"Agent role '{role}' is not registered")

        # Ensure role matches
        if config.role != role:
            raise AgentRegistryError(
                f"Configuration role '{config.role}' does not match registered role '{role}'"
            )

        # Run custom validator if available
        if role in self._validators:
            try:
                self._validators[role](config)
            except Exception as e:
                raise AgentRegistryError(f"Configuration validation failed: {e}") from e

    def clear(self) -> None:
        """Clear all registrations."""
        count = len(self._agents)
        self._agents.clear()
        self._validators.clear()
        self.logger.info("Registry cleared", agents_removed=count)


class AgentFactory:
    """
    Factory for creating agent instances.

    This factory uses the agent registry to create properly configured
    agent instances based on their role.
    """

    def __init__(self, registry: AgentRegistry):
        """
        Initialize the agent factory.

        Args:
            registry: The agent registry to use
        """
        self.registry = registry
        self.logger = get_logger("agent.factory")
        self._instances: dict[str, BaseAgent] = {}

    def create(self, config: AgentConfig, singleton: bool = False, **kwargs: Any) -> BaseAgent:
        """
        Create an agent instance.

        Args:
            config: Agent configuration
            singleton: Whether to reuse existing instance
            **kwargs: Additional arguments passed to agent constructor

        Returns:
            The created agent instance

        Raises:
            AgentRegistryError: If creation fails
        """
        # Validate configuration
        self.registry.validate_config(config.role, config)

        # Check for singleton instance
        if singleton and config.name in self._instances:
            self.logger.debug(
                "Returning singleton agent instance", agent_name=config.name, agent_role=config.role
            )
            return self._instances[config.name]

        # Get agent class
        agent_class = self.registry.get(config.role)

        # Create instance
        try:
            agent = agent_class(config, **kwargs)

            # Store singleton if requested
            if singleton:
                self._instances[config.name] = agent

            self.logger.info(
                "Agent created",
                agent_name=config.name,
                agent_role=config.role,
                agent_class=agent_class.__name__,
                singleton=singleton,
            )

            return agent

        except Exception as e:
            raise AgentRegistryError(
                f"Failed to create agent '{config.name}' with role '{config.role}': {e}"
            ) from e

    def get_instance(self, name: str) -> BaseAgent | None:
        """
        Get a singleton agent instance by name.

        Args:
            name: The agent name

        Returns:
            The agent instance or None if not found
        """
        return self._instances.get(name)

    def list_instances(self) -> dict[str, BaseAgent]:
        """Get all singleton agent instances."""
        return self._instances.copy()

    def remove_instance(self, name: str) -> bool:
        """
        Remove a singleton agent instance.

        Args:
            name: The agent name

        Returns:
            True if instance was removed, False if not found
        """
        if name in self._instances:
            del self._instances[name]
            self.logger.info("Agent instance removed", agent_name=name)
            return True
        return False

    def clear_instances(self) -> None:
        """Clear all singleton instances."""
        count = len(self._instances)
        self._instances.clear()
        self.logger.info("Factory instances cleared", instances_removed=count)


# Global registry instance
_global_registry = AgentRegistry()


def get_registry() -> AgentRegistry:
    """Get the global agent registry."""
    return _global_registry


def register_agent(
    role: str,
    agent_class: type[BaseAgent] | None = None,
    validator: Callable[[AgentConfig], None] | None = None,
) -> Callable:
    """
    Decorator for registering agent classes.

    Can be used as:
    - @register_agent("role")
    - @register_agent("role", validator=my_validator)

    Args:
        role: The agent role identifier
        agent_class: The agent class (if not used as decorator)
        validator: Optional configuration validator

    Returns:
        Decorator function or None if agent_class provided
    """

    def decorator(cls: type[BaseAgent]) -> type[BaseAgent]:
        get_registry().register(role, cls, validator)
        return cls

    if agent_class is not None:
        # Direct registration
        get_registry().register(role, agent_class, validator)
        return agent_class

    # Decorator usage
    return decorator
