"""
Centralized error handling for the Pokemon scanner application.

This module provides custom exception classes and error handling utilities
to ensure robust operation and consistent error reporting throughout the app.
"""

import logging
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass


class PokemonScannerError(Exception):
    """Base exception class for all Pokemon scanner errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class ConfigurationError(PokemonScannerError):
    """Raised when there are configuration or environment variable issues."""
    pass


class CaptureError(PokemonScannerError):
    """Raised when camera capture or image processing fails."""
    pass


class OCRError(PokemonScannerError):
    """Raised when OCR processing fails or produces invalid results."""
    pass


class ResolutionError(PokemonScannerError):
    """Raised when card resolution fails due to API issues or invalid data."""
    pass


class PricingError(PokemonScannerError):
    """Raised when pricing data extraction or processing fails."""
    pass


class CacheError(PokemonScannerError):
    """Raised when cache operations fail."""
    pass


class WriterError(PokemonScannerError):
    """Raised when CSV writing or file operations fail."""
    pass


class NetworkError(PokemonScannerError):
    """Raised when network requests fail."""
    pass


@dataclass
class ErrorContext:
    """Context information for error reporting."""
    operation: str
    module: str
    function: str
    input_data: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None


def handle_error(
    error: Exception,
    context: ErrorContext,
    logger: logging.Logger,
    reraise: bool = True,
    default_return: Any = None
) -> Any:
    """
    Centralized error handling with logging and optional recovery.
    
    Args:
        error: The exception that occurred
        context: Context information about where the error occurred
        logger: Logger instance to use for error reporting
        reraise: Whether to re-raise the exception after logging
        default_return: Value to return if not re-raising
        
    Returns:
        The default_return value if not re-raising
        
    Raises:
        The original exception if reraise is True
    """
    error_msg = f"Error in {context.module}.{context.function} during {context.operation}"
    
    if isinstance(error, PokemonScannerError):
        error_msg += f": {error.message}"
        if error.details:
            error_msg += f" | Details: {error.details}"
    else:
        error_msg += f": {str(error)}"
    
    # Log the error with context
    logger.error(
        error_msg,
        extra={
            "error_type": type(error).__name__,
            "operation": context.operation,
            "error_module": context.module,
            "error_function": context.function,
            "input_data": context.input_data,
            "timestamp": context.timestamp,
            "exception": error
        },
        exc_info=True
    )
    
    if reraise:
        raise error
    
    return default_return


def safe_execute(
    func,
    *args,
    context: ErrorContext,
    logger: logging.Logger,
    default_return: Any = None,
    **kwargs
) -> Any:
    """
    Safely execute a function with error handling and logging.
    
    Args:
        func: Function to execute
        context: Error context information
        logger: Logger instance
        default_return: Value to return on error
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        Function result or default_return on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        return handle_error(e, context, logger, reraise=False, default_return=default_return)


def validate_required_fields(data: Dict[str, Any], required_fields: list, context: ErrorContext) -> None:
    """
    Validate that required fields are present in data.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        context: Error context for reporting
        
    Raises:
        ConfigurationError: If required fields are missing
    """
    missing_fields = [field for field in required_fields if field not in data or data[field] is None]
    
    if missing_fields:
        raise ConfigurationError(
            f"Missing required fields: {missing_fields}",
            details={
                "missing_fields": missing_fields,
                "available_fields": list(data.keys()),
                "context": context
            }
        )

