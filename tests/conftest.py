"""Pytest configuration and fixtures."""

from pathlib import Path

import pytest

from entropy_playground.logging.logger import cleanup_logging_handlers


@pytest.fixture
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def temp_config(tmp_path):
    """Create a temporary configuration file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github:
  token: test_token
  repo: test/repo

agents:
  - name: test_agent
    type: issue_reader

redis:
  url: redis://localhost:6379
"""
    )
    return config_file


@pytest.fixture(autouse=True)
def cleanup_logging():
    """Automatically clean up logging handlers after each test."""
    yield
    # Clean up after test to prevent Windows file locking issues
    cleanup_logging_handlers()
