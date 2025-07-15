#!/bin/bash
# Setup GitHub labels for the Entropy-Playground project

set -e

# Load .env file if it exists
if [ -f "../../.env" ]; then
    export $(cat ../../.env | grep -v '^#' | xargs)
fi

# Check if repository name is provided as argument, otherwise use from .env
if [ $# -eq 0 ]; then
    if [ -z "$GITHUB_REPO" ]; then
        echo "Usage: ./setup-labels.sh [owner/repo]"
        echo "Example: ./setup-labels.sh entropy-playground/entropy-playground"
        echo "Or set GITHUB_REPO in .env file and run without arguments"
        exit 1
    fi
    REPO=$GITHUB_REPO
else
    REPO=$1
fi

# Check if GITHUB_TOKEN is set
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN not found"
    echo "Please set it in .env file or export GITHUB_TOKEN=your_github_token"
    exit 1
fi

# Install dependencies if needed
echo "Checking Python dependencies..."
pip install -q PyGithub pyyaml python-dotenv || {
    echo "Failed to install dependencies. Make sure pip is available."
    exit 1
}

# Run the Python script
echo "Setting up labels for repository: $REPO"
python "$(dirname "$0")/setup-labels.py" "$REPO"