"""
Tests for the retry utilities with exponential backoff.

This module tests the retry decorators and utilities to ensure they handle
transient failures gracefully with proper backoff strategies.
"""

import pytest
import asyncio
import time
import logging
from unittest.mock import Mock, patch
from src.utils.retry import retry, retry_with_context, is_retryable_error
from src.utils.error_handler import ErrorContext, NetworkError


class TestRetryDecorator:
    """Test the basic retry decorator functionality."""
    
    def test_retry_success_on_first_attempt(self):
        """Test that function succeeds on first attempt without retries."""
        @retry(max_attempts=3, base_delay=0.1)
        def test_func():
            return "success"
        
        result = test_func()
        assert result == "success"
    
    def test_retry_success_after_failures(self):
        """Test that function succeeds after some failures."""
        attempt_count = 0
        
        @retry(max_attempts=3, base_delay=0.1)
        def test_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = test_func()
        assert result == "success"
        assert attempt_count == 3
    
    def test_retry_max_attempts_exceeded(self):
        """Test that retry stops after max attempts."""
        attempt_count = 0
        
        @retry(max_attempts=3, base_delay=0.1)
        def test_func():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Persistent failure")
        
        with pytest.raises(ValueError) as exc_info:
            test_func()
        
        assert str(exc_info.value) == "Persistent failure"
        assert attempt_count == 3
    
    def test_retry_with_custom_exceptions(self):
        """Test retry with specific exception types."""
        attempt_count = 0
        
        @retry(max_attempts=3, base_delay=0.1, exceptions=(ValueError, TypeError))
        def test_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Value error")
            return "success"
        
        result = test_func()
        assert result == "success"
        assert attempt_count == 3
    
    def test_retry_ignores_unexpected_exceptions(self):
        """Test that retry doesn't catch unexpected exception types."""
        @retry(max_attempts=3, base_delay=0.1, exceptions=(ValueError,))
        def test_func():
            raise TypeError("Type error")
        
        with pytest.raises(TypeError) as exc_info:
            test_func()
        
        assert str(exc_info.value) == "Type error"
    
    def test_retry_delay_calculation(self):
        """Test that retry delays follow exponential backoff pattern."""
        delays = []
        
        @retry(max_attempts=4, base_delay=0.1, exponential_base=2.0, jitter=False)
        def test_func():
            delays.append(time.time())
            raise ValueError("Failure")
        
        start_time = time.time()
        
        with pytest.raises(ValueError):
            test_func()
        
        # Should have 4 attempts
        assert len(delays) == 4
        
        # Check delay progression (approximately)
        delay1 = delays[1] - delays[0]
        delay2 = delays[2] - delays[1]
        delay3 = delays[3] - delays[2]
        
        # Base delay is 0.1, so delays should be approximately:
        # 0.1, 0.2, 0.4 seconds
        assert abs(delay1 - 0.1) < 0.05
        assert abs(delay2 - 0.2) < 0.05
        assert abs(delay3 - 0.4) < 0.05
    
    def test_retry_with_max_delay(self):
        """Test that retry respects maximum delay limit."""
        delays = []
        
        @retry(max_attempts=5, base_delay=1.0, max_delay=2.0, exponential_base=2.0, jitter=False)
        def test_func():
            delays.append(time.time())
            raise ValueError("Failure")
        
        start_time = time.time()
        
        with pytest.raises(ValueError):
            test_func()
        
        # Should have 5 attempts
        assert len(delays) == 5
        
        # Check that delays don't exceed max_delay
        delay1 = delays[1] - delays[0]  # Should be 1.0
        delay2 = delays[2] - delays[1]  # Should be 2.0 (capped)
        delay3 = delays[3] - delays[2]  # Should be 2.0 (capped)
        delay4 = delays[4] - delays[3]  # Should be 2.0 (capped)
        
        assert abs(delay1 - 1.0) < 0.05
        assert abs(delay2 - 2.0) < 0.05
        assert abs(delay3 - 2.0) < 0.05
        assert abs(delay4 - 2.0) < 0.05
    
    def test_retry_with_jitter(self):
        """Test that retry adds jitter to delays."""
        delays = []
        
        @retry(max_attempts=3, base_delay=0.1, jitter=True)
        def test_func():
            delays.append(time.time())
            raise ValueError("Failure")
        
        with pytest.raises(ValueError):
            test_func()
        
        # Should have 3 attempts
        assert len(delays) == 3
        
        # Check that delays have some variation due to jitter
        delay1 = delays[1] - delays[0]
        delay2 = delays[2] - delays[1]
        
        # Delays should be different due to jitter
        assert delay1 != delay2


class TestRetryWithContext:
    """Test the retry decorator with error context."""
    
    def test_retry_with_context_success(self):
        """Test retry with context when function succeeds."""
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        @retry_with_context(context, max_attempts=3, base_delay=0.1)
        def test_func():
            return "success"
        
        result = test_func()
        assert result == "success"
    
    def test_retry_with_context_failure(self):
        """Test retry with context when function fails."""
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        attempt_count = 0
        
        @retry_with_context(context, max_attempts=3, base_delay=0.1)
        def test_func():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Failure")
        
        with pytest.raises(ValueError):
            test_func()
        
        assert attempt_count == 3


class TestAsyncRetry:
    """Test retry functionality with async functions."""
    
    @pytest.mark.asyncio
    async def test_async_retry_success_on_first_attempt(self):
        """Test that async function succeeds on first attempt without retries."""
        @retry(max_attempts=3, base_delay=0.1)
        async def test_func():
            return "success"
        
        result = await test_func()
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_async_retry_success_after_failures(self):
        """Test that async function succeeds after some failures."""
        attempt_count = 0
        
        @retry(max_attempts=3, base_delay=0.1)
        async def test_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = await test_func()
        assert result == "success"
        assert attempt_count == 3
    
    @pytest.mark.asyncio
    async def test_async_retry_max_attempts_exceeded(self):
        """Test that async retry stops after max attempts."""
        attempt_count = 0
        
        @retry(max_attempts=3, base_delay=0.1)
        async def test_func():
            nonlocal attempt_count
            attempt_count += 1
            raise ValueError("Persistent failure")
        
        with pytest.raises(ValueError) as exc_info:
            await test_func()
        
        assert str(exc_info.value) == "Persistent failure"
        assert attempt_count == 3
    
    @pytest.mark.asyncio
    async def test_async_retry_delay_calculation(self):
        """Test that async retry delays follow exponential backoff pattern."""
        delays = []
        
        @retry(max_attempts=3, base_delay=0.1, exponential_base=2.0, jitter=False)
        async def test_func():
            delays.append(time.time())
            raise ValueError("Failure")
        
        start_time = time.time()
        
        with pytest.raises(ValueError):
            await test_func()
        
        # Should have 3 attempts
        assert len(delays) == 3
        
        # Check delay progression (approximately)
        delay1 = delays[1] - delays[0]
        delay2 = delays[2] - delays[1]
        
        # Base delay is 0.1, so delays should be approximately:
        # 0.1, 0.2 seconds
        assert abs(delay1 - 0.1) < 0.05
        assert abs(delay2 - 0.2) < 0.05


class TestRetryableErrorDetection:
    """Test the retryable error detection utility."""
    
    def test_retryable_error_types(self):
        """Test that known retryable error types are detected correctly."""
        retryable_errors = [
            ConnectionError("Connection refused"),
            TimeoutError("Operation timed out"),
            OSError("Network unreachable"),
        ]
        
        for error in retryable_errors:
            assert is_retryable_error(error)
    
    def test_non_retryable_error_types(self):
        """Test that non-retryable error types are detected correctly."""
        non_retryable_errors = [
            ValueError("Invalid value"),
            TypeError("Invalid type"),
            KeyError("Missing key"),
        ]
        
        for error in non_retryable_errors:
            assert not is_retryable_error(error)
    
    def test_retryable_error_messages(self):
        """Test that error messages with retryable keywords are detected."""
        retryable_messages = [
            "Connection timeout",
            "Rate limit exceeded",
            "Service temporarily unavailable",
            "Too many requests",
            "Server error occurred",
            "Gateway timeout",
        ]
        
        for message in retryable_messages:
            error = Exception(message)
            assert is_retryable_error(error)
    
    def test_non_retryable_error_messages(self):
        """Test that error messages without retryable keywords are not detected."""
        non_retryable_messages = [
            "Invalid input data",
            "File not found",
            "Permission denied",
            "Syntax error",
        ]
        
        for message in non_retryable_messages:
            error = Exception(message)
            assert not is_retryable_error(error)


class TestRetryLogging:
    """Test that retry decorators log retry attempts properly."""
    
    def test_retry_logging_with_logger(self, caplog):
        """Test that retry decorator logs retry attempts when logger is provided."""
        caplog.set_level(logging.WARNING)
        
        logger = logging.getLogger("test_retry_logger")
        
        attempt_count = 0
        
        @retry(max_attempts=3, base_delay=0.1, logger=logger)
        def test_func():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = test_func()
        assert result == "success"
        
        # Should have 2 warning logs for retry attempts
        warning_logs = [record for record in caplog.records if record.levelno == logging.WARNING]
        assert len(warning_logs) == 2
        
        # Check log messages
        assert "attempt 1/3" in warning_logs[0].message
        assert "attempt 2/3" in warning_logs[1].message
    
    def test_retry_logging_final_failure(self, caplog):
        """Test that retry decorator logs final failure when max attempts exceeded."""
        caplog.set_level(logging.ERROR)
        
        logger = logging.getLogger("test_retry_logger")
        
        @retry(max_attempts=3, base_delay=0.1, logger=logger)
        def test_func():
            raise ValueError("Persistent failure")
        
        with pytest.raises(ValueError):
            test_func()
        
        # Should have 1 error log for final failure
        error_logs = [record for record in caplog.records if record.levelno == logging.ERROR]
        assert len(error_logs) == 1
        
        # Check log message
        assert "failed after 3 attempts" in error_logs[0].message


class TestRetryIntegration:
    """Test retry functionality in realistic scenarios."""
    
    def test_network_request_retry_scenario(self):
        """Test retry in a network request scenario."""
        attempt_count = 0
        
        @retry(max_attempts=3, base_delay=0.1, exceptions=(NetworkError,))
        def mock_network_request():
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count == 1:
                raise NetworkError("Connection timeout")
            elif attempt_count == 2:
                raise NetworkError("Rate limit exceeded")
            else:
                return {"status": "success", "data": "card_info"}
        
        result = mock_network_request()
        
        assert result["status"] == "success"
        assert result["data"] == "card_info"
        assert attempt_count == 3
    
    def test_file_operation_retry_scenario(self):
        """Test retry in a file operation scenario."""
        attempt_count = 0
        
        @retry(max_attempts=3, base_delay=0.1, exceptions=(OSError,))
        def mock_file_operation():
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:
                raise OSError("File temporarily locked")
            else:
                return "file_content"
        
        result = mock_file_operation()
        
        assert result == "file_content"
        assert attempt_count == 3
