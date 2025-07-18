"""
Runtime module for Entropy-Playground.

Core runtime functionality including:
- Agent lifecycle management
- Task scheduling
- Inter-agent communication
- State management
"""

from entropy_playground.runtime.registry import (
    AgentFactory,
    AgentRegistry,
    AgentRegistryError,
    get_registry,
    register_agent,
)

__all__ = [
    "AgentRegistry",
    "AgentFactory",
    "AgentRegistryError",
    "get_registry",
    "register_agent",
]