"""Tests for CLI exception handling."""

from unittest.mock import MagicMock, patch

import pytest

from entropy_playground.cli.exceptions import (
    AgentError,
    ConfigurationError,
    ConnectionError,
    EntropyPlaygroundError,
    handle_errors,
)


class TestExceptions:
    """Test custom exception classes."""
    
    def test_entropy_playground_error(self):
        """Test base exception."""
        error = EntropyPlaygroundError("Test error")
        assert str(error) == "Test error"
        assert error.format_message() == "Test error"
    
    def test_configuration_error(self):
        """Test configuration exception."""
        error = ConfigurationError("Config error")
        assert isinstance(error, EntropyPlaygroundError)
        assert str(error) == "Config error"
    
    def test_connection_error(self):
        """Test connection exception."""
        error = ConnectionError("Connection failed")
        assert isinstance(error, EntropyPlaygroundError)
        assert str(error) == "Connection failed"
    
    def test_agent_error(self):
        """Test agent exception."""
        error = AgentError("Agent failed")
        assert isinstance(error, EntropyPlaygroundError)
        assert str(error) == "Agent failed"


class TestHandleErrors:
    """Test error handling decorator."""
    
    def test_handle_errors_success(self):
        """Test decorator with successful function."""
        @handle_errors
        def successful_func():
            return "success"
        
        result = successful_func()
        assert result == "success"
    
    def test_handle_errors_entropy_playground_error(self):
        """Test decorator with EntropyPlaygroundError."""
        @handle_errors
        def failing_func():
            raise ConfigurationError("Config problem")
        
        with pytest.raises(ConfigurationError) as exc_info:
            failing_func()
        
        assert str(exc_info.value) == "Config problem"
    
    def test_handle_errors_file_not_found(self):
        """Test decorator with FileNotFoundError."""
        @handle_errors
        def file_func():
            e = FileNotFoundError("No such file")
            e.filename = "test.txt"
            raise e
        
        with pytest.raises(ConfigurationError) as exc_info:
            file_func()
        
        assert "File not found: test.txt" in str(exc_info.value)
    
    def test_handle_errors_permission_error(self):
        """Test decorator with PermissionError."""
        @handle_errors
        def permission_func():
            error = PermissionError("Permission denied")
            error.filename = "/protected/file"
            raise error
        
        with pytest.raises(ConfigurationError) as exc_info:
            permission_func()
        
        assert "Permission denied: /protected/file" in str(exc_info.value)
    
    @patch("entropy_playground.logging.logger.get_logger")
    def test_handle_errors_unexpected(self, mock_get_logger):
        """Test decorator with unexpected exception."""
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        @handle_errors
        def unexpected_func():
            raise ValueError("Unexpected error")
        
        with pytest.raises(EntropyPlaygroundError) as exc_info:
            unexpected_func()
        
        assert "An unexpected error occurred: Unexpected error" in str(exc_info.value)
        assert "Run with --verbose for more details" in str(exc_info.value)
        
        # Verify logging
        mock_logger.error.assert_called_once_with("Unexpected error", exc_info=True)