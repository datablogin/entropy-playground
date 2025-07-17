# Contributing to Entropy-Playground

Thank you for your interest in contributing to Entropy-Playground! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. We are committed to providing a welcoming and inspiring community for all. Please be respectful, inclusive, and considerate in all interactions.

## How to Contribute

### Reporting Issues

- Check if the issue already exists in the [issue tracker](https://github.com/datablogin/entropy-playground/issues)
- Use the appropriate issue template
- Provide clear description and steps to reproduce
- Include relevant logs and error messages

### Suggesting Features

- Open a discussion in [GitHub Discussions](https://github.com/datablogin/entropy-playground/discussions)
- Describe the use case and benefits
- Consider implementation complexity

### Contributing Code

1. **Fork the Repository**
   ```bash
   gh repo fork datablogin/entropy-playground
   ```

2. **Clone Your Fork**
   ```bash
   git clone https://github.com/YOUR_USERNAME/entropy-playground.git
   cd entropy-playground
   ```

3. **Set Up Development Environment**
   
   #### Prerequisites
   - Python 3.11 or higher
   - Docker and Docker Compose (for integration testing)
   - AWS CLI (for infrastructure development)
   - Terraform (for infrastructure as code)
   
   #### Setup Steps
   ```bash
   # Create virtual environment
   uv venv --python 3.11
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install development dependencies
   uv pip install -e ".[dev]"
   
   # Install pre-commit hooks
   pre-commit install
   
   # Verify installation
   entropy-playground --version
   
   # Run initial tests to ensure setup is correct
   pytest tests/unit/
   ```
   
   #### Environment Variables
   Create a `.env` file for local development (never commit this):
   ```bash
   GITHUB_TOKEN=your_github_token
   REDIS_URL=redis://localhost:6379
   AWS_REGION=us-east-1
   LOG_LEVEL=DEBUG
   ENTROPY_WORKSPACE=/tmp/entropy-workspace
   ```

4. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

5. **Make Your Changes**
   - Write clean, readable code
   - Add tests for new functionality
   - Update documentation as needed
   - Follow the project's coding standards

6. **Run Tests and Linting**
   ```bash
   # Run tests
   pytest
   
   # Run linting
   ruff check .
   black --check .
   mypy .
   ```

7. **Commit Your Changes**
   ```bash
   git add .
   git commit -m "feat: add amazing new feature"
   ```

   Follow conventional commit format:
   - `feat:` for new features
   - `fix:` for bug fixes
   - `docs:` for documentation
   - `test:` for tests
   - `refactor:` for refactoring
   - `chore:` for maintenance

8. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   gh pr create
   ```

## Development Guidelines

### Code Style

#### Python Standards
- Follow [PEP 8](https://pep8.org/) with these specifications:
  - Maximum line length: 100 characters
  - Use 4 spaces for indentation (no tabs)
  - Two blank lines between top-level definitions
  - One blank line between method definitions

#### Type Hints
- Required for all function signatures
- Use `from typing import` for complex types
- Example:
  ```python
  from typing import List, Optional, Dict, Any
  
  def process_issues(issues: List[Dict[str, Any]], 
                    assignee: Optional[str] = None) -> List[Issue]:
      """Process GitHub issues with optional assignee filter."""
      pass
  ```

#### Naming Conventions
- Classes: `PascalCase` (e.g., `CoderAgent`, `GitHubClient`)
- Functions/variables: `snake_case` (e.g., `get_issue_details`, `max_retries`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`, `MAX_WORKERS`)
- Private methods: prefix with underscore (e.g., `_internal_method`)

#### Docstrings
- Use Google-style docstrings for all public functions/classes
- Include:
  - Brief description
  - Args with types and descriptions
  - Returns with type and description
  - Raises for exceptions
  - Examples for complex functions

#### Import Order
1. Standard library imports
2. Third-party imports
3. Local application imports

Each group separated by a blank line, sorted alphabetically.

#### Error Handling
- Use specific exceptions, not bare `except:`
- Create custom exceptions in `entropy_playground.exceptions`
- Always log exceptions with appropriate context
- Example:
  ```python
  try:
      result = github_client.get_issue(issue_id)
  except GitHubAPIError as e:
      logger.error("Failed to fetch issue", 
                  issue_id=issue_id, 
                  error=str(e))
      raise
  ```

### Testing

#### Test Requirements
- **Coverage**: Maintain minimum 80% code coverage
- **New Features**: Must include comprehensive unit tests
- **Bug Fixes**: Must include regression tests
- **Integration Tests**: Required for external service interactions

#### Test Structure
```
tests/
├── unit/           # Fast, isolated unit tests
├── integration/    # Tests with external dependencies
├── fixtures/       # Shared test fixtures
└── conftest.py     # Pytest configuration
```

#### Writing Tests
- Use descriptive test names: `test_<what>_<condition>_<expected_result>`
- One assertion per test when possible
- Use pytest fixtures for setup/teardown
- Mock external dependencies (GitHub API, Redis, AWS)

#### Test Examples
```python
import pytest
from unittest.mock import Mock, patch

class TestCoderAgent:
    @pytest.fixture
    def mock_github_client(self):
        """Fixture for mocked GitHub client."""
        return Mock(spec=GitHubClient)
    
    def test_create_pull_request_success(self, mock_github_client):
        """Test successful PR creation with valid issue."""
        # Arrange
        agent = CoderAgent(github_client=mock_github_client)
        mock_github_client.get_issue.return_value = Mock(state="open")
        
        # Act
        pr = agent.create_pull_request(issue_id=123)
        
        # Assert
        assert pr.title.startswith("Fix #123")
        mock_github_client.create_pull_request.assert_called_once()
```

#### Running Tests
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=entropy_playground --cov-report=term-missing

# Run specific test file
pytest tests/unit/test_coder_agent.py

# Run with verbose output
pytest -vv

# Run only marked tests
pytest -m "not slow"
```

#### Performance Testing
- Mark slow tests with `@pytest.mark.slow`
- Set timeouts for long-running tests
- Profile critical paths

### Documentation

#### Documentation Requirements
- **Docstrings**: Required for all public modules, classes, and functions
- **Type Hints**: Required for better IDE support and documentation
- **README Updates**: Update when adding major features
- **Architecture Docs**: Update ARCHITECTURE.md for design changes
- **API Docs**: Document all public APIs with examples

#### Documentation Style
- Use clear, concise language
- Include code examples for complex features
- Explain the "why" not just the "what"
- Keep examples up-to-date and tested

#### Example Documentation
```python
def analyze_code_changes(pr_number: int, 
                        base_branch: str = "main") -> CodeAnalysis:
    """Analyze code changes in a pull request.
    
    Performs static analysis, security checks, and style validation
    on all changed files in the specified pull request.
    
    Args:
        pr_number: The GitHub pull request number to analyze.
        base_branch: The base branch to compare against. Defaults to "main".
    
    Returns:
        CodeAnalysis: Analysis results including:
            - security_issues: List of potential security vulnerabilities
            - style_violations: List of code style issues
            - complexity_metrics: Code complexity measurements
            - test_coverage: Coverage delta for changed lines
    
    Raises:
        GitHubAPIError: If the PR cannot be accessed.
        AnalysisError: If code analysis fails.
    
    Example:
        >>> analysis = analyze_code_changes(pr_number=456)
        >>> if analysis.security_issues:
        ...     logger.warning(f"Found {len(analysis.security_issues)} security issues")
        >>> print(f"Coverage: {analysis.test_coverage:.1f}%")
        Coverage: 85.3%
    """
    pass
```

### Git Workflow

#### Branch Naming
- Features: `feature/issue-<number>-<brief-description>`
- Bugfixes: `fix/issue-<number>-<brief-description>`
- Hotfixes: `hotfix/<brief-description>`
- Documentation: `docs/<brief-description>`

#### Commit Guidelines
- **Atomic Commits**: One logical change per commit
- **Commit Messages**: Follow [Conventional Commits](https://www.conventionalcommits.org/)
  ```
  <type>(<scope>): <subject>
  
  <body>
  
  <footer>
  ```
- **Types**: feat, fix, docs, style, refactor, test, chore
- **Scope**: agent, github, infra, logging, cli, etc.
- **Subject**: Imperative mood, no period, <50 chars
- **Body**: Explain what and why, not how

#### Examples:
```bash
# Good commit messages
git commit -m "feat(agent): add retry logic for GitHub API calls"
git commit -m "fix(logging): correct timestamp format in CloudWatch"
git commit -m "docs: update setup instructions for Windows users"

# With body
git commit -m "refactor(cli): simplify command structure

Consolidated agent subcommands under a single 'agent' command
to improve usability. This change maintains backward compatibility
through aliases.

Closes #123"
```

#### Pre-Push Checklist
- [ ] All tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation is updated
- [ ] Commits are well-organized
- [ ] Branch is up-to-date with main

### Security Considerations

#### Secure Coding Practices
- **Never commit secrets**: Use environment variables for sensitive data
- **Input validation**: Validate all external inputs
- **Dependency security**: Keep dependencies updated
- **SQL injection**: Use parameterized queries
- **Command injection**: Avoid shell=True, use subprocess with lists

#### Security Checklist
- [ ] No hardcoded credentials or API keys
- [ ] All user inputs are validated and sanitized
- [ ] Error messages don't expose sensitive information
- [ ] File operations use safe path joining
- [ ] External command execution is properly escaped
- [ ] Dependencies are from trusted sources

#### Handling Secrets
```python
# BAD - Never do this
GITHUB_TOKEN = "ghp_xxxxxxxxxxxxxxxxxxxx"

# GOOD - Use environment variables
import os
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
if not GITHUB_TOKEN:
    raise ValueError("GITHUB_TOKEN environment variable not set")
```

## Pull Request Process

### Before Creating a PR

1. **Run Full Test Suite**
   ```bash
   # Run all tests and checks
   pytest --cov=entropy_playground
   ruff check .
   black --check .
   mypy .
   pre-commit run --all-files
   ```

2. **Update Documentation**
   - Docstrings for new/modified functions
   - README.md if adding features
   - ARCHITECTURE.md for design changes
   - API documentation if applicable

3. **Self-Review**
   - Review your own changes
   - Check for debugging code
   - Verify no sensitive data
   - Ensure consistent style

### Creating the PR

1. **Title Format**: `<type>: <description> (#<issue-number>)`
   - Example: `feat: add retry logic for GitHub API calls (#123)`

2. **PR Description Template**:
   ```markdown
   ## Description
   Brief description of changes
   
   ## Related Issue
   Fixes #<issue-number>
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   - [ ] Unit tests pass
   - [ ] Integration tests pass
   - [ ] Manual testing completed
   
   ## Checklist
   - [ ] Code follows project style guidelines
   - [ ] Self-review completed
   - [ ] Documentation updated
   - [ ] Tests added/updated
   - [ ] No new warnings
   ```

### Review Process

1. **Automated Checks**: Wait for CI/CD to complete
2. **Code Review**: Address reviewer feedback promptly
3. **Update Branch**: Keep branch up-to-date with main
4. **Final Approval**: Maintainer approval required
5. **Merge**: Squash and merge preferred

### After Merge

- Delete your feature branch
- Update your local repository
- Close related issues if not auto-closed

## Getting Help

- Join discussions in [GitHub Discussions](https://github.com/datablogin/entropy-playground/discussions)
- Ask questions in issues with `question` label
- Reach out to maintainers

## Recognition

Contributors will be recognized in:
- The project README
- Release notes
- Annual contributor reports

Thank you for contributing to Entropy-Playground!