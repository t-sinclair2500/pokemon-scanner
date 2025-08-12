"""Regex patterns for Pokemon card text extraction."""

import re
from typing import Optional, Dict


def parse_collector_number(text: str) -> Optional[Dict[str, int]]:
    """
    Parse collector number from text using regex.
    
    Args:
        text: Text containing collector number
        
    Returns:
        Dict with 'num' and 'den' keys, or None if parsing fails
        
    Examples:
        >>> parse_collector_number("12 / 159")
        {'num': 12, 'den': 159}
        >>> parse_collector_number("123/123")
        {'num': 123, 'den': 123}
        >>> parse_collector_number("1/1")
        {'num': 1, 'den': 1}
    """
    # Pattern: \b([1-9]\d{0,2})\s*/\s*([1-9]\d{0,2})\b
    # This excludes 0 as a valid number (collector numbers start from 1)
    pattern = re.compile(r'\b([1-9]\d{0,2})\s*/\s*([1-9]\d{0,2})\b')
    
    match = pattern.search(text)
    if match:
        try:
            num = int(match.group(1))
            den = int(match.group(2))
            return {'num': num, 'den': den}
        except (ValueError, IndexError):
            return None
    
    return None


def is_valid_collector_number(text: str) -> bool:
    """
    Check if text contains a valid collector number pattern.
    
    Args:
        text: Text to validate
        
    Returns:
        True if valid collector number pattern found, False otherwise
    """
    return parse_collector_number(text) is not None


# Compiled regex pattern for reuse
# Pattern: \b([1-9]\d{0,2})\s*/\s*([1-9]\d{0,2})\b
# This excludes 0 as a valid number (collector numbers start from 1)
COLLECTOR_NUMBER_PATTERN = re.compile(r'\b([1-9]\d{0,2})\s*/\s*([1-9]\d{0,2})\b')
