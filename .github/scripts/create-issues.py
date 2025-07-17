#!/usr/bin/env python3
"""
Create GitHub issues from ISSUES.md file.
Requires GitHub CLI (gh) to be installed and authenticated.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv


def parse_issues_file(filepath):
    """Parse ISSUES.md file and extract issue information."""
    with open(filepath, "r") as f:
        content = f.read()

    # Split by issue headers
    issue_pattern = r"### Issue \d+: (.+?)\n\*\*Labels:\*\* (.+?)\n\*\*Description:\*\*\n(.+?)(?=\n### Issue|\n## Usage Instructions|\Z)"

    issues = []
    for match in re.finditer(issue_pattern, content, re.DOTALL):
        title = match.group(1).strip()
        labels = match.group(2).strip()
        body = match.group(3).strip()

        # Clean up labels - remove backticks and extra spaces
        labels = labels.replace("`", "").replace(", ", ",")

        issues.append({"title": title, "labels": labels, "body": body})

    return issues


def create_issue_with_gh(repo, title, body, labels):
    """Create a GitHub issue using gh CLI."""
    cmd = [
        "gh",
        "issue",
        "create",
        "--repo",
        repo,
        "--title",
        title,
        "--body",
        body,
        "--label",
        labels,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        issue_url = result.stdout.strip()
        return True, issue_url
    except subprocess.CalledProcessError as e:
        return False, e.stderr


def main():
    """Main function."""
    # Load .env file
    load_dotenv()

    # Check for --yes flag
    auto_confirm = "--yes" in sys.argv
    args = [arg for arg in sys.argv[1:] if arg != "--yes"]

    if len(args) > 1:
        print("Usage: python create-issues.py [owner/repo] [--yes]")
        print("Example: python create-issues.py entropy-playground/entropy-playground")
        print("Or just: python create-issues.py --yes (uses GITHUB_REPO from .env)")
        sys.exit(1)

    # Get repo from argument or .env
    if len(args) == 1:
        repo = args[0]
    else:
        repo = os.environ.get("GITHUB_REPO")
        if not repo:
            print("Error: Repository not specified. Set GITHUB_REPO in .env or pass as argument.")
            sys.exit(1)

    # Find ISSUES.md file
    issues_file = Path(__file__).parent.parent.parent / "ISSUES.md"
    if not issues_file.exists():
        print(f"Error: {issues_file} not found")
        sys.exit(1)

    # Parse issues
    issues = parse_issues_file(issues_file)
    print(f"Found {len(issues)} issues to create")

    # Confirm before creating
    if not auto_confirm:
        response = input("Do you want to create these issues? (y/N): ")
        if response.lower() != "y":
            print("Aborted")
            sys.exit(0)
    else:
        print("Auto-confirming issue creation (--yes flag used)")

    # Create issues
    created = 0
    failed = 0

    for i, issue in enumerate(issues, 1):
        print(f"\nCreating issue {i}/{len(issues)}: {issue['title']}")
        success, result = create_issue_with_gh(repo, issue["title"], issue["body"], issue["labels"])

        if success:
            print(f"✓ Created: {result}")
            created += 1
        else:
            print(f"✗ Failed: {result}")
            failed += 1

    print(f"\nSummary: Created {created} issues, {failed} failed")


if __name__ == "__main__":
    main()
