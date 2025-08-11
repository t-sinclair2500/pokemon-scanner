"""Tests for OCR regex functionality."""

import pytest
import re

from src.ocr.extract import CardInfo


class TestCollectorNumberRegex:
    """Test collector number pattern extraction."""
    
    def test_collector_number_patterns(self):
        """Test various collector number formats."""
        # Pattern: \b(\d{1,3})\s*/\s*(\d{1,3})\b
        pattern = re.compile(r'\b(\d{1,3})\s*/\s*(\d{1,3})\b')
        
        # Valid patterns
        test_cases = [
            ("25/102", "25/102"),
            ("4/102", "4/102"), 
            ("150/165", "150/165"),
            ("  25 / 102  ", "25/102"),
            ("Card 25/102 Rare", "25/102"),
        ]
        
        for input_text, expected in test_cases:
            match = pattern.search(input_text)
            assert match is not None, f"Should match: {input_text}"
            result = f"{match.group(1)}/{match.group(2)}"
            assert result == expected
    
    def test_invalid_collector_numbers(self):
        """Test patterns that should NOT match."""
        pattern = re.compile(r'\b(\d{1,3})\s*/\s*(\d{1,3})\b')
        
        invalid_cases = [
            "25/", "/102", "1234/102", "25/1234", "no numbers", "25-102"
        ]
        
        for invalid_text in invalid_cases:
            match = pattern.search(invalid_text)
            assert match is None, f"Should NOT match: {invalid_text}"


class TestCardInfo:
    """Test CardInfo dataclass."""
    
    def test_card_info_creation(self):
        """Test CardInfo creation."""
        card_info = CardInfo(
            name="Charizard",
            collector_number="4/102",
            confidence=85.5
        )
        
        assert card_info.name == "Charizard"
        assert card_info.collector_number == "4/102"
        assert card_info.confidence == 85.5
        assert card_info.ocr_result is None
    
    def test_card_info_defaults(self):
        """Test CardInfo defaults."""
        card_info = CardInfo()
        
        assert card_info.name is None
        assert card_info.collector_number is None
        assert card_info.confidence == 0.0
        assert card_info.ocr_result is None


if __name__ == "__main__":
    pytest.main([__file__])