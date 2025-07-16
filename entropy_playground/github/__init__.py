"""
GitHub integration module for Entropy-Playground.

Handles all interactions with the GitHub API including:
- Issue management
- Pull request operations
- Code reviews
- Repository operations
"""

from .client import GitHubClient, GitHubTokenManager
from .models import (
    Comment,
    GitHubError,
    Issue,
    IssueState,
    Label,
    Milestone,
    PullRequest,
    PullRequestBranch,
    PullRequestState,
    RateLimit,
    RateLimitInfo,
    Repository,
    Review,
    User,
    WebhookEvent,
)

__all__ = [
    # Client
    "GitHubClient",
    "GitHubTokenManager",
    # Models
    "User",
    "Label",
    "Milestone",
    "Repository",
    "Issue",
    "PullRequest",
    "PullRequestBranch",
    "Comment",
    "Review",
    "RateLimit",
    "RateLimitInfo",
    "WebhookEvent",
    "GitHubError",
    "IssueState",
    "PullRequestState",
]

