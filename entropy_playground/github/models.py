"""
Pydantic models for GitHub API objects.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class IssueState(str, Enum):
    """Issue state enumeration."""
    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"


class PullRequestState(str, Enum):
    """Pull request state enumeration."""
    OPEN = "open"
    CLOSED = "closed"
    ALL = "all"


class User(BaseModel):
    """GitHub user model."""
    login: str
    id: int
    avatar_url: HttpUrl
    html_url: HttpUrl
    type: str = Field(description="User type (User, Organization, Bot)")
    site_admin: bool = False


class Label(BaseModel):
    """GitHub label model."""
    id: int
    name: str
    color: str
    description: str | None = None
    default: bool = False


class Milestone(BaseModel):
    """GitHub milestone model."""
    id: int
    number: int
    title: str
    description: str | None = None
    state: str
    created_at: datetime
    updated_at: datetime | None = None
    due_on: datetime | None = None
    closed_at: datetime | None = None


class Repository(BaseModel):
    """GitHub repository model."""
    id: int
    name: str
    full_name: str
    owner: User
    private: bool
    description: str | None = None
    fork: bool = False
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime | None = None
    size: int
    stargazers_count: int
    watchers_count: int
    language: str | None = None
    forks_count: int
    open_issues_count: int
    default_branch: str
    topics: list[str] = Field(default_factory=list)
    visibility: str
    html_url: HttpUrl
    clone_url: HttpUrl
    ssh_url: str


class Issue(BaseModel):
    """GitHub issue model."""
    id: int
    number: int
    title: str
    body: str | None = None
    state: IssueState
    locked: bool = False
    assignee: User | None = None
    assignees: list[User] = Field(default_factory=list)
    labels: list[Label] = Field(default_factory=list)
    milestone: Milestone | None = None
    created_at: datetime
    updated_at: datetime | None = None
    closed_at: datetime | None = None
    user: User
    html_url: HttpUrl
    repository_url: HttpUrl
    comments: int = 0

    model_config = {"use_enum_values": True}


class PullRequestBranch(BaseModel):
    """Pull request branch information."""
    label: str
    ref: str
    sha: str
    user: User | None = None
    repo: Repository | None = None


class PullRequest(BaseModel):
    """GitHub pull request model."""
    id: int
    number: int
    title: str
    body: str | None = None
    state: PullRequestState
    locked: bool = False
    assignee: User | None = None
    assignees: list[User] = Field(default_factory=list)
    labels: list[Label] = Field(default_factory=list)
    milestone: Milestone | None = None
    created_at: datetime
    updated_at: datetime | None = None
    closed_at: datetime | None = None
    merged_at: datetime | None = None
    user: User
    html_url: HttpUrl
    diff_url: HttpUrl
    patch_url: HttpUrl
    issue_url: HttpUrl | None = None
    commits: int = 0
    additions: int = 0
    deletions: int = 0
    changed_files: int = 0
    comments: int = 0
    review_comments: int = 0
    maintainer_can_modify: bool = False
    draft: bool = False
    head: PullRequestBranch
    base: PullRequestBranch
    merge_commit_sha: str | None = None
    mergeable: bool | None = None
    mergeable_state: str | None = None
    merged: bool = False
    merged_by: User | None = None

    model_config = {"use_enum_values": True}


class Comment(BaseModel):
    """GitHub comment model."""
    id: int
    body: str
    user: User
    created_at: datetime
    updated_at: datetime | None = None
    html_url: HttpUrl
    issue_url: HttpUrl | None = None
    author_association: str


class Review(BaseModel):
    """Pull request review model."""
    id: int
    user: User
    body: str | None = None
    state: str  # APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED, PENDING
    submitted_at: datetime | None = None
    commit_id: str
    html_url: HttpUrl
    pull_request_url: HttpUrl
    author_association: str


class RateLimit(BaseModel):
    """GitHub rate limit information."""
    limit: int
    remaining: int
    reset: datetime
    used: int = 0

    @property
    def is_exceeded(self) -> bool:
        """Check if rate limit is exceeded."""
        return self.remaining == 0

    @property
    def reset_in_seconds(self) -> float:
        """Get seconds until rate limit reset."""
        return max(0, (self.reset - datetime.now()).total_seconds())


class RateLimitInfo(BaseModel):
    """Complete rate limit information."""
    core: RateLimit
    search: RateLimit
    graphql: RateLimit | None = None
    integration_manifest: RateLimit | None = None
    code_scanning_upload: RateLimit | None = None


class WebhookEvent(BaseModel):
    """GitHub webhook event model."""
    action: str
    sender: User
    repository: Repository | None = None
    organization: User | None = None
    installation: dict[str, Any] | None = None

    # Event-specific fields
    issue: Issue | None = None
    pull_request: PullRequest | None = None
    comment: Comment | None = None
    review: Review | None = None

    # Additional event data
    changes: dict[str, Any] | None = None

    model_config = {"extra": "allow"}  # Allow additional fields for various event types


class GitHubError(BaseModel):
    """GitHub API error response."""
    message: str
    documentation_url: HttpUrl | None = None
    errors: list[dict[str, Any]] | None = None
    status: int | None = None

