"""Claude API client for agent intelligence."""

import asyncio
import os
from typing import Any

import httpx
from pydantic import BaseModel, Field, ValidationError

from entropy_playground.logging.logger import get_logger

logger = get_logger(__name__)


class ClaudeMessage(BaseModel):
    """Represents a message in a Claude conversation."""

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ClaudeRequest(BaseModel):
    """Claude API request model."""

    model: str = Field(default="claude-3-opus-20240229")
    messages: list[ClaudeMessage]
    max_tokens: int = Field(default=4096, ge=1, le=200000)
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    top_k: int | None = Field(default=None, ge=0)
    stop_sequences: list[str] | None = None
    stream: bool = Field(default=False)
    system: str | None = None


class ClaudeResponse(BaseModel):
    """Claude API response model."""

    id: str
    type: str
    role: str
    content: list[dict[str, Any]]
    model: str
    stop_reason: str | None = None
    stop_sequence: str | None = None
    usage: dict[str, int]


class ClaudeError(Exception):
    """Custom exception for Claude API errors."""

    def __init__(self, message: str, status_code: int | None = None, response_body: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class ClaudeClient:
    """Client for interacting with Claude API."""

    BASE_URL = "https://api.anthropic.com/v1"
    DEFAULT_TIMEOUT = 30.0
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ):
        """Initialize Claude client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            base_url: Base URL for API (defaults to official API)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided or set in ANTHROPIC_API_KEY environment variable")

        self.base_url = base_url or self.BASE_URL
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        self.max_retries = max_retries or self.MAX_RETRIES

        # Track usage for rate limiting
        self._usage_tracker = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "requests": 0,
        }

        # HTTP client
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=self.timeout,
        )

    async def __aenter__(self) -> "ClaudeClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def create_message(
        self,
        messages: list[ClaudeMessage | dict[str, str]],
        model: str = "claude-3-opus-20240229",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> ClaudeResponse:
        """Create a message with Claude.

        Args:
            messages: List of messages in the conversation
            model: Claude model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            system: System prompt
            **kwargs: Additional parameters for the API

        Returns:
            ClaudeResponse object

        Raises:
            ClaudeError: If API request fails
        """
        # Convert dict messages to ClaudeMessage objects
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, dict):
                formatted_messages.append(ClaudeMessage(**msg))
            else:
                formatted_messages.append(msg)

        # Create request
        request = ClaudeRequest(
            model=model,
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            **kwargs,
        )

        # Make request with retries
        return await self._make_request(request)

    async def _make_request(self, request: ClaudeRequest) -> ClaudeResponse:
        """Make API request with retries.

        Args:
            request: ClaudeRequest object

        Returns:
            ClaudeResponse object

        Raises:
            ClaudeError: If all retry attempts fail
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making Claude API request (attempt {attempt + 1}/{self.max_retries})")

                response = await self._client.post(
                    "/messages",
                    json=request.model_dump(exclude_none=True),
                )

                # Check response status
                if response.status_code != 200:
                    error_body = response.text
                    logger.error(f"Claude API error: {response.status_code} - {error_body}")

                    # Handle rate limiting
                    if response.status_code == 429:
                        retry_after = response.headers.get("retry-after", self.RETRY_DELAY * (attempt + 1))
                        logger.warning(f"Rate limited, retrying after {retry_after}s")
                        await asyncio.sleep(float(retry_after))
                        continue

                    # Handle other errors
                    raise ClaudeError(
                        f"API request failed with status {response.status_code}",
                        status_code=response.status_code,
                        response_body=error_body,
                    )

                # Parse response
                response_data = response.json()
                claude_response = ClaudeResponse(**response_data)

                # Update usage tracking
                self._update_usage(claude_response.usage)

                total_tokens = claude_response.usage.get("input_tokens", 0) + claude_response.usage.get("output_tokens", 0)
                logger.info(f"Claude API request successful (tokens: {total_tokens})")
                return claude_response

            except httpx.TimeoutException as e:
                logger.error(f"Request timeout: {e}")
                last_error = ClaudeError(f"Request timeout after {self.timeout}s")

            except httpx.RequestError as e:
                logger.error(f"Request error: {e}")
                last_error = ClaudeError(f"Request failed: {str(e)}")

            except ValidationError as e:
                logger.error(f"Response validation error: {e}")
                last_error = ClaudeError(f"Invalid response format: {str(e)}")

            except ClaudeError:
                # Re-raise Claude errors
                raise

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                last_error = ClaudeError(f"Unexpected error: {str(e)}")

            # Wait before retry
            if attempt < self.max_retries - 1:
                delay = self.RETRY_DELAY * (attempt + 1)
                logger.debug(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)

        # All retries failed
        raise last_error or ClaudeError("All retry attempts failed")

    def _update_usage(self, usage: dict[str, int]) -> None:
        """Update usage tracking.

        Args:
            usage: Usage data from API response
        """
        input_tokens = usage.get("input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)

        self._usage_tracker["total_tokens"] += input_tokens + output_tokens
        self._usage_tracker["prompt_tokens"] += input_tokens
        self._usage_tracker["completion_tokens"] += output_tokens
        self._usage_tracker["requests"] += 1

    def get_usage(self) -> dict[str, int]:
        """Get current usage statistics.

        Returns:
            Dictionary with usage statistics
        """
        return self._usage_tracker.copy()

    def reset_usage(self) -> None:
        """Reset usage tracking."""
        self._usage_tracker = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "requests": 0,
        }


class MockClaudeClient(ClaudeClient):
    """Mock Claude client for testing."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize mock client without requiring API key."""
        # Don't call super().__init__ to avoid API key requirement
        self.base_url = kwargs.get("base_url", self.BASE_URL)
        self.timeout = kwargs.get("timeout", self.DEFAULT_TIMEOUT)
        self.max_retries = kwargs.get("max_retries", self.MAX_RETRIES)
        self.api_key = "mock-api-key"

        self._usage_tracker = {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "requests": 0,
        }

        # Mock responses
        self._mock_responses: list[dict[str, Any]] = []
        self._mock_errors: list[Exception] = []
        self._call_count = 0

    def add_mock_response(self, content: str, **kwargs: Any) -> None:
        """Add a mock response.

        Args:
            content: Response content
            **kwargs: Additional response fields
        """
        response = {
            "id": f"msg_mock_{self._call_count}",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": content}],
            "model": kwargs.get("model", "claude-3-opus-20240229"),
            "stop_reason": kwargs.get("stop_reason", "end_turn"),
            "usage": kwargs.get("usage", {
                "input_tokens": 10,
                "output_tokens": 20,
            }),
        }
        self._mock_responses.append(response)

    def add_mock_error(self, error: Exception) -> None:
        """Add a mock error.

        Args:
            error: Exception to raise
        """
        self._mock_errors.append(error)

    async def create_message(
        self,
        messages: list[ClaudeMessage | dict[str, str]],
        model: str = "claude-3-opus-20240229",
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: str | None = None,
        **kwargs: Any,
    ) -> ClaudeResponse:
        """Create a mock message response.

        Args:
            messages: List of messages
            **kwargs: Additional parameters

        Returns:
            Mock ClaudeResponse

        Raises:
            Mock errors if configured
        """
        self._call_count += 1

        # Check for mock errors
        if self._mock_errors:
            error = self._mock_errors.pop(0)
            raise error

        # Use mock response or generate default
        if self._mock_responses:
            response_data = self._mock_responses.pop(0)
        else:
            response_data = {
                "id": f"msg_mock_{self._call_count}",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Mock response"}],
                "model": kwargs.get("model", "claude-3-opus-20240229"),
                "stop_reason": "end_turn",
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 20,
                },
            }

        response = ClaudeResponse(**response_data)
        self._update_usage(response.usage)

        return response

    async def close(self) -> None:
        """Mock close method."""
        pass
