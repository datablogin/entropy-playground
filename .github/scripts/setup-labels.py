#!/usr/bin/env python3
"""
Setup GitHub labels from labels.yml configuration.
Requires PyGithub: pip install PyGithub pyyaml python-dotenv
"""

import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv
from github import Github


def load_labels_config() -> list[dict[str, str]]:
    """Load labels from the labels.yml file."""
    config_path = Path(__file__).parent.parent / "labels.yml"
    with open(config_path) as f:
        data = yaml.safe_load(f)
        result: list[dict[str, str]] = data if data is not None else []
        return result


def setup_labels(repo_name: str | None = None, token: str | None = None) -> None:
    """Setup labels on the GitHub repository."""
    # Load .env file
    load_dotenv()

    # Use token from .env or environment if not provided
    if not token:
        token = os.environ.get("GITHUB_TOKEN")

    # Use repo from .env if not provided
    if not repo_name:
        repo_name = os.environ.get("GITHUB_REPO")

    if not token:
        print("Error: GitHub token not provided. Set GITHUB_TOKEN in .env file or environment.")
        sys.exit(1)

    if not repo_name:
        print(
            "Error: Repository name not provided. Set GITHUB_REPO in .env file or pass as argument."
        )
        sys.exit(1)

    # Initialize GitHub client
    g = Github(token)
    repo = g.get_repo(repo_name)

    # Get existing labels
    existing_labels = {label.name: label for label in repo.get_labels()}

    # Load label configuration
    labels_config = load_labels_config()

    # Process each label
    created = 0
    updated = 0

    for label_data in labels_config:
        name = label_data["name"]
        color = label_data["color"]
        description = label_data.get("description", "")

        if name in existing_labels:
            # Update existing label
            label = existing_labels[name]
            if label.color != color or label.description != description:
                label.edit(name=name, color=color, description=description)
                print(f"Updated label: {name}")
                updated += 1
            else:
                print(f"Label already up-to-date: {name}")
        else:
            # Create new label
            repo.create_label(name=name, color=color, description=description)
            print(f"Created label: {name}")
            created += 1

    print(f"\nSummary: Created {created} labels, updated {updated} labels")


def main() -> None:
    """Main function."""
    if len(sys.argv) > 2:
        print("Usage: python setup-labels.py [owner/repo]")
        print("Example: python setup-labels.py entropy-playground/entropy-playground")
        print("Or just: python setup-labels.py (uses GITHUB_REPO from .env)")
        sys.exit(1)

    repo_name = sys.argv[1] if len(sys.argv) == 2 else None
    setup_labels(repo_name)


if __name__ == "__main__":
    main()
