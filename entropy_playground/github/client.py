"""
GitHub API client with secure token management and retry logic.
"""

import os
import time
from datetime import datetime
from typing import Any

from github import Github, GithubException, RateLimitExceededException
from github.GithubObject import NotSet
from github.Issue import Issue
from github.PullRequest import PullRequest
from github.Repository import Repository

from entropy_playground.logging.logger import get_logger

logger = get_logger(__name__)


class GitHubTokenManager:
    """Secure token management for GitHub API access."""

    def __init__(self, token: str | None = None):
        """
        Initialize token manager.

        Args:
            token: GitHub personal access token. If not provided,
                  will attempt to read from GITHUB_TOKEN environment variable.
        """
        self._token = token or os.environ.get("GITHUB_TOKEN")
        if not self._token:
            raise ValueError(
                "GitHub token not provided. Set GITHUB_TOKEN environment variable "
                "or pass token explicitly."
            )
        self._validate_token()

    def _validate_token(self) -> None:
        """Validate token format without making API calls."""
        if not self._token:
            raise ValueError("Token cannot be empty")

        # GitHub tokens should be at least 40 characters
        if len(self._token) < 40:
            raise ValueError("Invalid token format")

        # Check for common token prefixes
        valid_prefixes = ("ghp_", "ghs_", "gho_", "ghu_", "ghr_")
        if not any(self._token.startswith(prefix) for prefix in valid_prefixes):
            logger.warning("Token does not match expected GitHub token format")

    def get_token(self) -> str | None:
        """Get the GitHub token."""
        return self._token

    def revoke(self) -> None:
        """Clear the token from memory."""
        self._token = None


class GitHubClient:
    """
    Enhanced GitHub API client with rate limiting and retry logic.
    """

    DEFAULT_RETRY_COUNT = 3
    DEFAULT_RETRY_DELAY = 1.0  # seconds

    def __init__(
        self,
        token: str | None = None,
        base_url: str | None = None,
        retry_count: int = DEFAULT_RETRY_COUNT,
        retry_delay: float = DEFAULT_RETRY_DELAY,
    ):
        """
        Initialize GitHub client.

        Args:
            token: GitHub personal access token
            base_url: GitHub API base URL (for GitHub Enterprise)
            retry_count: Number of retry attempts for failed requests
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self._token_manager = GitHubTokenManager(token)
        self._base_url = base_url
        self._retry_count = retry_count
        self._retry_delay = retry_delay

        # Initialize PyGithub client
        # Use token directly for compatibility with older PyGithub versions
        token = self._token_manager.get_token()
        if base_url:
            self._github = Github(token if token else None, base_url=base_url)
        else:
            self._github = Github(token if token else None)

        # Track rate limit info
        self._rate_limit_reset: datetime | None = None

        logger.info(
            "GitHub client initialized",
            extra={
                "base_url": base_url or "https://api.github.com",
                "retry_count": retry_count,
                "retry_delay": retry_delay,
            },
        )

    def _handle_rate_limit(self, exception: RateLimitExceededException) -> None:
        """Handle rate limit exceeded exception."""
        reset_time = datetime.fromtimestamp(exception.data["rate"]["reset"])
        self._rate_limit_reset = reset_time

        wait_time = (reset_time - datetime.now()).total_seconds()
        logger.warning(
            f"Rate limit exceeded. Waiting {wait_time:.0f} seconds until reset",
            extra={"reset_time": reset_time.isoformat(), "wait_seconds": wait_time},
        )

        if wait_time > 0:
            time.sleep(wait_time + 1)  # Add 1 second buffer

    def _retry_operation(self, operation: Any, *args: Any, **kwargs: Any) -> Any:
        """
        Execute an operation with retry logic.

        Args:
            operation: The operation to execute
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation

        Returns:
            The result of the operation

        Raises:
            GithubException: If all retries are exhausted
        """
        last_exception = None
        delay = self._retry_delay

        for attempt in range(self._retry_count):
            try:
                return operation(*args, **kwargs)
            except RateLimitExceededException as e:
                self._handle_rate_limit(e)
                # Reset delay after rate limit wait
                delay = self._retry_delay
            except GithubException as e:
                last_exception = e
                logger.warning(
                    f"GitHub API error (attempt {attempt + 1}/{self._retry_count}): {e}",
                    extra={"status": e.status, "data": e.data, "attempt": attempt + 1},
                )

                # Don't retry on certain status codes
                if e.status in [401, 403, 404, 422]:
                    raise

                if attempt < self._retry_count - 1:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff

        if last_exception is not None:
            raise last_exception
        else:
            raise RuntimeError("Operation failed with no exception captured")

    def get_repository(self, repo_name: str) -> Repository:
        """
        Get a repository by name.

        Args:
            repo_name: Repository name in format "owner/repo"

        Returns:
            Repository object
        """
        result: Repository = self._retry_operation(self._github.get_repo, repo_name)
        return result

    def get_issue(self, repo_name: str, issue_number: int) -> Issue:
        """
        Get an issue by number.

        Args:
            repo_name: Repository name in format "owner/repo"
            issue_number: Issue number

        Returns:
            Issue object
        """
        repo = self.get_repository(repo_name)
        result: Issue = self._retry_operation(repo.get_issue, issue_number)
        return result

    def list_issues(
        self,
        repo_name: str,
        state: str = "open",
        labels: list[str] | None = None,
        assignee: str | None = None,
        sort: str = "created",
        direction: str = "desc",
    ) -> list[Issue]:
        """
        List issues for a repository.

        Args:
            repo_name: Repository name in format "owner/repo"
            state: Issue state ("open", "closed", "all")
            labels: Filter by labels
            assignee: Filter by assignee
            sort: Sort by ("created", "updated", "comments")
            direction: Sort direction ("asc", "desc")

        Returns:
            List of Issue objects
        """
        repo = self.get_repository(repo_name)

        def _get_issues() -> list[Issue]:
            return list(
                repo.get_issues(
                    state=state,
                    labels=labels or [],
                    assignee=assignee or NotSet,
                    sort=sort,
                    direction=direction,
                )
            )

        result: list[Issue] = self._retry_operation(_get_issues)
        return result

    def create_issue(
        self,
        repo_name: str,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignees: list[str] | None = None,
    ) -> Issue:
        """
        Create a new issue.

        Args:
            repo_name: Repository name in format "owner/repo"
            title: Issue title
            body: Issue body
            labels: List of label names
            assignees: List of assignee usernames

        Returns:
            Created Issue object
        """
        repo = self.get_repository(repo_name)
        result: Issue = self._retry_operation(
            repo.create_issue,
            title=title,
            body=body,
            labels=labels or [],
            assignees=assignees or [],
        )
        return result

    def create_pull_request(
        self,
        repo_name: str,
        title: str,
        body: str | None = None,
        head: str | None = None,
        base: str = "main",
        draft: bool = False,
    ) -> PullRequest:
        """
        Create a new pull request.

        Args:
            repo_name: Repository name in format "owner/repo"
            title: PR title
            body: PR description
            head: Head branch
            base: Base branch (default: "main")
            draft: Create as draft PR

        Returns:
            Created PullRequest object
        """
        repo = self.get_repository(repo_name)
        result: PullRequest = self._retry_operation(
            repo.create_pull, title=title, body=body, head=head, base=base, draft=draft
        )
        return result

    def get_pull_request(self, repo_name: str, pr_number: int) -> PullRequest:
        """
        Get a pull request by number.

        Args:
            repo_name: Repository name in format "owner/repo"
            pr_number: Pull request number

        Returns:
            PullRequest object
        """
        repo = self.get_repository(repo_name)
        result: PullRequest = self._retry_operation(repo.get_pull, pr_number)
        return result

    def list_pull_requests(
        self,
        repo_name: str,
        state: str = "open",
        sort: str = "created",
        direction: str = "desc",
        base: str | None = None,
        head: str | None = None,
    ) -> list[PullRequest]:
        """
        List pull requests for a repository.

        Args:
            repo_name: Repository name in format "owner/repo"
            state: PR state ("open", "closed", "all")
            sort: Sort by ("created", "updated", "popularity")
            direction: Sort direction ("asc", "desc")
            base: Filter by base branch
            head: Filter by head branch

        Returns:
            List of PullRequest objects
        """
        repo = self.get_repository(repo_name)

        def _get_pulls() -> list[PullRequest]:
            return list(
                repo.get_pulls(
                    state=state,
                    sort=sort,
                    direction=direction,
                    base=base or NotSet,
                    head=head or NotSet,
                )
            )

        result: list[PullRequest] = self._retry_operation(_get_pulls)
        return result

    def get_rate_limit(self) -> dict[str, Any]:
        """
        Get current rate limit status.

        Returns:
            Dictionary with rate limit information
        """
        rate_limit = self._retry_operation(self._github.get_rate_limit)
        return {
            "core": {
                "limit": rate_limit.core.limit,
                "remaining": rate_limit.core.remaining,
                "reset": rate_limit.core.reset.isoformat(),
            },
            "search": {
                "limit": rate_limit.search.limit,
                "remaining": rate_limit.search.remaining,
                "reset": rate_limit.search.reset.isoformat(),
            },
        }

    def close(self) -> None:
        """Clean up resources."""
        self._token_manager.revoke()
        logger.info("GitHub client closed")
