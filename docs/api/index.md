# API Reference

This section contains detailed API documentation for all Entropy-Playground modules.

## Core Modules

### [entropy_playground.agents](agents.md)
Agent implementations and base classes.

### [entropy_playground.cli](cli.md)
Command-line interface and commands.

### [entropy_playground.github](github.md)
GitHub API integration and utilities.

### [entropy_playground.infrastructure](infrastructure.md)
Infrastructure management and deployment.

### [entropy_playground.logging](logging.md)
Logging, audit, and metrics functionality.

### [entropy_playground.runtime](runtime.md)
Core runtime, scheduling, and lifecycle management.

## Quick Reference

### Creating an Agent

```python
from entropy_playground.agents import BaseAgent

class MyAgent(BaseAgent):
    def run(self):
        # Agent logic here
        pass
```

### Using the GitHub Client

```python
from entropy_playground.github import GitHubClient

client = GitHubClient(token="your_token")
issues = client.get_issues(repo="owner/repo")
```

### Logging

```python
from entropy_playground.logging import get_logger

logger = get_logger(__name__)
logger.info("Agent started", agent_id="123", task="issue-1")
```