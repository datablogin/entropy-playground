"""AI integration modules for Entropy Playground."""

from .claude import ClaudeClient, MockClaudeClient
from .prompts import (
    AgentRole,
    PromptEngineer,
    PromptTemplate,
    create_conversation,
)

__all__ = [
    "ClaudeClient",
    "MockClaudeClient",
    "AgentRole",
    "PromptEngineer",
    "PromptTemplate",
    "create_conversation",
]
