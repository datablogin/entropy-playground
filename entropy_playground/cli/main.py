"""Main entry point for the Entropy-Playground CLI."""

from pathlib import Path

import click
from rich.console import Console

from entropy_playground import __version__
from entropy_playground.cli.exceptions import (
    ConfigurationError,
    handle_errors,
)
from entropy_playground.infrastructure.config import Config
from entropy_playground.logging.logger import get_logger

console = Console()
logger = get_logger(__name__)


@click.group()
@click.version_option(version=__version__, prog_name="entropy-playground")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Path to configuration file",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, config: Path | None, verbose: bool) -> None:
    """Entropy-Playground: GitHub-Native AI Coding Agent Framework.

    Orchestrate autonomous AI development teams to work on GitHub repositories,
    manage issues, submit pull requests, and review code.
    """
    ctx.ensure_object(dict)

    # Load configuration
    if config:
        ctx.obj["config"] = Config.from_file(config)
    else:
        ctx.obj["config"] = Config()

    # Set logging level
    if verbose:
        logger.debug("Verbose mode enabled")

    ctx.obj["verbose"] = verbose


@cli.command()
@click.option(
    "--workspace",
    "-w",
    type=click.Path(path_type=Path),
    default=Path.cwd() / ".entropy",
    help="Path to workspace directory",
)
@click.option(
    "--github-token",
    envvar="GITHUB_TOKEN",
    help="GitHub API token (can also use GITHUB_TOKEN env var)",
)
@click.option(
    "--redis-url",
    envvar="REDIS_URL",
    default="redis://localhost:6379",
    help="Redis connection URL",
)
@click.pass_context
@handle_errors
def init(
    ctx: click.Context,
    workspace: Path,
    github_token: str | None,
    redis_url: str,
) -> None:
    """Initialize the Entropy-Playground environment.

    Sets up the necessary configuration files, workspace directories,
    and validates connectivity to required services.
    """
    console.print("[bold]Initializing Entropy-Playground environment...[/bold]")

    # Create workspace directory
    try:
        workspace.mkdir(parents=True, exist_ok=True)
        console.print(f"✓ Created workspace directory: {workspace}")
    except PermissionError:
        raise ConfigurationError(
            f"Permission denied creating workspace directory: {workspace}"
        ) from None

    # Validate GitHub token
    if not github_token:
        raise ConfigurationError(
            "GitHub token not provided. Set GITHUB_TOKEN environment variable or use --github-token"
        )

    # Create config
    config = Config(
        version=__version__,
        workspace=workspace,
        redis_url=redis_url,
        github={"token": "${GITHUB_TOKEN}"},  # Use env var reference
    )

    # Save configuration
    config_path = workspace / "config.yaml"
    try:
        config.save(config_path)
        console.print(f"✓ Created configuration file: {config_path}")
    except Exception as e:
        raise ConfigurationError(f"Failed to save configuration: {str(e)}") from e

    # Test GitHub connectivity
    try:
        from github import Github

        g = Github(github_token)
        user = g.get_user()
        console.print(f"✓ GitHub authentication successful (user: {user.login})")
    except Exception as e:
        logger.warning("GitHub authentication failed", error=str(e))
        console.print(
            "[yellow]⚠ Could not verify GitHub token. Ensure it's valid before starting agents.[/yellow]"
        )

    console.print("[green]✓ Environment initialized successfully![/green]")


@cli.command()
@click.option(
    "--agent",
    "-a",
    type=click.Choice(["issue_reader", "coder", "reviewer", "all"]),
    default="all",
    help="Agent type to start",
)
@click.option(
    "--repo",
    "-r",
    required=True,
    help="GitHub repository (format: owner/repo)",
)
@click.option(
    "--issue",
    "-i",
    type=int,
    help="Specific issue number to work on",
)
@click.option(
    "--detach",
    "-d",
    is_flag=True,
    help="Run agents in background",
)
@click.pass_context
@handle_errors
def start(
    ctx: click.Context,
    agent: str,
    repo: str,
    issue: int | None,
    detach: bool,
) -> None:
    """Start agent(s) to work on a GitHub repository.

    Launches one or more agents to autonomously work on issues,
    create pull requests, and review code.
    """
    config = ctx.obj["config"]

    # Validate repository format
    if "/" not in repo:
        raise ConfigurationError(f"Invalid repository format: {repo}. Expected format: owner/repo")

    owner, repo_name = repo.split("/", 1)
    if not owner or not repo_name:
        raise ConfigurationError(f"Invalid repository format: {repo}. Expected format: owner/repo")

    # Check configuration
    if not config.validate_github_token():
        raise ConfigurationError(
            "GitHub token not configured. Run 'entropy-playground init' first."
        )

    console.print(f"[bold]Starting {agent} agent(s) for {owner}/{repo_name}...[/bold]")

    if issue:
        console.print(f"Working on issue #{issue}")

    # TODO: Implement agent startup logic
    # This will be implemented in future issues
    console.print("[yellow]Agent startup not yet implemented[/yellow]")


@cli.command()
@click.option(
    "--format",
    "-f",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
)
@click.pass_context
@handle_errors
def status(ctx: click.Context, format: str) -> None:
    """Check the status of running agents.

    Shows active agents, their current tasks, and recent activity.
    """
    _ = ctx.obj["config"]  # Will be used in future implementation

    console.print("[bold]Agent Status[/bold]")

    # TODO: Implement status checking logic
    # This will be implemented in future issues
    console.print("[yellow]Status checking not yet implemented[/yellow]")


@cli.command()
@click.argument("agent", type=click.Choice(["issue_reader", "coder", "reviewer", "all"]))
@click.pass_context
@handle_errors
def stop(ctx: click.Context, agent: str) -> None:
    """Stop running agent(s).

    Gracefully shuts down specified agents.
    """
    console.print(f"[bold]Stopping {agent} agent(s)...[/bold]")

    # TODO: Implement agent stopping logic
    # This will be implemented in future issues
    console.print("[yellow]Agent stopping not yet implemented[/yellow]")


@cli.command()
@click.option(
    "--tail",
    "-n",
    type=int,
    default=50,
    help="Number of log lines to show",
)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow log output",
)
@click.option(
    "--agent",
    "-a",
    type=click.Choice(["issue_reader", "coder", "reviewer", "all"]),
    default="all",
    help="Filter logs by agent type",
)
@click.pass_context
@handle_errors
def logs(
    ctx: click.Context,
    tail: int,
    follow: bool,
    agent: str,
) -> None:
    """View agent logs.

    Display recent log entries from agent activities.
    """
    console.print(f"[bold]Showing logs for {agent} agent(s)[/bold]")

    # TODO: Implement log viewing logic
    # This will be implemented in future issues
    console.print("[yellow]Log viewing not yet implemented[/yellow]")


if __name__ == "__main__":
    cli()
