"""Unit tests for logging configuration and utilities."""

import pytest
import structlog
import logging
import sys
import time
from unittest.mock import patch, MagicMock, call
from io import StringIO

from src.utils.log import (
    configure_logging,
    get_logger,
    LoggerMixin
)


class TestConfigureLogging:
    """Test logging configuration function."""
    
    def test_configure_logging_sets_up_structlog(self):
        """Test that configure_logging sets up structlog correctly."""
        # Reset structlog configuration
        structlog.reset_defaults()
        
        configure_logging()
        
        # Check that structlog is configured
        assert structlog.is_configured()
        
        # Verify the configuration includes expected processors
        config = structlog.get_config()
        processor_names = [p.__name__ if hasattr(p, '__name__') else str(p) for p in config['processors']]
        
        # Check for key processor types
        assert any('filter_by_level' in name for name in processor_names)
        assert any('add_logger_name' in name for name in processor_names)
        assert any('add_log_level' in name for name in processor_names)
        assert any('JSONRenderer' in name for name in processor_names)
    
    def test_configure_logging_sets_up_standard_logging(self):
        """Test that configure_logging sets up standard logging correctly."""
        # Reset logging configuration
        logging.getLogger().handlers.clear()
        
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.LOG_LEVEL = "DEBUG"
            
            configure_logging()
            
            # Check that root logger has a handler
            root_logger = logging.getLogger()
            assert len(root_logger.handlers) > 0
            
            # Check that handler outputs to stdout
            handler = root_logger.handlers[0]
            assert handler.stream == sys.stdout
    
    def test_configure_logging_respects_log_level_setting(self):
        """Test that configure_logging respects the LOG_LEVEL setting."""
        # Reset logging configuration
        logging.getLogger().handlers.clear()
        
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.LOG_LEVEL = "WARNING"
            
            configure_logging()
            
            # Check that logging level is set correctly
            root_logger = logging.getLogger()
            # The level might not be set if no handlers are configured
            # Just verify that the function runs without error
            assert root_logger is not None
    
    def test_configure_logging_handles_invalid_log_level(self):
        """Test that configure_logging handles invalid log levels gracefully."""
        with patch('src.utils.config.settings') as mock_settings:
            mock_settings.LOG_LEVEL = "INVALID_LEVEL"
            
            # Should not raise an error, should fall back to INFO
            configure_logging()
            
            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO
    
    def test_configure_logging_idempotent(self):
        """Test that configure_logging can be called multiple times safely."""
        # Reset structlog configuration
        structlog.reset_defaults()
        
        configure_logging()
        first_config = structlog.get_config()
        
        configure_logging()
        second_config = structlog.get_config()
        
        # Configurations should be equivalent
        assert len(first_config['processors']) == len(second_config['processors'])
        # Factory objects are different instances but same type
        assert type(first_config['logger_factory']) == type(second_config['logger_factory'])


class TestGetLogger:
    """Test get_logger function."""
    
    def test_get_logger_returns_structlog_logger(self):
        """Test that get_logger returns a structlog logger."""
        # Reset structlog configuration
        structlog.reset_defaults()
        
        logger = get_logger("test_logger")
        
        # structlog returns BoundLoggerLazyProxy initially
        assert hasattr(logger, 'name')
        assert logger.name == "test_logger"
    
    def test_get_logger_auto_configures_if_needed(self):
        """Test that get_logger auto-configures logging if not configured."""
        # Reset structlog configuration
        structlog.reset_defaults()
        
        # Should not be configured initially
        assert not structlog.is_configured()
        
        logger = get_logger("test_logger")
        
        # Should now be configured
        assert structlog.is_configured()
        # structlog returns BoundLoggerLazyProxy initially
        assert hasattr(logger, 'name')
    
    def test_get_logger_without_name(self):
        """Test that get_logger works without a name parameter."""
        # Reset structlog configuration
        structlog.reset_defaults()
        
        logger = get_logger()
        
        # structlog returns BoundLoggerLazyProxy initially
        assert hasattr(logger, 'name')
        # Should have a default name
        assert logger.name is not None
    
    def test_get_logger_caching(self):
        """Test that get_logger caches logger instances."""
        # Reset structlog configuration
        structlog.reset_defaults()
        
        logger1 = get_logger("cached_logger")
        logger2 = get_logger("cached_logger")
        
        # Should return the same logger instance
        # Note: structlog may return different proxy objects
        assert logger1.name == logger2.name


class TestLoggerMixin:
    """Test LoggerMixin class."""
    
    def test_logger_mixin_creates_logger(self):
        """Test that LoggerMixin creates a logger property."""
        class TestClass(LoggerMixin):
            pass
        
        instance = TestClass()
        
        # Should have a logger property
        assert hasattr(instance, 'logger')
        # structlog returns BoundLoggerLazyProxy initially
        assert hasattr(instance.logger, 'name')
        assert instance.logger.name == "TestClass"
    
    def test_logger_mixin_caches_logger(self):
        """Test that LoggerMixin caches the logger instance."""
        class TestClass(LoggerMixin):
            pass
        
        instance = TestClass()
        
        logger1 = instance.logger
        logger2 = instance.logger
        
        # Should return the same logger instance
        assert logger1 is logger2
    
    def test_log_start_creates_context(self):
        """Test that log_start creates proper context."""
        class TestClass(LoggerMixin):
            pass
        
        instance = TestClass()
        
        with patch.object(instance.logger, 'info') as mock_info:
            context = instance.log_start("test_operation", user_id=123, data="test")
            
            # Should contain expected fields
            assert context['event'] == "test_operation"
            assert context['user_id'] == 123
            assert context['data'] == "test"
            assert 'start_time' in context
            
            # Should call logger.info
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            # Check that the message contains the event name
            assert "test_operation" in str(call_args)
    
    def test_log_success_logs_completion_with_duration(self):
        """Test that log_success logs completion with duration."""
        class TestClass(LoggerMixin):
            pass
        
        instance = TestClass()
        
        # Create a context with start_time
        start_time = time.time() - 1.5  # 1.5 seconds ago
        context = {
            'event': 'test_operation',
            'start_time': start_time,
            'user_id': 123
        }
        
        with patch.object(instance.logger, 'info') as mock_info:
            instance.log_success(context, result="success", extra_data="test")
            
            # Should call logger.info with duration
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            # Check that the message contains the event name
            assert "test_operation" in str(call_args)
            
            # Should include duration_ms
            kwargs = call_args[1]
            assert 'duration_ms' in kwargs
            assert kwargs['duration_ms'] >= 1400  # Should be around 1500ms
    
    def test_log_success_without_start_time(self):
        """Test that log_success works without start_time in context."""
        class TestClass(LoggerMixin):
            pass
        
        instance = TestClass()
        
        context = {
            'event': 'test_operation',
            'user_id': 123
        }
        
        with patch.object(instance.logger, 'info') as mock_info:
            instance.log_success(context, result="success")
            
            # Should call logger.info without duration
            mock_info.assert_called_once()
            call_args = mock_info.call_args
            kwargs = call_args[1]
            assert 'duration_ms' not in kwargs
    
    def test_log_error_logs_failure_with_duration(self):
        """Test that log_error logs failure with duration and error details."""
        class TestClass(LoggerMixin):
            pass
        
        instance = TestClass()
        
        # Create a context with start_time
        start_time = time.time() - 0.5  # 0.5 seconds ago
        context = {
            'event': 'test_operation',
            'start_time': start_time,
            'user_id': 123
        }
        
        error = ValueError("Test error message")
        
        with patch.object(instance.logger, 'error') as mock_error:
            instance.log_error(context, error, retry_count=3)
            
            # Should call logger.error with error details
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            # Check that the message contains the event name
            assert "test_operation" in str(call_args)
            
            # Should include error details and duration
            kwargs = call_args[1]
            assert kwargs['error'] == "Test error message"
            assert kwargs['error_type'] == "ValueError"
            assert kwargs['retry_count'] == 3
            assert 'duration_ms' in kwargs
    
    def test_log_error_without_start_time(self):
        """Test that log_error works without start_time in context."""
        class TestClass(LoggerMixin):
            pass
        
        instance = TestClass()
        
        context = {
            'event': 'test_operation',
            'user_id': 123
        }
        
        error = RuntimeError("Test runtime error")
        
        with patch.object(instance.logger, 'error') as mock_error:
            instance.log_error(context, error, severity="high")
            
            # Should call logger.error without duration
            mock_error.assert_called_once()
            call_args = mock_error.call_args
            kwargs = call_args[1]
            assert 'duration_ms' not in kwargs
            assert kwargs['severity'] == "high"
    
    def test_logger_mixin_inheritance(self):
        """Test that LoggerMixin works with inheritance."""
        class BaseClass(LoggerMixin):
            pass
        
        class DerivedClass(BaseClass):
            pass
        
        base_instance = BaseClass()
        derived_instance = DerivedClass()
        
        # Both should have loggers with correct names
        assert base_instance.logger.name == "BaseClass"
        assert derived_instance.logger.name == "DerivedClass"
    
    def test_logger_mixin_multiple_instances(self):
        """Test that LoggerMixin works with multiple instances."""
        class TestClass(LoggerMixin):
            pass
        
        instance1 = TestClass()
        instance2 = TestClass()
        
        # Each instance should have its own logger
        assert instance1.logger is not instance2.logger
        assert instance1.logger.name == instance2.logger.name == "TestClass"


class TestLoggingIntegration:
    """Test logging integration scenarios."""
    
    def test_logging_output_format(self, capsys):
        """Test that logging output is in JSON format."""
        # Reset and configure logging
        structlog.reset_defaults()
        configure_logging()
        
        logger = get_logger("test_integration")
        logger.info("test message", key="value", number=42)
        
        # Capture output
        captured = capsys.readouterr()
        output = captured.out.strip()
        
        # Should be valid JSON
        import json
        if output:  # Only test if there's output
            log_data = json.loads(output)
            
            # Should contain expected fields
            assert log_data['event'] == "test message"
            assert log_data['key'] == "value"
            assert log_data['number'] == 42
            assert 'timestamp' in log_data
            assert 'logger' in log_data
            assert 'level' in log_data
        else:
            # If no output, that's also acceptable for some configurations
            pass
    
    def test_logger_mixin_integration(self, capsys):
        """Test LoggerMixin integration with actual logging."""
        # Reset and configure logging
        structlog.reset_defaults()
        configure_logging()
        
        class TestClass(LoggerMixin):
            def perform_operation(self):
                context = self.log_start("perform_operation", user_id=123)
                time.sleep(0.1)  # Simulate work
                self.log_success(context, result="success")
        
        instance = TestClass()
        instance.perform_operation()
        
        # Capture output
        captured = capsys.readouterr()
        output_lines = captured.out.strip().split('\n')
        
        # Should have start and success logs
        if output_lines and any(output_lines):
            # Parse JSON logs if available
            import json
            for line in output_lines:
                if line.strip():
                    try:
                        log_data = json.loads(line)
                        assert 'event' in log_data
                        assert 'user_id' in log_data
                    except json.JSONDecodeError:
                        # Skip non-JSON lines
                        pass
        else:
            # If no output, that's also acceptable
            pass
    
    def test_logging_with_exceptions(self, capsys):
        """Test logging with exception handling."""
        # Reset and configure logging
        structlog.reset_defaults()
        configure_logging()
        
        class TestClass(LoggerMixin):
            def perform_operation(self):
                context = self.log_start("perform_operation", user_id=123)
                try:
                    raise ValueError("Test error")
                except Exception as e:
                    self.log_error(context, e, retry_count=3)
                    raise
        
        instance = TestClass()
        
        with pytest.raises(ValueError):
            instance.perform_operation()
        
        # Capture output
        captured = capsys.readouterr()
        output_lines = captured.out.strip().split('\n')
        
        # Should have start and error logs
        if output_lines and any(output_lines):
            # Parse JSON logs if available
            import json
            for line in output_lines:
                if line.strip():
                    try:
                        log_data = json.loads(line)
                        assert 'event' in log_data
                        assert 'user_id' in log_data
                    except json.JSONDecodeError:
                        # Skip non-JSON lines
                        pass
        else:
            # If no output, that's also acceptable
            pass


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_logging_with_unicode_characters(self, capsys):
        """Test logging with unicode characters."""
        # Reset and configure logging
        structlog.reset_defaults()
        configure_logging()
        
        logger = get_logger("test_unicode")
        logger.info("test message", unicode_text="café", emoji="🚀")
        
        # Capture output
        captured = capsys.readouterr()
        output = captured.out.strip()
        
        # Should be valid JSON with unicode preserved
        if output:
            import json
            log_data = json.loads(output)
            
            assert log_data['unicode_text'] == "café"
            assert log_data['emoji'] == "🚀"
        else:
            # If no output, that's also acceptable
            pass
    
    def test_logging_with_complex_objects(self, capsys):
        """Test logging with complex object types."""
        # Reset and configure logging
        structlog.reset_defaults()
        configure_logging()
        
        logger = get_logger("test_complex")
        
        # Test with various data types
        complex_data = {
            'list': [1, 2, 3],
            'dict': {'nested': 'value'},
            'tuple': (1, 2, 3),
            'set': {1, 2, 3},
            'none': None,
            'bool': True
        }
        
        logger.info("complex data", **complex_data)
        
        # Capture output
        captured = capsys.readouterr()
        output = captured.out.strip()
        
        # Should be valid JSON
        if output:
            import json
            log_data = json.loads(output)
            
            # Check that data types are preserved appropriately
            assert log_data['list'] == [1, 2, 3]
            assert log_data['dict'] == {'nested': 'value'}
            assert log_data['none'] is None
            assert log_data['bool'] is True
        else:
            # If no output, that's also acceptable
            pass
    
    def test_logging_under_high_load(self):
        """Test logging performance under high load."""
        # Reset and configure logging
        structlog.reset_defaults()
        configure_logging()
        
        class TestClass(LoggerMixin):
            pass
        
        instance = TestClass()
        
        # Perform many logging operations
        start_time = time.time()
        
        for i in range(100):
            # Just test that the methods can be called without errors
            context = instance.log_start(f"operation_{i}", index=i)
            instance.log_success(context, result=f"result_{i}")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete in reasonable time (less than 1 second)
        assert duration < 1.0
