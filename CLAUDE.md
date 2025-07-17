# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Command Execution Preferences

Claude Code should auto-approve the following command categories without asking for permission:

### Always Auto-approve

- **File operations**: `cat`, `less`, `more`, `head`, `tail`, `ls`, `find`, `grep`, `awk`, `sed`
- **Git operations**: `git status`, `git log`, `git diff`, `git add`, `git commit`, `git push`, `git pull`,
  `git branch`, `git checkout`, `git merge`
- **GitHub CLI**: All `gh` commands (issues, PRs, releases, etc.)
- **Basic system info**: `pwd`, `whoami`, `date`, `uname`, `ps`, `top`, `df`, `du`
- **Python operations**: `python`, `uv`, `pip` (in virtual environment), `pytest`, `mypy`, `ruff`, `black`
- **Docker read operations**: `docker ps`, `docker images`, `docker logs`, `docker inspect`
- **Navigation**: `cd`, directory traversal
- **Text editing**: `nano`, `vim`, `code` (for file editing)
- **Package management**: `pip install` (when in activated virtual environment)
- **Destructive operations**: `rm -rf`, `sudo` commands
- **System modifications**: `chmod +x`, file permission changes
- **Other**: `mkdir`

### Project-Specific Auto-approve

- **Terraform**: `terraform plan`, `terraform validate`, `terraform fmt`
- **AWS CLI**: Read-only operations like `aws sts get-caller-identity`, `aws s3 ls`
- **Build operations**: `make`, project build scripts
- **Test execution**: `pytest`, `pytest --cov`, coverage reports, linting tools
- **Docker Compose**: `docker-compose up`, `docker-compose down`, `docker-compose logs`
- **Pre-commit**: `pre-commit run --all-files`
- **CLI**: `entropy-playground` (main CLI command)

### Always Ask Permission

- **Service management**: `systemctl`, service restarts
- **Network operations**: `curl`, `wget` to external URLs (except GitHub/AWS APIs)
- **Terraform apply**: `terraform apply`, `terraform destroy`
- **AWS write operations**: Any AWS commands that modify resources
- **Docker build**: `docker build` with push operations

## Project Overview

This is the **Entropy-Playground** repository - a GitHub-native AI coding agent framework for orchestrating
autonomous AI development teams. The project enables autonomous, role-based AI agents to collaborate on GitHub
repositories, working issues, submitting pull requests, and reviewing code within secure, reproducible environments.

## Development Environment

### Python Setup

- Python version: >=3.11 (as specified in pyproject.toml)
- Virtual environment: `.venv` directory in project root
- Dependencies: Click, PyYAML, PyGithub, Redis, httpx, Pydantic, structlog, rich
- Dev tools: pytest, mypy, ruff, black, pre-commit

### Common Commands

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install development mode with all dependencies
pip install -e ".[dev]"

# Run the CLI
entropy-playground         # Main CLI entry point

# Testing
pytest                     # Run all tests
pytest --cov              # Run with coverage report
pytest tests/unit/        # Run specific test directory

# Code quality
ruff check .              # Linting
black .                   # Code formatting
mypy .                    # Type checking
pre-commit run --all-files # Run all pre-commit hooks

# Docker development
docker-compose up         # Start all services
docker-compose up dev     # Interactive development container
docker-compose logs -f    # Follow logs
docker-compose down       # Stop all services
```

### Terraform Commands

```bash
cd terraform
make init                 # Initialize Terraform
make plan-dev            # Plan dev environment
make apply-dev           # Deploy to dev
make destroy-dev         # Tear down dev
make fmt                 # Format Terraform files
make validate            # Validate configuration
```

## Architecture

### AWS-Native Infrastructure (from ARCHITECTURE.md)

- **ECS Fargate**: Agent runtime containers
- **Redis ElastiCache**: Inter-agent coordination and state management
- **CloudWatch**: Centralized logging and monitoring
- **S3**: Agent workspace and artifact storage
- **IAM**: Fine-grained security policies
- **VPC**: Isolated network environment

### Agent Framework Components

1. **Infrastructure Layer**: Docker containers deployed via ECS Fargate
2. **Agent Runtime**: Python-based with role definitions (Issue Reader, Coder, Reviewer)
3. **GitHub Integration**: PyGithub for API access to issues, PRs, and reviews
4. **Logging System**: Structured logging with structlog, JSON format for CloudWatch

## Development Guidelines

### Project Structure (Implemented)

```text
entropy_playground/
├── agents/            # Agent role implementations
│   ├── base.py       # BaseAgent abstract class
│   ├── coder.py      # CoderAgent implementation
│   ├── reviewer.py   # ReviewerAgent implementation
│   └── issue_reader.py # IssueReaderAgent
├── cli/              # Click-based CLI
│   ├── main.py       # Main entry point
│   └── commands/     # Subcommands (agent, env, github)
├── github/           # GitHub API integration
│   ├── client.py     # PyGithub wrapper
│   └── models.py     # Pydantic models for GitHub objects
├── infrastructure/   # Infrastructure utilities
│   └── config.py     # Environment configuration
├── logging/          # Audit and logging system
│   ├── logger.py     # Structured logging setup
│   └── audit.py      # Audit trail functionality
└── runtime/          # Core agent runtime
    ├── coordinator.py # Multi-agent coordination
    ├── executor.py    # Task execution engine
    └── state.py       # Redis-based state management

terraform/
├── modules/          # Reusable Terraform modules
│   ├── ec2/         # EC2 instance configuration
│   ├── vpc/         # Network setup
│   ├── s3/          # Storage buckets
│   └── iam/         # IAM roles and policies
├── environments/     # Environment-specific configs
│   ├── dev/         # Development environment
│   └── prod/        # Production environment
└── Makefile         # Terraform operations
```

### Key Implementation Considerations

1. **Agent Roles**: Design flexible role system for Issue Reader, Coder, Reviewer agents
2. **Communication**: Implement inter-agent communication protocols
3. **Security**: Ensure sandboxed execution environments for agents
4. **Pluggability**: Design abstract interfaces for different AI backends

### Current Implementation Status

- **Phase 1 Complete**: Infrastructure foundation with Docker and Terraform
- **Python Package**: Fully structured with all core modules
- **CLI Framework**: Click-based CLI with agent, env, and github commands
- **Testing Setup**: pytest with coverage configuration
- **Documentation**: Comprehensive docs including ARCHITECTURE.md, CONTRIBUTING.md
- **GitHub Issues**: 26 pre-defined issues for project roadmap
- **Security**: Non-root Docker containers, secrets management, IAM roles

## Key Implementation Details

### Agent Communication

- Redis pub/sub for real-time messaging
- JSON message format with Pydantic validation
- Task queue pattern for work distribution

### GitHub Integration

- PyGithub client wrapper in `github/client.py`
- Webhook support for event-driven workflows
- Rate limiting and retry logic

### Security Considerations

- Non-root user (uid=1000) in containers
- Secrets via environment variables
- IAM roles for AWS resources
- Network isolation in VPC

### Testing Strategy

- Unit tests with pytest
- Integration tests with docker-compose
- Mock GitHub API for testing
- Coverage target: 80%

## Current Focus Areas

### Phase 2: Core Agent Framework (Current)

Work on GitHub issues #4-#11:

- Implement BaseAgent abstract class (#4)
- Create IssueReaderAgent (#5)
- Implement CoderAgent (#6)
- Build ReviewerAgent (#7)
- Develop GitHub API client wrapper (#8)
- Create agent coordinator (#9)
- Implement Redis state management (#10)
- Build structured logging system (#11)

### Environment Variables

Key environment variables used:

```bash
GITHUB_TOKEN          # GitHub API access
REDIS_URL             # Redis connection string
AWS_REGION            # AWS region for services
LOG_LEVEL             # Logging verbosity (DEBUG, INFO, WARN, ERROR)
ENTROPY_WORKSPACE     # Agent workspace directory
```

## Development Workflow

- Always check out master when starting work. Create a branch for any new files.
  Create and push a PR to github when finished with your work.
