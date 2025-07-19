"""Tests for prompt engineering framework."""

import pytest

from entropy_playground.ai.prompts import (
    AgentRole,
    CoderPromptStrategy,
    IssueReaderPromptStrategy,
    PromptEngineer,
    PromptTemplate,
    ReviewerPromptStrategy,
    create_conversation,
)


class TestPromptTemplate:
    """Test PromptTemplate model."""

    def test_basic_formatting(self):
        """Test basic template formatting."""
        template = PromptTemplate(
            role=AgentRole.CODER,
            system_prompt="You are a {role} developer.",
            task_prompt="Implement {feature} functionality.",
        )

        result = template.format(role="Python", feature="authentication")

        assert result["system"] == "You are a Python developer."
        assert result["task"] == "Implement authentication functionality."

    def test_output_format_inclusion(self):
        """Test output format is included in task prompt."""
        template = PromptTemplate(
            role=AgentRole.CODER,
            system_prompt="System prompt",
            task_prompt="Task prompt",
            output_format="JSON format required",
        )

        result = template.format()

        assert "Output Format:" in result["task"]
        assert "JSON format required" in result["task"]

    def test_examples_inclusion(self):
        """Test examples are included in task prompt."""
        template = PromptTemplate(
            role=AgentRole.CODER,
            system_prompt="System prompt",
            task_prompt="Task prompt",
            examples=[
                {"input": "test input", "output": "test output"},
                {"input": "another input", "output": "another output"},
            ],
        )

        result = template.format()

        assert "Examples:" in result["task"]
        assert "Example 1:" in result["task"]
        assert "Example 2:" in result["task"]
        assert "test input" in result["task"]
        assert "test output" in result["task"]

    def test_constraints_inclusion(self):
        """Test constraints are included in task prompt."""
        template = PromptTemplate(
            role=AgentRole.CODER,
            system_prompt="System prompt",
            task_prompt="Task prompt",
            constraints=["Follow PEP 8", "Include tests", "Add documentation"],
        )

        result = template.format()

        assert "Constraints:" in result["task"]
        assert "- Follow PEP 8" in result["task"]
        assert "- Include tests" in result["task"]
        assert "- Add documentation" in result["task"]


class TestIssueReaderPromptStrategy:
    """Test IssueReaderPromptStrategy."""

    def test_generate_prompt(self):
        """Test prompt generation for issue reader."""
        strategy = IssueReaderPromptStrategy()
        context = {
            "issue_number": 123,
            "issue_title": "Add new feature",
            "issue_author": "developer",
            "issue_labels": "enhancement, priority-high",
            "issue_body": "Detailed description of the feature...",
        }

        template = strategy.generate_prompt(context)

        assert template.role == AgentRole.ISSUE_READER
        assert "GitHub issue analyzer" in template.system_prompt
        assert "Analyze the following GitHub issue" in template.task_prompt
        assert template.output_format is not None
        assert "json" in template.output_format.lower()
        assert len(template.constraints) > 0

    def test_formatted_prompt(self):
        """Test formatted prompt includes context."""
        strategy = IssueReaderPromptStrategy()
        context = {
            "issue_number": 123,
            "issue_title": "Add new feature",
            "issue_author": "developer",
            "issue_labels": "enhancement",
            "issue_body": "Feature description",
        }

        template = strategy.generate_prompt(context)
        result = template.format(**context)

        assert "Issue #123" in result["task"]
        assert "Add new feature" in result["task"]
        assert "developer" in result["task"]
        assert "enhancement" in result["task"]


class TestCoderPromptStrategy:
    """Test CoderPromptStrategy."""

    def test_generate_prompt(self):
        """Test prompt generation for coder."""
        strategy = CoderPromptStrategy()
        context = {
            "task_description": "Implement user authentication",
            "task_type": "implementation",
            "task_context": "New feature for login system",
            "codebase_info": "Django-based web application",
            "requirements": "OAuth2 support required",
        }

        template = strategy.generate_prompt(context)

        assert template.role == AgentRole.CODER
        assert "Python developer" in template.system_prompt
        assert "Implement the following task" in template.task_prompt
        assert template.output_format is not None
        assert "Implementation Approach" in template.output_format
        assert "Code Changes" in template.output_format
        assert len(template.constraints) > 0
        assert len(template.examples) > 0

    def test_formatted_prompt(self):
        """Test formatted prompt includes all context."""
        strategy = CoderPromptStrategy()
        context = {
            "task_description": "Implement user authentication",
            "task_type": "implementation",
            "task_context": "New feature",
            "codebase_info": "Django app",
            "requirements": "OAuth2 support",
        }

        template = strategy.generate_prompt(context)
        result = template.format(**context)

        assert "Implement user authentication" in result["task"]
        assert "implementation" in result["task"]
        assert "OAuth2 support" in result["task"]


class TestReviewerPromptStrategy:
    """Test ReviewerPromptStrategy."""

    def test_generate_prompt(self):
        """Test prompt generation for reviewer."""
        strategy = ReviewerPromptStrategy()
        context = {
            "pr_title": "Add authentication feature",
            "pr_author": "developer",
            "files_changed": "auth.py, views.py",
            "code_diff": "diff content here...",
        }

        template = strategy.generate_prompt(context)

        assert template.role == AgentRole.REVIEWER
        assert "senior software engineer" in template.system_prompt
        assert "Review the following code changes" in template.task_prompt
        assert template.output_format is not None
        assert "Code Review Summary" in template.output_format
        assert "Overall Assessment" in template.output_format
        assert len(template.constraints) > 0

    def test_formatted_prompt(self):
        """Test formatted prompt includes PR context."""
        strategy = ReviewerPromptStrategy()
        context = {
            "pr_title": "Add authentication feature",
            "pr_author": "developer",
            "files_changed": "auth.py",
            "code_diff": "diff content",
        }

        template = strategy.generate_prompt(context)
        result = template.format(**context)

        assert "Add authentication feature" in result["task"]
        assert "developer" in result["task"]
        assert "auth.py" in result["task"]


class TestPromptEngineer:
    """Test PromptEngineer class."""

    def test_create_prompt_issue_reader(self):
        """Test creating prompt for issue reader."""
        engineer = PromptEngineer()
        context = {
            "issue_number": 123,
            "issue_title": "Test issue",
            "issue_author": "user",
            "issue_labels": "bug",
            "issue_body": "Issue description",
        }

        result = engineer.create_prompt(AgentRole.ISSUE_READER, context)

        assert "system" in result
        assert "task" in result
        assert "GitHub issue analyzer" in result["system"]
        assert "Issue #123" in result["task"]

    def test_create_prompt_coder(self):
        """Test creating prompt for coder."""
        engineer = PromptEngineer()
        context = {
            "task_description": "Add feature",
            "task_type": "implementation",
            "task_context": "context",
            "codebase_info": "info",
            "requirements": "requirements",
        }

        result = engineer.create_prompt(AgentRole.CODER, context)

        assert "system" in result
        assert "task" in result
        assert "Python developer" in result["system"]
        assert "Add feature" in result["task"]

    def test_create_prompt_reviewer(self):
        """Test creating prompt for reviewer."""
        engineer = PromptEngineer()
        context = {
            "pr_title": "PR title",
            "pr_author": "author",
            "files_changed": "files",
            "code_diff": "diff",
        }

        result = engineer.create_prompt(AgentRole.REVIEWER, context)

        assert "system" in result
        assert "task" in result
        assert "senior software engineer" in result["system"]
        assert "PR title" in result["task"]

    def test_unsupported_role(self):
        """Test error for unsupported role."""
        engineer = PromptEngineer()

        with pytest.raises(ValueError, match="Unsupported role"):
            engineer.create_prompt("invalid_role", {})

    def test_add_custom_strategy(self):
        """Test adding custom strategy."""
        engineer = PromptEngineer()

        class CustomStrategy:
            def generate_prompt(self, context):
                return PromptTemplate(
                    role=AgentRole.COORDINATOR,
                    system_prompt="Custom system",
                    task_prompt="Custom task",
                )

        engineer.add_strategy(AgentRole.COORDINATOR, CustomStrategy())

        result = engineer.create_prompt(AgentRole.COORDINATOR, {})
        assert result["system"] == "Custom system"
        assert result["task"] == "Custom task"


class TestCreateConversation:
    """Test create_conversation function."""

    def test_empty_conversation(self):
        """Test creating conversation with no messages."""
        result = create_conversation("System prompt", [])

        assert len(result) == 0

    def test_conversation_with_messages(self):
        """Test creating conversation with existing messages."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        result = create_conversation("System prompt", messages)

        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hi there!"

    def test_conversation_with_task_prompt(self):
        """Test adding task prompt to conversation."""
        messages = [{"role": "user", "content": "Hello"}]

        result = create_conversation("System prompt", messages, "Please help me")

        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "user"
        assert result[1]["content"] == "Please help me"

    def test_message_with_missing_fields(self):
        """Test handling messages with missing fields."""
        messages = [
            {"content": "Hello"},  # Missing role
            {"role": "assistant"},  # Missing content
        ]

        result = create_conversation("System prompt", messages)

        assert len(result) == 2
        assert result[0]["role"] == "user"  # Default role
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == ""  # Default content
