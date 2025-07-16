"""
Unit tests for GitHub Pydantic models.
"""

from datetime import datetime, timedelta
from typing import Dict, Any

import pytest
from pydantic import ValidationError

from entropy_playground.github.models import (
    User, Label, Milestone, Repository, Issue, PullRequest,
    PullRequestBranch, Comment, Review, RateLimit, RateLimitInfo,
    WebhookEvent, GitHubError, IssueState, PullRequestState
)


class TestEnums:
    """Test enumeration classes."""
    
    def test_issue_state_values(self):
        """Test IssueState enum values."""
        assert IssueState.OPEN == "open"
        assert IssueState.CLOSED == "closed"
        assert IssueState.ALL == "all"
    
    def test_pull_request_state_values(self):
        """Test PullRequestState enum values."""
        assert PullRequestState.OPEN == "open"
        assert PullRequestState.CLOSED == "closed"
        assert PullRequestState.ALL == "all"


class TestUser:
    """Test User model."""
    
    def test_valid_user(self):
        """Test creating a valid user."""
        user = User(
            login="octocat",
            id=1,
            avatar_url="https://github.com/images/error/octocat_happy.gif",
            html_url="https://github.com/octocat",
            type="User"
        )
        assert user.login == "octocat"
        assert user.id == 1
        assert user.site_admin is False
    
    def test_user_with_all_fields(self):
        """Test user with all fields."""
        user = User(
            login="octocat",
            id=1,
            avatar_url="https://github.com/images/error/octocat_happy.gif",
            html_url="https://github.com/octocat",
            type="Organization",
            site_admin=True
        )
        assert user.type == "Organization"
        assert user.site_admin is True
    
    def test_invalid_url(self):
        """Test user with invalid URL."""
        with pytest.raises(ValidationError):
            User(
                login="octocat",
                id=1,
                avatar_url="not-a-url",
                html_url="https://github.com/octocat",
                type="User"
            )


class TestLabel:
    """Test Label model."""
    
    def test_valid_label(self):
        """Test creating a valid label."""
        label = Label(
            id=1,
            name="bug",
            color="fc2929"
        )
        assert label.name == "bug"
        assert label.color == "fc2929"
        assert label.description is None
        assert label.default is False
    
    def test_label_with_all_fields(self):
        """Test label with all fields."""
        label = Label(
            id=1,
            name="bug",
            color="fc2929",
            description="Something isn't working",
            default=True
        )
        assert label.description == "Something isn't working"
        assert label.default is True


class TestMilestone:
    """Test Milestone model."""
    
    def test_valid_milestone(self):
        """Test creating a valid milestone."""
        now = datetime.now()
        milestone = Milestone(
            id=1,
            number=1,
            title="v1.0",
            state="open",
            created_at=now
        )
        assert milestone.title == "v1.0"
        assert milestone.state == "open"
        assert milestone.created_at == now
    
    def test_milestone_with_dates(self):
        """Test milestone with all date fields."""
        now = datetime.now()
        milestone = Milestone(
            id=1,
            number=1,
            title="v1.0",
            description="First release",
            state="closed",
            created_at=now,
            updated_at=now + timedelta(days=1),
            due_on=now + timedelta(days=30),
            closed_at=now + timedelta(days=25)
        )
        assert milestone.description == "First release"
        assert milestone.due_on == now + timedelta(days=30)


class TestRepository:
    """Test Repository model."""
    
    @pytest.fixture
    def valid_user(self):
        """Create a valid user for testing."""
        return User(
            login="octocat",
            id=1,
            avatar_url="https://github.com/images/error/octocat_happy.gif",
            html_url="https://github.com/octocat",
            type="User"
        )
    
    def test_valid_repository(self, valid_user):
        """Test creating a valid repository."""
        now = datetime.now()
        repo = Repository(
            id=1,
            name="Hello-World",
            full_name="octocat/Hello-World",
            owner=valid_user,
            private=False,
            created_at=now,
            updated_at=now,
            size=180,
            stargazers_count=80,
            watchers_count=80,
            forks_count=9,
            open_issues_count=0,
            default_branch="main",
            visibility="public",
            html_url="https://github.com/octocat/Hello-World",
            clone_url="https://github.com/octocat/Hello-World.git",
            ssh_url="git@github.com:octocat/Hello-World.git"
        )
        assert repo.name == "Hello-World"
        assert repo.owner.login == "octocat"
        assert repo.fork is False
    
    def test_repository_with_optional_fields(self, valid_user):
        """Test repository with optional fields."""
        now = datetime.now()
        repo = Repository(
            id=1,
            name="Hello-World",
            full_name="octocat/Hello-World",
            owner=valid_user,
            private=True,
            description="My first repository",
            fork=True,
            created_at=now,
            updated_at=now,
            pushed_at=now,
            size=180,
            stargazers_count=80,
            watchers_count=80,
            language="Python",
            forks_count=9,
            open_issues_count=2,
            default_branch="develop",
            topics=["python", "github", "api"],
            visibility="private",
            html_url="https://github.com/octocat/Hello-World",
            clone_url="https://github.com/octocat/Hello-World.git",
            ssh_url="git@github.com:octocat/Hello-World.git"
        )
        assert repo.description == "My first repository"
        assert repo.language == "Python"
        assert len(repo.topics) == 3


class TestIssue:
    """Test Issue model."""
    
    @pytest.fixture
    def valid_user(self):
        """Create a valid user for testing."""
        return User(
            login="octocat",
            id=1,
            avatar_url="https://github.com/images/error/octocat_happy.gif",
            html_url="https://github.com/octocat",
            type="User"
        )
    
    def test_valid_issue(self, valid_user):
        """Test creating a valid issue."""
        now = datetime.now()
        issue = Issue(
            id=1,
            number=1347,
            title="Found a bug",
            state=IssueState.OPEN,
            created_at=now,
            user=valid_user,
            html_url="https://github.com/octocat/Hello-World/issues/1347",
            repository_url="https://api.github.com/repos/octocat/Hello-World"
        )
        assert issue.number == 1347
        assert issue.state == "open"  # Enum value
        assert issue.locked is False
    
    def test_issue_with_labels_and_assignees(self, valid_user):
        """Test issue with labels and assignees."""
        label = Label(id=1, name="bug", color="fc2929")
        issue = Issue(
            id=1,
            number=1347,
            title="Found a bug",
            body="## Description\nI found a bug!",
            state=IssueState.CLOSED,
            locked=True,
            assignee=valid_user,
            assignees=[valid_user],
            labels=[label],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            closed_at=datetime.now(),
            user=valid_user,
            html_url="https://github.com/octocat/Hello-World/issues/1347",
            repository_url="https://api.github.com/repos/octocat/Hello-World",
            comments=5
        )
        assert issue.body == "## Description\nI found a bug!"
        assert len(issue.labels) == 1
        assert issue.labels[0].name == "bug"
        assert issue.comments == 5


class TestPullRequest:
    """Test PullRequest model."""
    
    @pytest.fixture
    def valid_user(self):
        """Create a valid user for testing."""
        return User(
            login="octocat",
            id=1,
            avatar_url="https://github.com/images/error/octocat_happy.gif",
            html_url="https://github.com/octocat",
            type="User"
        )
    
    @pytest.fixture
    def valid_branch(self, valid_user):
        """Create a valid branch for testing."""
        return PullRequestBranch(
            label="octocat:new-feature",
            ref="new-feature",
            sha="aa218f56b14c9653891f9e74264a383fa43fefbd",
            user=valid_user
        )
    
    def test_valid_pull_request(self, valid_user, valid_branch):
        """Test creating a valid pull request."""
        now = datetime.now()
        pr = PullRequest(
            id=1,
            number=1,
            title="Amazing new feature",
            state=PullRequestState.OPEN,
            created_at=now,
            user=valid_user,
            html_url="https://github.com/octocat/Hello-World/pull/1",
            diff_url="https://github.com/octocat/Hello-World/pull/1.diff",
            patch_url="https://github.com/octocat/Hello-World/pull/1.patch",
            head=valid_branch,
            base=valid_branch
        )
        assert pr.number == 1
        assert pr.state == "open"
        assert pr.draft is False
        assert pr.merged is False
    
    def test_merged_pull_request(self, valid_user, valid_branch):
        """Test merged pull request."""
        now = datetime.now()
        pr = PullRequest(
            id=1,
            number=1,
            title="Amazing new feature",
            state=PullRequestState.CLOSED,
            created_at=now,
            updated_at=now,
            closed_at=now,
            merged_at=now,
            user=valid_user,
            html_url="https://github.com/octocat/Hello-World/pull/1",
            diff_url="https://github.com/octocat/Hello-World/pull/1.diff",
            patch_url="https://github.com/octocat/Hello-World/pull/1.patch",
            head=valid_branch,
            base=valid_branch,
            merged=True,
            merged_by=valid_user,
            merge_commit_sha="e5bd3914e2e596debea16f433f57875b5b90bcd6",
            commits=3,
            additions=100,
            deletions=50,
            changed_files=5
        )
        assert pr.merged is True
        assert pr.merged_by.login == "octocat"
        assert pr.commits == 3


class TestRateLimit:
    """Test RateLimit model."""
    
    def test_valid_rate_limit(self):
        """Test creating a valid rate limit."""
        reset_time = datetime.now() + timedelta(hours=1)
        rate_limit = RateLimit(
            limit=5000,
            remaining=4999,
            reset=reset_time
        )
        assert rate_limit.limit == 5000
        assert rate_limit.remaining == 4999
        assert rate_limit.used == 0
    
    def test_rate_limit_exceeded(self):
        """Test rate limit exceeded check."""
        rate_limit = RateLimit(
            limit=5000,
            remaining=0,
            reset=datetime.now() + timedelta(hours=1),
            used=5000
        )
        assert rate_limit.is_exceeded is True
    
    def test_rate_limit_not_exceeded(self):
        """Test rate limit not exceeded."""
        rate_limit = RateLimit(
            limit=5000,
            remaining=1,
            reset=datetime.now() + timedelta(hours=1),
            used=4999
        )
        assert rate_limit.is_exceeded is False
    
    def test_reset_in_seconds_future(self):
        """Test reset time calculation for future reset."""
        reset_time = datetime.now() + timedelta(hours=1)
        rate_limit = RateLimit(
            limit=5000,
            remaining=0,
            reset=reset_time
        )
        seconds = rate_limit.reset_in_seconds
        assert 3595 <= seconds <= 3605  # Allow small time variance
    
    def test_reset_in_seconds_past(self):
        """Test reset time calculation for past reset."""
        reset_time = datetime.now() - timedelta(hours=1)
        rate_limit = RateLimit(
            limit=5000,
            remaining=5000,
            reset=reset_time
        )
        assert rate_limit.reset_in_seconds == 0


class TestWebhookEvent:
    """Test WebhookEvent model."""
    
    @pytest.fixture
    def valid_user(self):
        """Create a valid user for testing."""
        return User(
            login="octocat",
            id=1,
            avatar_url="https://github.com/images/error/octocat_happy.gif",
            html_url="https://github.com/octocat",
            type="User"
        )
    
    def test_issue_webhook_event(self, valid_user):
        """Test issue webhook event."""
        issue = Issue(
            id=1,
            number=1,
            title="Test issue",
            state=IssueState.OPEN,
            created_at=datetime.now(),
            user=valid_user,
            html_url="https://github.com/test/repo/issues/1",
            repository_url="https://api.github.com/repos/test/repo"
        )
        
        event = WebhookEvent(
            action="opened",
            sender=valid_user,
            issue=issue
        )
        assert event.action == "opened"
        assert event.issue.title == "Test issue"
        assert event.pull_request is None
    
    def test_webhook_event_extra_fields(self, valid_user):
        """Test webhook event with extra fields."""
        event = WebhookEvent(
            action="created",
            sender=valid_user,
            extra_field="extra_value",
            another_field={"nested": "data"}
        )
        assert event.action == "created"
        assert event.extra_field == "extra_value"
        assert event.another_field["nested"] == "data"


class TestGitHubError:
    """Test GitHubError model."""
    
    def test_simple_error(self):
        """Test simple error message."""
        error = GitHubError(message="Not Found")
        assert error.message == "Not Found"
        assert error.documentation_url is None
        assert error.errors is None
    
    def test_error_with_details(self):
        """Test error with all fields."""
        error = GitHubError(
            message="Validation Failed",
            documentation_url="https://docs.github.com/rest/reference/repos#create-a-repository",
            errors=[
                {"field": "name", "code": "missing"},
                {"field": "name", "code": "invalid"}
            ],
            status=422
        )
        assert error.message == "Validation Failed"
        assert error.status == 422
        assert len(error.errors) == 2