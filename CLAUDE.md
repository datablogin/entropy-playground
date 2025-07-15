# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the **Entropy-Playground** repository - a GitHub-native AI coding agent framework for orchestrating autonomous AI development teams. The project enables autonomous, role-based AI agents to collaborate on GitHub repositories, working issues, submitting pull requests, and reviewing code within secure, reproducible environments.

## Development Environment

### Python Setup
- Python version: >=3.11 (as specified in pyproject.toml)
- Virtual environment: `.venv` directory exists in the project root
- No dependencies are currently listed in pyproject.toml

### Common Commands

```bash
# Activate virtual environment
source .venv/bin/activate  # On Linux/Mac
.venv\Scripts\activate  # On Windows

# Install the project in development mode (once dependencies are added)
pip install -e .

# Future commands (to be implemented):
# python -m entropy_playground.cli  # Run the CLI
# pytest tests/  # Run tests
# ruff check .  # Lint code
# mypy .  # Type check
```

## Architecture Goals (from README)

The Entropy-Playground framework aims to implement:

1. **Infrastructure Layer**: Docker, Kubernetes, and Terraform for reproducible environments
2. **Agent Runtime Framework**: Python-based with role definitions and multi-agent coordination
3. **GitHub Integration**: API access for issues, PRs, and reviews
4. **Auditability**: Immutable logging and action tracking

## Development Guidelines

### Project Structure (Recommended)
Given the architecture described in the README, consider organizing the code as:

```
entropy_playground/
├── infrastructure/     # Terraform, Docker configs
├── agents/            # Agent role implementations
├── github/            # GitHub API integration
├── runtime/           # Core agent runtime
├── logging/           # Audit and logging system
└── cli/              # Command-line interface
```

### Key Implementation Considerations

1. **Agent Roles**: Design flexible role system for Issue Reader, Coder, Reviewer agents
2. **Communication**: Implement inter-agent communication protocols
3. **Security**: Ensure sandboxed execution environments for agents
4. **Pluggability**: Design abstract interfaces for different AI backends

### Current Implementation Status

- No source code implemented yet
- Basic Python project structure initialized
- Comprehensive vision documented in README
- Claude AI integration configured via `.claude/settings.local.json`

## Next Steps

When implementing features:
1. Start with the MVP features listed in the README
2. Follow Python best practices and PEP 8 style guide
3. Create modular, testable components
4. Document API interfaces for agent communication
5. Implement logging early for auditability

## MVP Features (from README)

- Terraform scripts for AWS VM provisioning
- Docker Compose support for local runs
- Basic CLI for launching and managing agent environments
- Single-agent workflow completing a full GitHub issue lifecycle

## Roadmap Phases

1. **Foundation (0-2 months)**: Repository scaffolding, infrastructure scripts, CLI
2. **Core Agent Framework (2-4 months)**: Role management, GitHub API integration, audit framework
3. **Multi-Agent Collaboration (4-6 months)**: Communication protocols, review workflows, GitHub Actions
4. **Pluggable LLM Backends (6-9 months)**: Backend abstraction, support for multiple AI models
5. **Hardening and Community Release (9-12 months)**: Security, auto-scaling, v1.0 release