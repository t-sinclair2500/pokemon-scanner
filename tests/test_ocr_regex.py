"""Tests for OCR regex functionality."""

import re

import pytest

from src.ocr.regexes import (
    COLLECTOR_NUMBER_PATTERN,
    is_valid_collector_number,
    parse_collector_number,
)


class TestCollectorNumberRegex:
    """Test collector number pattern extraction."""

    def test_valid_collector_number_patterns(self):
        """Test various valid collector number formats."""
        test_cases = [
            ("25/102", 25, 102),
            ("4/102", 4, 102),
            ("150/165", 150, 165),
            ("  25 / 102  ", 25, 102),
            ("Card 25/102 Rare", 25, 102),
            ("123/123", 123, 123),
            ("1/1", 1, 1),
            ("99/99", 99, 99),
            ("  1 / 159  ", 1, 159),
            ("Number: 25/102", 25, 102),
        ]

        for input_text, expected_num, expected_den in test_cases:
            result = parse_collector_number(input_text)
            assert result is not None, f"Should parse: {input_text}"
            assert (
                result["num"] == expected_num
            ), f"Expected num {expected_num}, got {result['num']} for {input_text}"
            assert (
                result["den"] == expected_den
            ), f"Expected den {expected_den}, got {result['den']} for {input_text}"

    def test_invalid_collector_numbers(self):
        """Test patterns that should NOT match."""
        invalid_cases = [
            "25/",  # Missing denominator
            "/102",  # Missing numerator
            "1234/102",  # Numerator too long (4 digits)
            "25/1234",  # Denominator too long (4 digits)
            "no numbers",  # No numbers at all
            "25-102",  # Wrong separator
            "25.102",  # Wrong separator
            "25 102",  # No separator
            "abc",  # Just letters
            "12.34",  # Decimal numbers
            "25/",  # Incomplete
            "/102",  # Incomplete
            "25",  # Just numerator
            "102",  # Just denominator
            "25//102",  # Double separator
            "25 / / 102",  # Multiple separators
        ]

        for invalid_text in invalid_cases:
            result = parse_collector_number(invalid_text)
            assert result is None, f"Should NOT parse: {invalid_text}"

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Test single digit numbers
        result = parse_collector_number("1/1")
        assert result == {"num": 1, "den": 1}

        # Test three digit numbers
        result = parse_collector_number("999/999")
        assert result == {"num": 999, "den": 999}

        # Test with extra whitespace
        result = parse_collector_number("  25  /  102  ")
        assert result == {"num": 25, "den": 102}

        # Test with surrounding text
        result = parse_collector_number("Card number 25/102 from set")
        assert result == {"num": 25, "den": 102}

    def test_regex_pattern_consistency(self):
        """Test that the compiled pattern matches the function behavior."""
        # Test that the compiled pattern gives same results
        test_text = "25/102"

        # Use the compiled pattern directly
        match = COLLECTOR_NUMBER_PATTERN.search(test_text)
        assert match is not None

        # Use the function
        result = parse_collector_number(test_text)
        assert result is not None

        # Both should give same results
        assert int(match.group(1)) == result["num"]
        assert int(match.group(2)) == result["den"]

    def test_is_valid_collector_number_function(self):
        """Test the is_valid_collector_number helper function."""
        # Valid cases
        assert is_valid_collector_number("25/102")
        assert is_valid_collector_number("1/1")
        assert is_valid_collector_number("  25 / 102  ")
        assert is_valid_collector_number("25/102")  # Valid format
        assert is_valid_collector_number("1/1")     # Valid format
        assert is_valid_collector_number("  25 / 102  ")  # Valid with spaces
        assert not is_valid_collector_number("25/")
        assert not is_valid_collector_number("/102")
        assert not is_valid_collector_number("abc")
        assert not is_valid_collector_number("25-102")
        assert not is_valid_collector_number("")

    def test_number_range_validation(self):
        """Test that numbers are within valid range (1-999)."""
        # Valid ranges
        assert parse_collector_number("1/1") == {"num": 1, "den": 1}
        assert parse_collector_number("999/999") == {"num": 999, "den": 999}
        assert parse_collector_number("100/200") == {"num": 100, "den": 200}

        # Invalid ranges (should not match due to regex pattern)
        assert parse_collector_number("1000/1000") is None  # 4 digits
        assert parse_collector_number("0/100") is None  # 0 not allowed
        assert parse_collector_number("100/0") is None  # 0 not allowed


if __name__ == "__main__":
    pytest.main([__file__])
