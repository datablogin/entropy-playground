# Getting Started with Entropy-Playground

This guide will help you set up and run your first AI agent with Entropy-Playground.

## Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Git
- GitHub account with personal access token
- (Optional) AWS account for cloud deployment

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/datablogin/entropy-playground.git
cd entropy-playground
```

### 2. Set Up Python Environment

We recommend using `uv` for Python environment management:

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv --python 3.11

# Activate environment
source .venv/bin/activate  # On Linux/Mac
# or
.venv\Scripts\activate  # On Windows

# Install dependencies
uv pip install -e ".[dev]"
```

### 3. Configure Environment

Copy the example environment file and add your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```bash
# GitHub Configuration
GITHUB_TOKEN=your_github_token
GITHUB_REPO=owner/repo

# AI Backend Configuration
CLAUDE_API_KEY=your_claude_api_key  # If using Claude

# Redis Configuration
REDIS_URL=redis://localhost:6379
```

### 4. Start Local Infrastructure

```bash
docker-compose up -d
```

This starts:
- Redis for state management
- Local development environment

## Your First Agent

### 1. Initialize the Project

```bash
entropy-playground init
```

### 2. Launch an Agent

```bash
entropy-playground start --agent issue-reader
```

### 3. Monitor Agent Activity

```bash
entropy-playground status
```

## Next Steps

- [Configure Multiple Agents](multi-agent-setup.md)
- [Deploy to AWS](aws-deployment.md)
- [Write Custom Agent Roles](custom-agents.md)