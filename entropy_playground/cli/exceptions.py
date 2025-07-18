"""CLI-specific exceptions and error handling."""

from collections.abc import Callable
from typing import Any, TypeVar

import click
from rich.console import Console

console = Console()


class EntropyPlaygroundError(click.ClickException):
    """Base exception for Entropy-Playground CLI errors."""

    def show(self, file: Any | None = None) -> None:
        """Display the error message."""
        console.print(f"[red]Error: {self.format_message()}[/red]")


class ConfigurationError(EntropyPlaygroundError):
    """Raised when configuration is invalid or missing."""

    pass


class ConnectionError(EntropyPlaygroundError):
    """Raised when unable to connect to required services."""

    pass


class AgentError(EntropyPlaygroundError):
    """Raised when agent operations fail."""

    pass


F = TypeVar("F", bound=Callable[..., Any])


def handle_errors(func: F) -> F:
    """Decorator to handle common errors in CLI commands.

    Catches and formats errors for better user experience.
    """
    import functools

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except EntropyPlaygroundError:
            # These are already formatted
            raise
        except FileNotFoundError as e:
            filename = getattr(e, "filename", None) or str(e)
            raise ConfigurationError(f"File not found: {filename}") from e
        except PermissionError as e:
            raise ConfigurationError(f"Permission denied: {e.filename}") from e
        except Exception as e:
            # Log the full exception for debugging
            from entropy_playground.logging.logger import get_logger

            logger = get_logger(__name__)
            logger.error("Unexpected error", exc_info=True)

            # Show user-friendly message
            raise EntropyPlaygroundError(
                f"An unexpected error occurred: {str(e)}\n" "Run with --verbose for more details."
            ) from e

    return wrapper  # type: ignore[return-value]
