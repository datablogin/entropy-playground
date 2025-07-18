"""Tests for CLI main entry point and commands."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from click.testing import CliRunner

from entropy_playground import __version__
from entropy_playground.cli import cli


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def mock_github():
    """Mock GitHub client."""
    with patch("github.Github") as mock:
        mock_instance = MagicMock()
        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_instance.get_user.return_value = mock_user
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def temp_config():
    """Create a temporary config file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        config_data = {
            "version": "0.1.0",
            "workspace": tmpdir,
            "redis_url": "redis://localhost:6379",
            "github": {"token": "test-token"},
        }
        with open(config_path, "w") as f:
            yaml.dump(config_data, f)
        yield config_path


class TestCLI:
    """Test main CLI functionality."""

    def test_version(self, runner):
        """Test version display."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_help(self, runner):
        """Test help display."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Entropy-Playground" in result.output
        assert "GitHub-Native AI Coding Agent Framework" in result.output


class TestInitCommand:
    """Test init command."""

    def test_init_success(self, runner, mock_github):
        """Test successful initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "entropy-workspace"

            result = runner.invoke(
                cli,
                [
                    "init",
                    "--workspace",
                    str(workspace),
                    "--github-token",
                    "test-token",
                    "--redis-url",
                    "redis://test:6379",
                ],
            )

            assert result.exit_code == 0
            assert "Environment initialized successfully!" in result.output

            # Check workspace created
            assert workspace.exists()
            assert workspace.is_dir()

            # Check config file created
            config_path = workspace / "config.yaml"
            assert config_path.exists()

            # Validate config content
            with open(config_path) as f:
                config = yaml.safe_load(f)

            assert config["version"] == __version__
            assert config["workspace"] == str(workspace)
            assert config["redis_url"] == "redis://test:6379"
            assert config["github"]["token"] == "${GITHUB_TOKEN}"

    def test_init_no_token(self, runner):
        """Test initialization without GitHub token."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "entropy-workspace"

            result = runner.invoke(
                cli,
                ["init", "--workspace", str(workspace)],
                env={"GITHUB_TOKEN": ""},  # Clear env var
            )

            assert result.exit_code == 1
            assert "GitHub token not provided" in result.output

    def test_init_permission_error(self, runner):
        """Test initialization with permission error."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Permission denied")

            result = runner.invoke(
                cli,
                ["init", "--github-token", "test-token"],
            )

            assert result.exit_code == 1
            assert "Permission denied" in result.output

    def test_init_github_validation_failure(self, runner):
        """Test initialization with GitHub validation failure."""
        with patch("github.Github") as mock_github:
            mock_github.side_effect = Exception("Invalid token")

            with tempfile.TemporaryDirectory() as tmpdir:
                workspace = Path(tmpdir) / "entropy-workspace"

                result = runner.invoke(
                    cli,
                    [
                        "init",
                        "--workspace",
                        str(workspace),
                        "--github-token",
                        "invalid-token",
                    ],
                )

                # Should still succeed but with warning
                assert result.exit_code == 0
                assert "Could not verify GitHub token" in result.output


class TestStartCommand:
    """Test start command."""

    def test_start_all_agents(self, runner, temp_config):
        """Test starting all agents."""
        result = runner.invoke(
            cli,
            ["--config", str(temp_config), "start", "--repo", "owner/repo"],
        )

        assert result.exit_code == 0
        assert "Starting all agent(s) for owner/repo" in result.output
        # Currently shows not implemented message
        assert "Agent startup not yet implemented" in result.output

    def test_start_specific_agent(self, runner, temp_config):
        """Test starting specific agent."""
        result = runner.invoke(
            cli,
            ["--config", str(temp_config), "start", "--agent", "coder", "--repo", "owner/repo"],
        )

        assert result.exit_code == 0
        assert "Starting coder agent(s) for owner/repo" in result.output

    def test_start_with_issue(self, runner, temp_config):
        """Test starting with specific issue."""
        result = runner.invoke(
            cli,
            ["--config", str(temp_config), "start", "--repo", "owner/repo", "--issue", "42"],
        )

        assert result.exit_code == 0
        assert "Working on issue #42" in result.output

    def test_start_invalid_repo_format(self, runner, temp_config):
        """Test starting with invalid repository format."""
        result = runner.invoke(
            cli,
            ["--config", str(temp_config), "start", "--repo", "invalid-format"],
        )

        assert result.exit_code == 1
        assert "Invalid repository format" in result.output
        assert "Expected format: owner/repo" in result.output

    def test_start_no_config(self, runner):
        """Test starting without configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config_data = {
                "version": "0.1.0",
                "workspace": tmpdir,
                "redis_url": "redis://localhost:6379",
                "github": {"token": "${GITHUB_TOKEN}"},  # Placeholder token
            }
            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            result = runner.invoke(
                cli,
                ["--config", str(config_path), "start", "--repo", "owner/repo"],
            )

            assert result.exit_code == 1
            assert "GitHub token not configured" in result.output
            assert "Run 'entropy-playground init' first" in result.output


class TestStatusCommand:
    """Test status command."""

    def test_status_default(self, runner, temp_config):
        """Test status with default format."""
        result = runner.invoke(cli, ["--config", str(temp_config), "status"])

        assert result.exit_code == 0
        assert "Agent Status" in result.output
        # Currently shows not implemented message
        assert "Status checking not yet implemented" in result.output

    def test_status_json_format(self, runner, temp_config):
        """Test status with JSON format."""
        result = runner.invoke(cli, ["--config", str(temp_config), "status", "--format", "json"])

        assert result.exit_code == 0


class TestStopCommand:
    """Test stop command."""

    def test_stop_all_agents(self, runner, temp_config):
        """Test stopping all agents."""
        result = runner.invoke(cli, ["--config", str(temp_config), "stop", "all"])

        assert result.exit_code == 0
        assert "Stopping all agent(s)" in result.output
        # Currently shows not implemented message
        assert "Agent stopping not yet implemented" in result.output

    def test_stop_specific_agent(self, runner, temp_config):
        """Test stopping specific agent."""
        result = runner.invoke(cli, ["--config", str(temp_config), "stop", "coder"])

        assert result.exit_code == 0
        assert "Stopping coder agent(s)" in result.output


class TestLogsCommand:
    """Test logs command."""

    def test_logs_default(self, runner, temp_config):
        """Test logs with default options."""
        result = runner.invoke(cli, ["--config", str(temp_config), "logs"])

        assert result.exit_code == 0
        assert "Showing logs for all agent(s)" in result.output
        # Currently shows not implemented message
        assert "Log viewing not yet implemented" in result.output

    def test_logs_with_options(self, runner, temp_config):
        """Test logs with various options."""
        result = runner.invoke(
            cli,
            ["--config", str(temp_config), "logs", "--tail", "100", "--follow", "--agent", "coder"],
        )

        assert result.exit_code == 0
        assert "Showing logs for coder agent(s)" in result.output
