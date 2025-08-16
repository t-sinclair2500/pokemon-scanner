"""
Input validation and sanitization utilities for the Pokemon scanner application.

This module provides validation functions to ensure data integrity and
prevent invalid data from causing runtime errors.
"""

import re
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from src.utils.error_handler import ConfigurationError, ErrorContext


def validate_file_path(file_path: Union[str, Path], must_exist: bool = False) -> Path:
    """
    Validate and normalize a file path.
    
    Args:
        file_path: File path to validate
        must_exist: Whether the file must already exist
        
    Returns:
        Normalized Path object
        
    Raises:
        ConfigurationError: If path is invalid or file doesn't exist when required
    """
    try:
        path = Path(file_path)
        
        # Check if file must exist before calling resolve()
        if must_exist and not path.exists():
            raise ConfigurationError(
                f"File does not exist: {path}",
                details={"file_path": str(path), "must_exist": must_exist}
            )
        
        # Now resolve the path
        resolved_path = path.resolve()
        return resolved_path
        
    except ConfigurationError:
        # Re-raise ConfigurationError as-is
        raise
    except Exception as e:
        raise ConfigurationError(
            f"Invalid file path: {file_path}",
            details={"file_path": str(file_path), "error": str(e)}
        )


def validate_directory_path(dir_path: Union[str, Path], create_if_missing: bool = False) -> Path:
    """
    Validate and normalize a directory path.
    
    Args:
        dir_path: Directory path to validate
        create_if_missing: Whether to create the directory if it doesn't exist
        
    Returns:
        Normalized Path object
        
    Raises:
        ConfigurationError: If path is invalid or directory cannot be created
    """
    try:
        path = Path(dir_path)
        
        # Check if directory exists before calling resolve()
        if create_if_missing and not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        elif not path.exists():
            raise ConfigurationError(
                f"Directory does not exist: {path}",
                details={"dir_path": str(path), "create_if_missing": create_if_missing}
            )
        
        # Now resolve the path
        resolved_path = path.resolve()
        
        # Check if it's actually a directory
        if not resolved_path.is_dir():
            raise ConfigurationError(
                f"Path is not a directory: {resolved_path}",
                details={"dir_path": str(resolved_path)}
            )
        
        return resolved_path
        
    except ConfigurationError:
        # Re-raise ConfigurationError as-is
        raise
    except Exception as e:
        raise ConfigurationError(
            f"Invalid directory path: {dir_path}",
            details={"dir_path": str(dir_path), "error": str(e)}
        )


def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> str:
    """
    Validate a URL string.
    
    Args:
        url: URL string to validate
        allowed_schemes: List of allowed URL schemes (default: http, https)
        
    Returns:
        Normalized URL string
        
    Raises:
        ConfigurationError: If URL is invalid
    """
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    # Basic URL pattern with stricter validation
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::(?:[1-9]\d{0,3}|[1-5]\d{4}|6[0-4]\d{3}|65[0-4]\d{2}|655[0-2]\d|6553[0-5]))?'  # valid port (1-65535)
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    if not url_pattern.match(url):
        raise ConfigurationError(
            f"Invalid URL format: {url}",
            details={"url": url, "allowed_schemes": allowed_schemes}
        )
    
    # Check scheme
    scheme = url.split('://')[0].lower()
    if scheme not in allowed_schemes:
        raise ConfigurationError(
            f"URL scheme '{scheme}' not allowed. Allowed schemes: {allowed_schemes}",
            details={"url": url, "scheme": scheme, "allowed_schemes": allowed_schemes}
        )
    
    return url


def validate_api_key(api_key: str, min_length: int = 10) -> str:
    """
    Validate an API key string.
    
    Args:
        api_key: API key to validate
        min_length: Minimum required length
        
    Returns:
        Normalized API key string
        
    Raises:
        ConfigurationError: If API key is invalid
    """
    if not api_key or not isinstance(api_key, str):
        raise ConfigurationError(
            "API key must be a non-empty string",
            details={"api_key": api_key, "min_length": min_length}
        )
    
    # Remove leading/trailing whitespace
    normalized_key = api_key.strip()
    
    # Check for empty string after stripping
    if not normalized_key:
        raise ConfigurationError(
            "API key must be a non-empty string",
            details={"api_key": api_key, "min_length": min_length}
        )
    
    # Check for common invalid patterns
    if normalized_key.lower() in ['none', 'null', 'undefined']:
        raise ConfigurationError(
            "API key cannot be empty or placeholder value",
            details={"api_key": normalized_key}
        )
    
    if len(normalized_key) < min_length:
        raise ConfigurationError(
            f"API key too short. Minimum length: {min_length}",
            details={"api_key_length": len(normalized_key), "min_length": min_length}
        )
    
    return normalized_key


def validate_numeric_range(
    value: Union[int, float],
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    field_name: str = "value"
) -> Union[int, float]:
    """
    Validate a numeric value is within specified range.
    
    Args:
        value: Numeric value to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        field_name: Name of the field for error messages
        
    Returns:
        The validated value
        
    Raises:
        ConfigurationError: If value is outside the allowed range
    """
    if min_value is not None and value < min_value:
        raise ConfigurationError(
            f"{field_name} {value} is below minimum {min_value}",
            details={
                "field_name": field_name,
                "value": value,
                "min_value": min_value,
                "max_value": max_value
            }
        )
    
    if max_value is not None and value > max_value:
        raise ConfigurationError(
            f"{field_name} {value} is above maximum {max_value}",
            details={
                "field_name": field_name,
                "value": value,
                "min_value": min_value,
                "max_value": max_value
            }
        )
    
    return value


def validate_string_length(
    value: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    field_name: str = "string"
) -> str:
    """
    Validate a string value length is within specified range.
    
    Args:
        value: String value to validate
        min_length: Minimum allowed length (inclusive)
        max_length: Maximum allowed length (inclusive)
        field_name: Name of the field for error messages
        
    Returns:
        The validated string
        
    Raises:
        ConfigurationError: If string length is outside the allowed range
    """
    if not isinstance(value, str):
        raise ConfigurationError(
            f"{field_name} must be a string, got {type(value).__name__}",
            details={"field_name": field_name, "value_type": type(value).__name__}
        )
    
    length = len(value)
    
    if min_length is not None and length < min_length:
        raise ConfigurationError(
            f"{field_name} length {length} is below minimum {min_length}",
            details={
                "field_name": field_name,
                "length": length,
                "min_length": min_length,
                "max_length": max_length
            }
        )
    
    if max_length is not None and length > max_length:
        raise ConfigurationError(
            f"{field_name} length {length} is above maximum {max_length}",
            details={
                "field_name": field_name,
                "length": length,
                "min_length": min_length,
                "max_length": max_length
            }
        )
    
    return value


def validate_enum_value(
    value: Any,
    allowed_values: List[Any],
    field_name: str = "value"
) -> Any:
    """
    Validate a value is one of the allowed enum values.
    
    Args:
        value: Value to validate
        allowed_values: List of allowed values
        field_name: Name of the field for error messages
        
    Returns:
        The validated value
        
    Raises:
        ConfigurationError: If value is not in the allowed list
    """
    if value not in allowed_values:
        raise ConfigurationError(
            f"{field_name} '{value}' is not allowed. Allowed values: {allowed_values}",
            details={
                "field_name": field_name,
                "value": value,
                "allowed_values": allowed_values
            }
        )
    
    return value


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename by removing invalid characters and limiting length.
    
    Args:
        filename: Original filename
        max_length: Maximum allowed filename length
        
    Returns:
        Sanitized filename
    """
    # Remove invalid characters for most filesystems
    invalid_chars = '<>:"/\\|?*'
    sanitized = ''.join(char for char in filename if char not in invalid_chars)
    
    # Remove leading/trailing spaces first
    sanitized = sanitized.strip()
    
    # Find the last dot that's followed by non-dot characters (the extension)
    last_dot_pos = -1
    for i in range(len(sanitized) - 1, -1, -1):
        if sanitized[i] == '.':
            # Check if this dot is followed by non-dot characters
            if i < len(sanitized) - 1 and sanitized[i + 1] != '.':
                last_dot_pos = i
                break
    
    if last_dot_pos > 0:
        # We have a valid extension
        name_part = sanitized[:last_dot_pos]
        ext_part = sanitized[last_dot_pos + 1:]
        
        # Clean the name part - remove all dots and replace spaces with underscores
        name_part = re.sub(r'[.\s]+', '_', name_part)
        name_part = re.sub(r'_+', '_', name_part)
        name_part = name_part.strip('_')
        
        # Clean the extension part - remove dots
        ext_part = ext_part.strip('.')
        
        # Rejoin only if both parts exist
        if name_part and ext_part:
            sanitized = f"{name_part}.{ext_part}"
        elif name_part:
            sanitized = name_part
        elif ext_part:
            sanitized = ext_part
        else:
            sanitized = ""
    else:
        # No valid extension, just clean the name
        sanitized = re.sub(r'[.\s]+', '_', sanitized)
        sanitized = re.sub(r'_+', '_', sanitized)
        sanitized = sanitized.strip('_')
    
    # Limit length
    if len(sanitized) > max_length:
        name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
        max_name_length = max_length - len(ext) - 1 if ext else max_length
        sanitized = name[:max_name_length] + (f'.{ext}' if ext else '')
    
    # Ensure filename is not empty
    if not sanitized:
        sanitized = 'unnamed_file'
    
    return sanitized

