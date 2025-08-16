"""
Retry utilities with exponential backoff for the Pokemon scanner application.

This module provides retry decorators and utilities to handle transient failures
gracefully, particularly for network requests and external API calls.
"""

import asyncio
import functools
import logging
import random
import time
from typing import Any, Callable, Optional, Type, Union
from src.utils.error_handler import PokemonScannerError, ErrorContext


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Union[Type[Exception], tuple] = Exception,
    logger: Optional[logging.Logger] = None
):
    """
    Retry decorator with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
        exceptions: Exception types to retry on
        logger: Logger instance for retry logging
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        if logger:
                            logger.error(
                                f"Function {func.__name__} failed after {max_attempts} attempts",
                                extra={
                                    "function": func.__name__,
                                    "attempts": max_attempts,
                                    "final_exception": str(e)
                                }
                            )
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                    
                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    if logger:
                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}), "
                            f"retrying in {delay:.2f}s",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt,
                                "max_attempts": max_attempts,
                                "delay": delay,
                                "exception": str(e)
                            }
                        )
                    
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        if logger:
                            logger.error(
                                f"Async function {func.__name__} failed after {max_attempts} attempts",
                                extra={
                                    "function": func.__name__,
                                    "attempts": max_attempts,
                                    "final_exception": str(e)
                                }
                            )
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                    
                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    if logger:
                        logger.warning(
                            f"Async function {func.__name__} failed (attempt {attempt}/{max_attempts}), "
                            f"retrying in {delay:.2f}s",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt,
                                "max_attempts": max_attempts,
                                "delay": delay,
                                "exception": str(e)
                            }
                        )
                    
                    await asyncio.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


def retry_with_context(
    context: ErrorContext,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Union[Type[Exception], tuple] = Exception,
    logger: Optional[logging.Logger] = None
):
    """
    Retry decorator that includes error context for better logging.
    
    Args:
        context: Error context for logging
        max_attempts: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
        exceptions: Exception types to retry on
        logger: Logger instance for retry logging
        
    Returns:
        Decorated function with retry logic and context
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        if logger:
                            logger.error(
                                f"Function {func.__name__} failed after {max_attempts} attempts",
                                extra={
                                    "function": func.__name__,
                                    "attempts": max_attempts,
                                    "final_exception": str(e),
                                    "context": context
                                }
                            )
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                    
                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    if logger:
                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}), "
                            f"retrying in {delay:.2f}s",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt,
                                "max_attempts": max_attempts,
                                "delay": delay,
                                "exception": str(e),
                                "context": context
                            }
                        )
                    
                    time.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        if logger:
                            logger.error(
                                f"Async function {func.__name__} failed after {max_attempts} attempts",
                                extra={
                                    "function": func.__name__,
                                    "attempts": max_attempts,
                                    "final_exception": str(e),
                                    "context": context
                                }
                            )
                        raise e
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** (attempt - 1)), max_delay)
                    
                    if jitter:
                        delay *= (0.5 + random.random() * 0.5)
                    
                    if logger:
                        logger.warning(
                            f"Async function {func.__name__} failed (attempt {attempt}/{max_attempts}), "
                            f"retrying in {delay:.2f}s",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt,
                                "max_attempts": max_attempts,
                                "delay": delay,
                                "exception": str(e),
                                "context": context
                            }
                        )
                    
                    await asyncio.sleep(delay)
            
            # This should never be reached, but just in case
            raise last_exception
        
        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper
    
    return decorator


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable.
    
    Args:
        error: The exception to check
        
    Returns:
        True if the error is retryable, False otherwise
    """
    # Network-related errors that are typically transient
    retryable_errors = (
        ConnectionError,
        TimeoutError,
        OSError,  # Covers many network-related errors
    )
    
    # Check if it's a retryable error type
    if isinstance(error, retryable_errors):
        return True
    
    # Check for specific error messages that indicate retryable conditions
    error_str = str(error).lower()
    retryable_keywords = [
        'timeout', 'connection refused', 'network unreachable',
        'temporary failure', 'service unavailable', 'service temporarily unavailable', 'rate limit',
        'too many requests', 'server error', 'gateway timeout'
    ]
    
    return any(keyword in error_str for keyword in retryable_keywords)

