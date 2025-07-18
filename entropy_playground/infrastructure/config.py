"""Configuration management for Entropy-Playground."""

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class GitHubConfig(BaseModel):
    """GitHub configuration settings."""

    token: str = Field(description="GitHub API token")

    @field_validator("token")
    @classmethod
    def expand_env_vars(cls, v: str) -> str:
        """Expand environment variables in token."""
        if v.startswith("${") and v.endswith("}"):
            env_var = v[2:-1]
            return os.environ.get(env_var, v)
        return v


class AgentConfig(BaseModel):
    """Individual agent configuration."""

    enabled: bool = Field(default=True, description="Whether agent is enabled")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    timeout: int = Field(default=300, description="Task timeout in seconds")


class AgentsConfig(BaseModel):
    """Configuration for all agents."""

    issue_reader: AgentConfig = Field(default_factory=AgentConfig)
    coder: AgentConfig = Field(default_factory=AgentConfig)
    reviewer: AgentConfig = Field(default_factory=AgentConfig)


class Config(BaseModel):
    """Main configuration for Entropy-Playground."""

    version: str = Field(default="0.1.0", description="Configuration version")
    workspace: Path = Field(
        default_factory=lambda: Path.cwd() / ".entropy", description="Workspace directory path"
    )
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")
    github: GitHubConfig = Field(default_factory=lambda: GitHubConfig(token="${GITHUB_TOKEN}"))
    agents: AgentsConfig = Field(default_factory=AgentsConfig)

    model_config = {
        "validate_assignment": True,
        "use_enum_values": True,
    }

    @classmethod
    def from_file(cls, config_path: Path) -> "Config":
        """Load configuration from YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Config instance

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path) as f:
            data = yaml.safe_load(f)

        return cls(**data)

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables.

        Returns:
            Config instance with values from environment
        """
        config_data: dict[str, Any] = {}

        if workspace := os.environ.get("ENTROPY_WORKSPACE"):
            config_data["workspace"] = Path(workspace)

        if redis_url := os.environ.get("REDIS_URL"):
            config_data["redis_url"] = redis_url

        if github_token := os.environ.get("GITHUB_TOKEN"):
            config_data["github"] = GitHubConfig(token=github_token)

        return cls(**config_data)

    def save(self, config_path: Path) -> None:
        """Save configuration to YAML file.

        Args:
            config_path: Path to save configuration
        """
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and handle Path objects
        data = self.model_dump()
        data["workspace"] = str(self.workspace)

        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    def validate_github_token(self) -> bool:
        """Validate GitHub token is set.

        Returns:
            True if token is set and not a placeholder
        """
        token = self.github.token
        return bool(token and not token.startswith("${"))

    def get_agent_config(self, agent_type: str) -> AgentConfig:
        """Get configuration for specific agent type.

        Args:
            agent_type: Type of agent (issue_reader, coder, reviewer)

        Returns:
            Agent configuration

        Raises:
            ValueError: If agent type is invalid
        """
        if not hasattr(self.agents, agent_type):
            raise ValueError(f"Unknown agent type: {agent_type}")

        agent_config = getattr(self.agents, agent_type)
        assert isinstance(agent_config, AgentConfig)
        return agent_config
