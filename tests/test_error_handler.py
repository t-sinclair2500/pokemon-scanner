"""
Tests for the error handling and logging system.

This module tests the custom exception classes, error handling utilities,
and logging functionality to ensure robust error reporting throughout the app.
"""

import pytest
import logging
from unittest.mock import Mock, patch
from src.utils.error_handler import (
    PokemonScannerError,
    ConfigurationError,
    CaptureError,
    OCRError,
    ResolutionError,
    PricingError,
    CacheError,
    WriterError,
    NetworkError,
    ErrorContext,
    handle_error,
    safe_execute,
    validate_required_fields
)


class TestPokemonScannerError:
    """Test the base exception class and its subclasses."""
    
    def test_base_exception_creation(self):
        """Test basic exception creation with message only."""
        error = PokemonScannerError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details == {}
    
    def test_exception_with_details(self):
        """Test exception creation with additional details."""
        details = {"field": "value", "code": 123}
        error = PokemonScannerError("Test error", details)
        assert str(error) == "Test error | Details: {'field': 'value', 'code': 123}"
        assert error.details == details
    
    def test_exception_inheritance(self):
        """Test that all custom exceptions inherit from PokemonScannerError."""
        exceptions = [
            ConfigurationError,
            CaptureError,
            OCRError,
            ResolutionError,
            PricingError,
            CacheError,
            WriterError,
            NetworkError
        ]
        
        for exc_class in exceptions:
            assert issubclass(exc_class, PokemonScannerError)
    
    def test_exception_types(self):
        """Test that each exception type can be created and has correct message."""
        test_cases = [
            (ConfigurationError, "Configuration error"),
            (CaptureError, "Capture error"),
            (OCRError, "OCR error"),
            (ResolutionError, "Resolution error"),
            (PricingError, "Pricing error"),
            (CacheError, "Cache error"),
            (WriterError, "Writer error"),
            (NetworkError, "Network error")
        ]
        
        for exc_class, message in test_cases:
            error = exc_class(message)
            assert isinstance(error, exc_class)
            assert error.message == message


class TestErrorContext:
    """Test the ErrorContext dataclass."""
    
    def test_error_context_creation(self):
        """Test basic ErrorContext creation."""
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        assert context.operation == "test_operation"
        assert context.module == "test_module"
        assert context.function == "test_function"
        assert context.input_data is None
        assert context.timestamp is None
    
    def test_error_context_with_optional_fields(self):
        """Test ErrorContext creation with all optional fields."""
        input_data = {"param1": "value1", "param2": 42}
        timestamp = "2025-01-12 10:00:00"
        
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function",
            input_data=input_data,
            timestamp=timestamp
        )
        
        assert context.input_data == input_data
        assert context.timestamp == timestamp


class TestHandleError:
    """Test the centralized error handling function."""
    
    def test_handle_error_with_custom_exception(self):
        """Test error handling with a custom exception."""
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        error = ConfigurationError("Test config error", {"missing_field": "api_key"})
        logger = Mock(spec=logging.Logger)
        
        # Test with reraise=True (default)
        with pytest.raises(ConfigurationError) as exc_info:
            handle_error(error, context, logger)
        
        assert exc_info.value == error
        
        # Check that error was logged
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "test_module.test_function" in call_args[0][0]
        assert "Test config error" in call_args[0][0]
    
    def test_handle_error_with_standard_exception(self):
        """Test error handling with a standard Python exception."""
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        error = ValueError("Invalid value")
        logger = Mock(spec=logging.Logger)
        
        with pytest.raises(ValueError) as exc_info:
            handle_error(error, context, logger)
        
        assert exc_info.value == error
        
        # Check that error was logged
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "Invalid value" in call_args[0][0]
    
    def test_handle_error_without_reraise(self):
        """Test error handling without re-raising the exception."""
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        error = ConfigurationError("Test config error")
        logger = Mock(spec=logging.Logger)
        
        # Test with reraise=False
        result = handle_error(error, context, logger, reraise=False, default_return="fallback_value")
        
        assert result == "fallback_value"
        
        # Check that error was logged
        logger.error.assert_called_once()
    
    def test_handle_error_logging_context(self):
        """Test that error logging includes all context information."""
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function",
            input_data={"param": "value"},
            timestamp="2025-01-12 10:00:00"
        )
        
        error = OCRError("OCR processing failed")
        logger = Mock(spec=logging.Logger)
        
        with pytest.raises(OCRError):
            handle_error(error, context, logger)
        
        # Check that context was included in log extras
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        
        # Verify extra fields are present
        extra = call_args[1]['extra']
        assert 'error_type' in extra
        assert 'operation' in extra
        assert 'error_module' in extra
        assert 'error_function' in extra
        assert 'input_data' in extra
        assert 'timestamp' in extra


class TestSafeExecute:
    """Test the safe execution utility function."""
    
    def test_safe_execute_success(self):
        """Test safe execution when function succeeds."""
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        logger = Mock(spec=logging.Logger)
        
        def test_func(x, y):
            return x + y
        
        result = safe_execute(test_func, 2, 3, context=context, logger=logger)
        
        assert result == 5
        # Logger should not have been called
        assert not logger.error.called
    
    def test_safe_execute_failure(self):
        """Test safe execution when function fails."""
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        logger = Mock(spec=logging.Logger)
        
        def test_func():
            raise ValueError("Test error")
        
        result = safe_execute(test_func, context=context, logger=logger, default_return="fallback")
        
        assert result == "fallback"
        
        # Check that error was logged
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "Test error" in call_args[0][0]
    
    def test_safe_execute_with_args_kwargs(self):
        """Test safe execution with various argument types."""
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        logger = Mock(spec=logging.Logger)
        
        def test_func(name, age=0, **kwargs):
            return f"{name} is {age} years old with {len(kwargs)} extra args"
        
        result = safe_execute(
            test_func, 
            "Alice", 
            age=25, 
            city="NYC", 
            context=context, 
            logger=logger
        )
        
        assert result == "Alice is 25 years old with 1 extra args"


class TestValidateRequiredFields:
    """Test the field validation utility function."""
    
    def test_validate_required_fields_success(self):
        """Test validation when all required fields are present."""
        data = {"field1": "value1", "field2": "value2", "field3": None}
        required_fields = ["field1", "field2"]
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        # Should not raise an exception
        validate_required_fields(data, required_fields, context)
    
    def test_validate_required_fields_missing(self):
        """Test validation when required fields are missing."""
        data = {"field1": "value1"}
        required_fields = ["field1", "field2", "field3"]
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            validate_required_fields(data, required_fields, context)
        
        error = exc_info.value
        assert "Missing required fields" in error.message
        assert "field2" in error.details["missing_fields"]
        assert "field3" in error.details["missing_fields"]
        assert "field1" not in error.details["missing_fields"]
    
    def test_validate_required_fields_none_values(self):
        """Test validation when required fields have None values."""
        data = {"field1": "value1", "field2": None, "field3": "value3"}
        required_fields = ["field1", "field2", "field3"]
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            validate_required_fields(data, required_fields, context)
        
        error = exc_info.value
        assert "field2" in error.details["missing_fields"]
    
    def test_validate_required_fields_empty_data(self):
        """Test validation with empty data dictionary."""
        data = {}
        required_fields = ["field1", "field2"]
        context = ErrorContext(
            operation="test_operation",
            module="test_module",
            function="test_function"
        )
        
        with pytest.raises(ConfigurationError) as exc_info:
            validate_required_fields(data, required_fields, context)
        
        error = exc_info.value
        assert "field1" in error.details["missing_fields"]
        assert "field2" in error.details["missing_fields"]
        assert error.details["available_fields"] == []


class TestErrorHandlingIntegration:
    """Test integration of error handling with real scenarios."""
    
    def test_camera_capture_error_scenario(self):
        """Test error handling in a camera capture scenario."""
        context = ErrorContext(
            operation="camera_capture",
            module="capture.camera",
            function="capture_frame",
            input_data={"camera_id": 0}
        )
        
        logger = Mock(spec=logging.Logger)
        
        # Simulate a camera capture error
        error = CaptureError("Camera device not found", {"camera_id": 0, "error_code": "DEVICE_NOT_FOUND"})
        
        with pytest.raises(CaptureError):
            handle_error(error, context, logger)
        
        # Verify error was logged with proper context
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "capture.camera.capture_frame" in call_args[0][0]
        assert "Camera device not found" in call_args[0][0]
    
    def test_ocr_processing_error_scenario(self):
        """Test error handling in an OCR processing scenario."""
        context = ErrorContext(
            operation="ocr_extraction",
            module="ocr.extract",
            function="extract_collector_number",
            input_data={"image_path": "/path/to/image.jpg"}
        )
        
        logger = Mock(spec=logging.Logger)
        
        # Simulate an OCR processing error
        error = OCRError("Tesseract not found", {"tesseract_path": "/usr/bin/tesseract"})
        
        with pytest.raises(OCRError):
            handle_error(error, context, logger)
        
        # Verify error was logged with proper context
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "ocr.extract.extract_collector_number" in call_args[0][0]
        assert "Tesseract not found" in call_args[0][0]
    
    def test_network_request_error_scenario(self):
        """Test error handling in a network request scenario."""
        context = ErrorContext(
            operation="api_request",
            module="resolve.poketcg",
            function="get_card",
            input_data={"card_id": "base1-1"}
        )
        
        logger = Mock(spec=logging.Logger)
        
        # Simulate a network error
        error = NetworkError("Connection timeout", {"endpoint": "https://api.pokemontcg.io/v2/cards/base1-1"})
        
        with pytest.raises(NetworkError):
            handle_error(error, context, logger)
        
        # Verify error was logged with proper context
        logger.error.assert_called_once()
        call_args = logger.error.call_args
        assert "resolve.poketcg.get_card" in call_args[0][0]
        assert "Connection timeout" in call_args[0][0]
