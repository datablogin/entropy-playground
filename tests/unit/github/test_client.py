"""
Unit tests for GitHub API client.
"""

import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from github import GithubException, RateLimitExceededException

from entropy_playground.github.client import GitHubClient, GitHubTokenManager


class TestGitHubTokenManager:
    """Test cases for GitHubTokenManager."""

    def test_init_with_token(self):
        """Test initialization with explicit token."""
        token = "ghp_" + "x" * 36  # Valid format
        manager = GitHubTokenManager(token)
        assert manager.get_token() == token

    def test_init_with_env_var(self, monkeypatch):
        """Test initialization from environment variable."""
        token = "ghp_" + "x" * 36
        monkeypatch.setenv("GITHUB_TOKEN", token)
        manager = GitHubTokenManager()
        assert manager.get_token() == token

    def test_init_without_token(self, monkeypatch):
        """Test initialization fails without token."""
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
        with pytest.raises(ValueError, match="GitHub token not provided"):
            GitHubTokenManager()

    def test_validate_empty_token(self):
        """Test validation fails for empty token."""
        with pytest.raises(ValueError, match="GitHub token not provided"):
            GitHubTokenManager("")

    def test_validate_short_token(self):
        """Test validation fails for short token."""
        with pytest.raises(ValueError, match="Invalid token format"):
            GitHubTokenManager("short_token")

    @pytest.mark.parametrize("prefix", ["ghp_", "ghs_", "gho_", "ghu_", "ghr_"])
    def test_validate_valid_prefixes(self, prefix):
        """Test validation accepts valid token prefixes."""
        token = prefix + "x" * 36
        manager = GitHubTokenManager(token)
        assert manager.get_token() == token

    def test_validate_invalid_prefix_warns(self, caplog):
        """Test validation warns for invalid prefix."""
        token = "invalid_" + "x" * 40
        GitHubTokenManager(token)
        assert "Token does not match expected GitHub token format" in caplog.text

    def test_revoke(self):
        """Test token revocation."""
        token = "ghp_" + "x" * 36
        manager = GitHubTokenManager(token)
        manager.revoke()
        assert manager.get_token() is None


class TestGitHubClient:
    """Test cases for GitHubClient."""

    @pytest.fixture
    def mock_github(self):
        """Create a mock Github instance."""
        with patch("entropy_playground.github.client.Github") as mock:
            yield mock

    @pytest.fixture
    def client(self, mock_github, monkeypatch):
        """Create a GitHubClient instance with mocked dependencies."""
        monkeypatch.setenv("GITHUB_TOKEN", "ghp_" + "x" * 36)
        return GitHubClient()

    def test_init_default_params(self, mock_github, monkeypatch):
        """Test client initialization with default parameters."""
        token = "ghp_" + "x" * 36
        monkeypatch.setenv("GITHUB_TOKEN", token)

        client = GitHubClient()

        mock_github.assert_called_once_with(token)
        assert client._retry_count == GitHubClient.DEFAULT_RETRY_COUNT
        assert client._retry_delay == GitHubClient.DEFAULT_RETRY_DELAY

    def test_init_custom_params(self, mock_github):
        """Test client initialization with custom parameters."""
        token = "ghp_" + "x" * 36
        base_url = "https://github.enterprise.com/api/v3"

        client = GitHubClient(token=token, base_url=base_url, retry_count=5, retry_delay=2.0)

        mock_github.assert_called_once_with(token, base_url=base_url)
        assert client._retry_count == 5
        assert client._retry_delay == 2.0

    def test_handle_rate_limit(self, client):
        """Test rate limit handling."""
        reset_time = int((datetime.now() + timedelta(seconds=5)).timestamp())
        exception = RateLimitExceededException(
            status=403, data={"rate": {"reset": reset_time}}, headers={}
        )

        start_time = time.time()
        client._handle_rate_limit(exception)
        elapsed_time = time.time() - start_time

        # Should wait approximately 5 seconds (with 1 second buffer)
        assert 5 <= elapsed_time <= 7
        assert client._rate_limit_reset is not None

    def test_retry_operation_success(self, client):
        """Test retry operation succeeds on first attempt."""
        mock_operation = Mock(return_value="success")

        result = client._retry_operation(mock_operation, "arg1", kwarg1="value1")

        assert result == "success"
        mock_operation.assert_called_once_with("arg1", kwarg1="value1")

    def test_retry_operation_eventual_success(self, client):
        """Test retry operation succeeds after failures."""
        mock_operation = Mock(
            side_effect=[
                GithubException(500, {"message": "Server error"}, {}),
                GithubException(502, {"message": "Bad gateway"}, {}),
                "success",
            ]
        )

        with patch("time.sleep"):  # Speed up test
            result = client._retry_operation(mock_operation)

        assert result == "success"
        assert mock_operation.call_count == 3

    def test_retry_operation_all_failures(self, client):
        """Test retry operation fails after all attempts."""
        exception = GithubException(500, {"message": "Server error"}, {})
        mock_operation = Mock(side_effect=exception)

        with patch("time.sleep"):  # Speed up test
            with pytest.raises(GithubException) as exc_info:
                client._retry_operation(mock_operation)

        assert exc_info.value == exception
        assert mock_operation.call_count == client._retry_count

    @pytest.mark.parametrize("status_code", [401, 403, 404, 422])
    def test_retry_operation_no_retry_statuses(self, client, status_code):
        """Test retry operation doesn't retry certain status codes."""
        exception = GithubException(status_code, {"message": "Error"}, {})
        mock_operation = Mock(side_effect=exception)

        with pytest.raises(GithubException) as exc_info:
            client._retry_operation(mock_operation)

        assert exc_info.value == exception
        mock_operation.assert_called_once()

    def test_retry_operation_rate_limit(self, client):
        """Test retry operation handles rate limit."""
        reset_time = int((datetime.now() + timedelta(seconds=1)).timestamp())
        rate_limit_exception = RateLimitExceededException(
            status=403, data={"rate": {"reset": reset_time}}, headers={}
        )
        mock_operation = Mock(side_effect=[rate_limit_exception, "success"])

        with patch.object(client, "_handle_rate_limit") as mock_handle:
            result = client._retry_operation(mock_operation)

        assert result == "success"
        mock_handle.assert_called_once_with(rate_limit_exception)
        assert mock_operation.call_count == 2

    def test_get_repository(self, client, mock_github):
        """Test get repository."""
        mock_repo = Mock()
        client._github.get_repo.return_value = mock_repo

        result = client.get_repository("owner/repo")

        assert result == mock_repo
        client._github.get_repo.assert_called_once_with("owner/repo")

    def test_get_issue(self, client, mock_github):
        """Test get issue."""
        mock_repo = Mock()
        mock_issue = Mock()
        mock_repo.get_issue.return_value = mock_issue
        client._github.get_repo.return_value = mock_repo

        result = client.get_issue("owner/repo", 123)

        assert result == mock_issue
        client._github.get_repo.assert_called_once_with("owner/repo")
        mock_repo.get_issue.assert_called_once_with(123)

    def test_list_issues(self, client, mock_github):
        """Test list issues."""
        mock_repo = Mock()
        mock_issues = [Mock(), Mock(), Mock()]
        mock_repo.get_issues.return_value = mock_issues
        client._github.get_repo.return_value = mock_repo

        result = client.list_issues(
            "owner/repo",
            state="open",
            labels=["bug", "enhancement"],
            assignee="user123",
            sort="updated",
            direction="asc",
        )

        assert result == mock_issues
        mock_repo.get_issues.assert_called_once_with(
            state="open",
            labels=["bug", "enhancement"],
            assignee="user123",
            sort="updated",
            direction="asc",
        )

    def test_create_issue(self, client, mock_github):
        """Test create issue."""
        mock_repo = Mock()
        mock_issue = Mock()
        mock_repo.create_issue.return_value = mock_issue
        client._github.get_repo.return_value = mock_repo

        result = client.create_issue(
            "owner/repo",
            title="Test Issue",
            body="Issue body",
            labels=["bug"],
            assignees=["user123"],
        )

        assert result == mock_issue
        mock_repo.create_issue.assert_called_once_with(
            title="Test Issue", body="Issue body", labels=["bug"], assignees=["user123"]
        )

    def test_create_pull_request(self, client, mock_github):
        """Test create pull request."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_repo.create_pull.return_value = mock_pr
        client._github.get_repo.return_value = mock_repo

        result = client.create_pull_request(
            "owner/repo",
            title="Test PR",
            body="PR body",
            head="feature-branch",
            base="main",
            draft=True,
        )

        assert result == mock_pr
        mock_repo.create_pull.assert_called_once_with(
            title="Test PR", body="PR body", head="feature-branch", base="main", draft=True
        )

    def test_get_pull_request(self, client, mock_github):
        """Test get pull request."""
        mock_repo = Mock()
        mock_pr = Mock()
        mock_repo.get_pull.return_value = mock_pr
        client._github.get_repo.return_value = mock_repo

        result = client.get_pull_request("owner/repo", 456)

        assert result == mock_pr
        mock_repo.get_pull.assert_called_once_with(456)

    def test_list_pull_requests(self, client, mock_github):
        """Test list pull requests."""
        mock_repo = Mock()
        mock_prs = [Mock(), Mock()]
        mock_repo.get_pulls.return_value = mock_prs
        client._github.get_repo.return_value = mock_repo

        result = client.list_pull_requests(
            "owner/repo",
            state="closed",
            sort="popularity",
            direction="desc",
            base="main",
            head="owner:feature",
        )

        assert result == mock_prs
        mock_repo.get_pulls.assert_called_once_with(
            state="closed", sort="popularity", direction="desc", base="main", head="owner:feature"
        )

    def test_get_rate_limit(self, client, mock_github):
        """Test get rate limit."""
        mock_rate_limit = Mock()
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.remaining = 4999
        mock_rate_limit.core.reset = datetime.now() + timedelta(hours=1)
        mock_rate_limit.search.limit = 30
        mock_rate_limit.search.remaining = 29
        mock_rate_limit.search.reset = datetime.now() + timedelta(minutes=1)

        client._github.get_rate_limit.return_value = mock_rate_limit

        result = client.get_rate_limit()

        assert result["core"]["limit"] == 5000
        assert result["core"]["remaining"] == 4999
        assert result["search"]["limit"] == 30
        assert result["search"]["remaining"] == 29
        assert "reset" in result["core"]
        assert "reset" in result["search"]

    def test_close(self, client):
        """Test client cleanup."""
        with patch.object(client._token_manager, "revoke") as mock_revoke:
            client.close()

        mock_revoke.assert_called_once()
