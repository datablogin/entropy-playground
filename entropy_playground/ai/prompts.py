"""Prompt engineering framework for Claude interactions."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from pydantic import BaseModel

from entropy_playground.logging.logger import get_logger

logger = get_logger(__name__)


class AgentRole(str, Enum):
    """Agent roles for prompt customization."""

    ISSUE_READER = "issue_reader"
    CODER = "coder"
    REVIEWER = "reviewer"
    COORDINATOR = "coordinator"


class PromptTemplate(BaseModel):
    """Template for generating prompts."""

    role: AgentRole
    system_prompt: str
    task_prompt: str
    output_format: str | None = None
    examples: list[dict[str, str]] | None = None
    constraints: list[str] | None = None

    def format(self, **kwargs: Any) -> dict[str, str]:
        """Format the template with provided values.

        Args:
            **kwargs: Values to substitute in templates

        Returns:
            Formatted prompts
        """
        formatted_system = self.system_prompt.format(**kwargs)
        formatted_task = self.task_prompt.format(**kwargs)

        # Add output format if specified
        if self.output_format:
            formatted_task += f"\n\nOutput Format:\n{self.output_format}"

        # Add examples if provided
        if self.examples:
            examples_text = "\n\nExamples:"
            for i, example in enumerate(self.examples, 1):
                examples_text += f"\n\nExample {i}:"
                if "input" in example:
                    examples_text += f"\nInput: {example['input']}"
                if "output" in example:
                    examples_text += f"\nOutput: {example['output']}"
            formatted_task += examples_text

        # Add constraints if specified
        if self.constraints:
            constraints_text = "\n\nConstraints:"
            for constraint in self.constraints:
                constraints_text += f"\n- {constraint}"
            formatted_task += constraints_text

        return {
            "system": formatted_system,
            "task": formatted_task,
        }


class BasePromptStrategy(ABC):
    """Base class for prompt generation strategies."""

    @abstractmethod
    def generate_prompt(self, context: dict[str, Any]) -> PromptTemplate:
        """Generate a prompt template based on context.

        Args:
            context: Context information for prompt generation

        Returns:
            PromptTemplate object
        """
        pass


class IssueReaderPromptStrategy(BasePromptStrategy):
    """Prompt strategy for issue reader agents."""

    def generate_prompt(self, context: dict[str, Any]) -> PromptTemplate:
        """Generate prompt for reading and analyzing GitHub issues."""
        return PromptTemplate(
            role=AgentRole.ISSUE_READER,
            system_prompt=(
                "You are an expert GitHub issue analyzer for the Entropy Playground project. "
                "Your role is to read, understand, and extract actionable tasks from GitHub issues. "
                "You have deep knowledge of software development, requirements analysis, and "
                "task decomposition."
            ),
            task_prompt=(
                "Analyze the following GitHub issue and extract actionable tasks:\n\n"
                "Issue #{issue_number}: {issue_title}\n"
                "Author: {issue_author}\n"
                "Labels: {issue_labels}\n\n"
                "Description:\n{issue_body}\n\n"
                "Please provide:\n"
                "1. A summary of the issue\n"
                "2. A list of specific, actionable tasks\n"
                "3. Any dependencies or prerequisites\n"
                "4. Estimated complexity (simple/medium/complex)\n"
                "5. Suggested agent assignments (coder/reviewer)"
            ),
            output_format=(
                "```json\n"
                "{\n"
                '  "summary": "Brief issue summary",\n'
                '  "tasks": [\n'
                "    {\n"
                '      "id": "task-1",\n'
                '      "description": "Task description",\n'
                '      "type": "implementation|test|documentation",\n'
                '      "complexity": "simple|medium|complex",\n'
                '      "assigned_to": "coder|reviewer",\n'
                '      "dependencies": ["task-id"]\n'
                "    }\n"
                "  ],\n"
                '  "prerequisites": ["List of prerequisites"],\n'
                '  "estimated_effort": "hours or days"\n'
                "}\n"
                "```"
            ),
            constraints=[
                "Focus on technical implementation details",
                "Break down complex tasks into smaller subtasks",
                "Consider existing codebase architecture",
                "Identify potential risks or challenges",
            ],
        )


class CoderPromptStrategy(BasePromptStrategy):
    """Prompt strategy for coder agents."""

    def generate_prompt(self, context: dict[str, Any]) -> PromptTemplate:
        """Generate prompt for code implementation tasks."""
        return PromptTemplate(
            role=AgentRole.CODER,
            system_prompt=(
                "You are an expert Python developer working on the Entropy Playground project. "
                "You write clean, maintainable, and well-tested code following best practices. "
                "You are familiar with the project's architecture, including asyncio, Pydantic, "
                "Click CLI framework, and AWS integration."
            ),
            task_prompt=(
                "Implement the following task:\n\n"
                "Task: {task_description}\n"
                "Type: {task_type}\n"
                "Context: {task_context}\n\n"
                "Current codebase structure:\n{codebase_info}\n\n"
                "Requirements:\n{requirements}\n\n"
                "Please provide:\n"
                "1. Implementation approach\n"
                "2. Code changes (with file paths)\n"
                "3. Test cases\n"
                "4. Any configuration changes needed"
            ),
            output_format=(
                "## Implementation Approach\n"
                "[Describe your approach]\n\n"
                "## Code Changes\n\n"
                "### File: [file_path]\n"
                "```python\n"
                "# Your code here\n"
                "```\n\n"
                "## Test Cases\n\n"
                "### File: tests/[test_file_path]\n"
                "```python\n"
                "# Test code here\n"
                "```\n\n"
                "## Configuration\n"
                "[Any config changes needed]"
            ),
            constraints=[
                "Follow PEP 8 style guidelines",
                "Include comprehensive error handling",
                "Write unit tests for all new functionality",
                "Use type hints for all function signatures",
                "Add docstrings to all classes and methods",
                "Ensure backward compatibility",
            ],
            examples=[
                {
                    "input": "Create a new API endpoint for health checks",
                    "output": "Implementation includes: 1) New route in cli/main.py, 2) Health check handler, 3) Unit tests",
                },
            ],
        )


class ReviewerPromptStrategy(BasePromptStrategy):
    """Prompt strategy for code reviewer agents."""

    def generate_prompt(self, context: dict[str, Any]) -> PromptTemplate:
        """Generate prompt for code review tasks."""
        return PromptTemplate(
            role=AgentRole.REVIEWER,
            system_prompt=(
                "You are a senior software engineer conducting code reviews for the Entropy Playground project. "
                "You focus on code quality, security, performance, and maintainability. "
                "You provide constructive feedback and suggest improvements while acknowledging good practices."
            ),
            task_prompt=(
                "Review the following code changes:\n\n"
                "Pull Request: {pr_title}\n"
                "Author: {pr_author}\n"
                "Files Changed: {files_changed}\n\n"
                "Changes:\n{code_diff}\n\n"
                "Please provide:\n"
                "1. Overall assessment\n"
                "2. Specific issues found (if any)\n"
                "3. Suggestions for improvement\n"
                "4. Security considerations\n"
                "5. Test coverage assessment"
            ),
            output_format=(
                "## Code Review Summary\n\n"
                "**Overall Assessment**: [APPROVED|NEEDS_CHANGES|REJECTED]\n\n"
                "### Strengths\n"
                "- [List positive aspects]\n\n"
                "### Issues Found\n"
                "1. **[Issue Type]**: [Description]\n"
                "   - File: [file:line]\n"
                "   - Suggestion: [How to fix]\n\n"
                "### Security Review\n"
                "[Security considerations]\n\n"
                "### Test Coverage\n"
                "[Assessment of test coverage]\n\n"
                "### Recommendations\n"
                "[Specific recommendations]"
            ),
            constraints=[
                "Be constructive and specific in feedback",
                "Check for security vulnerabilities",
                "Verify test coverage",
                "Ensure code follows project standards",
                "Consider performance implications",
                "Review error handling",
            ],
        )


class PromptEngineer:
    """Main class for managing prompt generation."""

    def __init__(self) -> None:
        """Initialize prompt engineer with strategies."""
        self._strategies = {
            AgentRole.ISSUE_READER: IssueReaderPromptStrategy(),
            AgentRole.CODER: CoderPromptStrategy(),
            AgentRole.REVIEWER: ReviewerPromptStrategy(),
        }

    def create_prompt(self, role: AgentRole, context: dict[str, Any]) -> dict[str, str]:
        """Create a formatted prompt for the given role and context.

        Args:
            role: Agent role
            context: Context information

        Returns:
            Dictionary with 'system' and 'task' prompts

        Raises:
            ValueError: If role is not supported
        """
        if role not in self._strategies:
            raise ValueError(f"Unsupported role: {role}")

        strategy = self._strategies[role]
        template = strategy.generate_prompt(context)

        logger.debug(f"Generated prompt template for role: {role}")

        return template.format(**context)

    def add_strategy(self, role: AgentRole, strategy: BasePromptStrategy) -> None:
        """Add or replace a prompt strategy.

        Args:
            role: Agent role
            strategy: Prompt strategy instance
        """
        self._strategies[role] = strategy
        logger.info(f"Added prompt strategy for role: {role}")


def create_conversation(
    system_prompt: str,
    messages: list[dict[str, str]],
    task_prompt: str | None = None,
) -> list[dict[str, str]]:
    """Create a conversation format for Claude API.

    Args:
        system_prompt: System prompt
        messages: Conversation history
        task_prompt: Optional task to append

    Returns:
        List of messages in Claude format
    """
    # Claude expects alternating user/assistant messages
    conversation = []

    # Add conversation history
    for msg in messages:
        conversation.append(
            {
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
            }
        )

    # Add task prompt if provided
    if task_prompt:
        conversation.append(
            {
                "role": "user",
                "content": task_prompt,
            }
        )

    return conversation
