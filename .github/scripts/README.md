# GitHub Setup Scripts

This directory contains scripts to help set up the Entropy-Playground repository on GitHub.

## Prerequisites

1. **Python 3.11+** with the following packages:

   ```bash
   pip install PyGithub pyyaml python-dotenv
   ```

2. **GitHub CLI** (`gh`) installed and authenticated:

   ```bash
   # Install GitHub CLI (varies by OS)
   # macOS: brew install gh
   # Linux: See https://github.com/cli/cli#installation

   # Authenticate
   gh auth login
   ```

3. **Environment Setup** - Create a `.env` file in the project root:

   ```bash
   # Copy the example file
   cp .env.example .env

   # Edit .env and add your GitHub token and repo
   # GITHUB_TOKEN=your_github_token
   # GITHUB_REPO=owner/repo
   ```

## Scripts

### setup-labels.sh / setup-labels.py

Sets up all GitHub issue labels defined in `.github/labels.yml`.

**Usage:**

```bash
cd .github/scripts

# Using .env file (recommended):
./setup-labels.sh

# Or specify repo explicitly:
./setup-labels.sh owner/repo
```

This will:

- Create all new labels defined in `labels.yml`
- Update existing labels if their color or description has changed
- Leave other labels untouched

### create-issues.py

Creates GitHub issues from the `ISSUES.md` file.

**Usage:**

```bash
cd .github/scripts

# Using .env file (recommended):
python create-issues.py

# Or specify repo explicitly:
python create-issues.py owner/repo
```

This will:

- Parse all issues from `ISSUES.md`
- Prompt for confirmation before creating
- Create each issue with the specified labels
- Report success/failure for each issue

## Full Setup Process

1. First, create the repository on GitHub

2. Set up environment:

   ```bash
   # Copy and edit .env file
   cp .env.example .env
   # Edit .env with your GITHUB_TOKEN and GITHUB_REPO

   # Authenticate GitHub CLI
   gh auth login
   ```

3. Create labels:

   ```bash
   cd .github/scripts
   ./setup-labels.sh
   ```

4. Create issues:

   ```bash
   python create-issues.py
   ```

## Label Categories

The label system includes:

- **Priority**: critical, high, medium, low
- **Type**: bug, feature, enhancement, documentation, security, etc.
- **Component**: infrastructure, agents, github-integration, cli, logging, aws
- **Status**: ready, in-progress, blocked, needs-review, needs-testing
- **Size**: xs, s, m, l, xl (time estimates)
- **Special**: good first issue, help wanted, dependencies
- **AI**: claude-compatible, needs-human-review, agent-task

## Troubleshooting

- **"GitHub token not provided"**: Check your `.env` file has `GITHUB_TOKEN` set
- **"Repository not specified"**: Check your `.env` file has `GITHUB_REPO` set
- **"gh: command not found"**: Install GitHub CLI
- **Rate limiting**: If creating many issues, you may hit rate limits. Wait and retry.
- **Label creation fails**: Ensure your token has appropriate permissions
- **Module not found**: Run `pip install PyGithub pyyaml python-dotenv`
