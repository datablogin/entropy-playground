"""Tests for Claude API client."""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from pydantic import ValidationError

from entropy_playground.ai.claude import (
    ClaudeClient,
    ClaudeError,
    ClaudeMessage,
    ClaudeRequest,
    ClaudeResponse,
    MockClaudeClient,
)


class TestClaudeMessage:
    """Test ClaudeMessage model."""
    
    def test_valid_message(self):
        """Test creating valid message."""
        msg = ClaudeMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_invalid_role(self):
        """Test invalid role raises validation error."""
        with pytest.raises(ValidationError):
            ClaudeMessage(role="invalid", content="Hello")


class TestClaudeRequest:
    """Test ClaudeRequest model."""
    
    def test_default_values(self):
        """Test default values are set correctly."""
        messages = [ClaudeMessage(role="user", content="Hello")]
        request = ClaudeRequest(messages=messages)
        
        assert request.model == "claude-3-opus-20240229"
        assert request.max_tokens == 4096
        assert request.temperature == 0.7
        assert request.stream is False
    
    def test_validation_constraints(self):
        """Test validation constraints."""
        messages = [ClaudeMessage(role="user", content="Hello")]
        
        # Test max_tokens constraints
        with pytest.raises(ValidationError):
            ClaudeRequest(messages=messages, max_tokens=0)
        
        with pytest.raises(ValidationError):
            ClaudeRequest(messages=messages, max_tokens=300000)
        
        # Test temperature constraints
        with pytest.raises(ValidationError):
            ClaudeRequest(messages=messages, temperature=-0.1)
        
        with pytest.raises(ValidationError):
            ClaudeRequest(messages=messages, temperature=1.1)


class TestClaudeResponse:
    """Test ClaudeResponse model."""
    
    def test_valid_response(self):
        """Test creating valid response."""
        response_data = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello!"}],
            "model": "claude-3-opus-20240229",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        
        response = ClaudeResponse(**response_data)
        assert response.id == "msg_123"
        assert response.role == "assistant"
        assert response.usage["input_tokens"] == 10


class TestClaudeClient:
    """Test ClaudeClient."""
    
    @pytest.fixture
    def mock_client(self):
        """Create mock HTTP client."""
        with patch("entropy_playground.ai.claude.httpx.AsyncClient") as mock:
            yield mock
    
    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = ClaudeClient(api_key="test-key")
        assert client.api_key == "test-key"
    
    def test_init_without_api_key(self):
        """Test initialization without API key raises error."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="API key must be provided"):
                ClaudeClient()
    
    def test_init_from_env(self):
        """Test initialization from environment variable."""
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "env-key"}):
            client = ClaudeClient()
            assert client.api_key == "env-key"
    
    @pytest.mark.asyncio
    async def test_successful_request(self, mock_client):
        """Test successful API request."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello!"}],
            "model": "claude-3-opus-20240229",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        
        mock_client.return_value.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.aclose = AsyncMock()
        
        client = ClaudeClient(api_key="test-key")
        
        messages = [{"role": "user", "content": "Hello"}]
        response = await client.create_message(messages)
        
        assert response.id == "msg_123"
        assert response.role == "assistant"
        assert client.get_usage()["requests"] == 1
        assert client.get_usage()["total_tokens"] == 15
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_api_error(self, mock_client):
        """Test API error handling."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        
        mock_client.return_value.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.aclose = AsyncMock()
        
        client = ClaudeClient(api_key="test-key")
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(ClaudeError) as exc_info:
            await client.create_message(messages)
        
        assert exc_info.value.status_code == 400
        await client.close()
    
    @pytest.mark.asyncio
    async def test_rate_limiting_retry(self, mock_client):
        """Test rate limiting retry logic."""
        # First request: rate limited
        rate_limited_response = Mock()
        rate_limited_response.status_code = 429
        rate_limited_response.headers = {"retry-after": "0.1"}
        rate_limited_response.text = "Rate limited"
        
        # Second request: success
        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "id": "msg_123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello!"}],
            "model": "claude-3-opus-20240229",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }
        
        mock_client.return_value.post = AsyncMock(
            side_effect=[rate_limited_response, success_response]
        )
        mock_client.return_value.aclose = AsyncMock()
        
        client = ClaudeClient(api_key="test-key")
        
        messages = [{"role": "user", "content": "Hello"}]
        response = await client.create_message(messages)
        
        assert response.id == "msg_123"
        assert mock_client.return_value.post.call_count == 2
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_timeout_error(self, mock_client):
        """Test timeout error handling."""
        mock_client.return_value.post = AsyncMock(
            side_effect=httpx.TimeoutException("Timeout")
        )
        mock_client.return_value.aclose = AsyncMock()
        
        client = ClaudeClient(api_key="test-key")
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(ClaudeError, match="Request timeout"):
            await client.create_message(messages)
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_request_error(self, mock_client):
        """Test request error handling."""
        mock_client.return_value.post = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )
        mock_client.return_value.aclose = AsyncMock()
        
        client = ClaudeClient(api_key="test-key")
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(ClaudeError, match="Request failed"):
            await client.create_message(messages)
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_validation_error(self, mock_client):
        """Test response validation error."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "invalid": "response"
        }
        
        mock_client.return_value.post = AsyncMock(return_value=mock_response)
        mock_client.return_value.aclose = AsyncMock()
        
        client = ClaudeClient(api_key="test-key")
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(ClaudeError, match="Invalid response format"):
            await client.create_message(messages)
        
        await client.close()
    
    def test_usage_tracking(self):
        """Test usage tracking."""
        client = ClaudeClient(api_key="test-key")
        
        # Test initial state
        usage = client.get_usage()
        assert usage["total_tokens"] == 0
        assert usage["requests"] == 0
        
        # Test update usage
        client._update_usage({"input_tokens": 10, "output_tokens": 5})
        usage = client.get_usage()
        assert usage["total_tokens"] == 15
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 5
        assert usage["requests"] == 1
        
        # Test reset
        client.reset_usage()
        usage = client.get_usage()
        assert usage["total_tokens"] == 0
        assert usage["requests"] == 0


class TestMockClaudeClient:
    """Test MockClaudeClient."""
    
    @pytest.mark.asyncio
    async def test_mock_response(self):
        """Test mock response generation."""
        client = MockClaudeClient()
        client.add_mock_response("Hello, world!")
        
        messages = [{"role": "user", "content": "Hello"}]
        response = await client.create_message(messages)
        
        assert response.content[0]["text"] == "Hello, world!"
        assert client.get_usage()["requests"] == 1
    
    @pytest.mark.asyncio
    async def test_mock_error(self):
        """Test mock error handling."""
        client = MockClaudeClient()
        client.add_mock_error(ClaudeError("Mock error"))
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with pytest.raises(ClaudeError, match="Mock error"):
            await client.create_message(messages)
    
    @pytest.mark.asyncio
    async def test_default_response(self):
        """Test default mock response."""
        client = MockClaudeClient()
        
        messages = [{"role": "user", "content": "Hello"}]
        response = await client.create_message(messages)
        
        assert response.content[0]["text"] == "Mock response"
        assert response.usage["input_tokens"] == 10
        assert response.usage["output_tokens"] == 20