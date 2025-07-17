"""Pytest configuration and fixtures."""

import pytest
from pathlib import Path


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
