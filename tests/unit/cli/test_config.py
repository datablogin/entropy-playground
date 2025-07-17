"""Tests for configuration management."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from entropy_playground.infrastructure.config import (
    AgentConfig,
    AgentsConfig,
    Config,
    GitHubConfig,
)


class TestGitHubConfig:
    """Test GitHub configuration."""

    def test_token_expansion(self):
        """Test environment variable expansion in token."""
        os.environ["TEST_TOKEN"] = "my-secret-token"

        config = GitHubConfig(token="${TEST_TOKEN}")
        assert config.token == "my-secret-token"

        # Clean up
        del os.environ["TEST_TOKEN"]

    def test_token_no_expansion(self):
        """Test token without environment variable."""
        config = GitHubConfig(token="plain-token")
        assert config.token == "plain-token"

    def test_token_missing_env(self):
        """Test token with missing environment variable."""
        config = GitHubConfig(token="${MISSING_TOKEN}")
        assert config.token == "${MISSING_TOKEN}"


class TestAgentConfig:
    """Test agent configuration."""

    def test_defaults(self):
        """Test default agent configuration."""
        config = AgentConfig()
        assert config.enabled is True
        assert config.max_retries == 3
        assert config.timeout == 300

    def test_custom_values(self):
        """Test custom agent configuration."""
        config = AgentConfig(enabled=False, max_retries=5, timeout=600)
        assert config.enabled is False
        assert config.max_retries == 5
        assert config.timeout == 600


class TestConfig:
    """Test main configuration."""

    def test_defaults(self):
        """Test default configuration."""
        config = Config()
        assert config.version == "0.1.0"
        assert config.workspace == Path.cwd() / ".entropy"
        assert config.redis_url == "redis://localhost:6379"
        assert config.github.token == "${GITHUB_TOKEN}"
        assert config.agents.issue_reader.enabled is True
        assert config.agents.coder.enabled is True
        assert config.agents.reviewer.enabled is True

    def test_from_file(self):
        """Test loading configuration from file."""
        config_data = {
            "version": "1.0.0",
            "workspace": "/tmp/entropy",
            "redis_url": "redis://custom:6379",
            "github": {"token": "test-token"},
            "agents": {
                "issue_reader": {"enabled": False},
                "coder": {"max_retries": 5},
                "reviewer": {"timeout": 600},
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            config_path = Path(f.name)

        try:
            config = Config.from_file(config_path)
            assert config.version == "1.0.0"
            assert config.workspace == Path("/tmp/entropy")
            assert config.redis_url == "redis://custom:6379"
            assert config.github.token == "test-token"
            assert config.agents.issue_reader.enabled is False
            assert config.agents.coder.max_retries == 5
            assert config.agents.reviewer.timeout == 600
        finally:
            config_path.unlink()

    def test_from_file_not_found(self):
        """Test loading from non-existent file."""
        with pytest.raises(FileNotFoundError):
            Config.from_file(Path("/non/existent/file.yaml"))

    def test_from_env(self):
        """Test creating configuration from environment."""
        os.environ["ENTROPY_WORKSPACE"] = "/env/workspace"
        os.environ["REDIS_URL"] = "redis://env:6379"
        os.environ["GITHUB_TOKEN"] = "env-token"

        try:
            config = Config.from_env()
            assert config.workspace == Path("/env/workspace")
            assert config.redis_url == "redis://env:6379"
            assert config.github.token == "env-token"
        finally:
            # Clean up
            for key in ["ENTROPY_WORKSPACE", "REDIS_URL", "GITHUB_TOKEN"]:
                if key in os.environ:
                    del os.environ[key]

    def test_save(self):
        """Test saving configuration to file."""
        config = Config(
            version="2.0.0",
            workspace=Path("/save/test"),
            redis_url="redis://save:6379",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config.save(config_path)

            assert config_path.exists()

            # Load and verify
            with open(config_path) as f:
                data = yaml.safe_load(f)

            assert data["version"] == "2.0.0"
            assert data["workspace"] == "/save/test"
            assert data["redis_url"] == "redis://save:6379"

    def test_validate_github_token(self):
        """Test GitHub token validation."""
        # Valid token
        config = Config(github={"token": "valid-token"})
        assert config.validate_github_token() is True

        # Placeholder token
        config = Config(github={"token": "${GITHUB_TOKEN}"})
        assert config.validate_github_token() is False

        # Empty token
        config = Config(github={"token": ""})
        assert config.validate_github_token() is False

    def test_get_agent_config(self):
        """Test getting agent configuration."""
        config = Config()

        # Valid agent types
        assert isinstance(config.get_agent_config("issue_reader"), AgentConfig)
        assert isinstance(config.get_agent_config("coder"), AgentConfig)
        assert isinstance(config.get_agent_config("reviewer"), AgentConfig)

        # Invalid agent type
        with pytest.raises(ValueError, match="Unknown agent type"):
            config.get_agent_config("invalid_agent")
