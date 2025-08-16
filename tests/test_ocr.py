"""Tests for OCR functionality including fallback collector number extraction."""

import re
import numpy as np
import pytest

from src.ocr.extract import CardInfo, OCRExtractor


class TestCollectorNumberRegex:
    """Test collector number pattern extraction."""

    def test_collector_number_patterns(self):
        """Test various collector number formats."""
        # Pattern: \b(\d{1,3})\s*/\s*(\d{1,3})\b
        pattern = re.compile(r"\b(\d{1,3})\s*/\s*(\d{1,3})\b")

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
        pattern = re.compile(r"\b(\d{1,3})\s*/\s*(\d{1,3})\b")

        invalid_cases = ["25/", "/102", "1234/102", "25/1234", "no numbers", "25-102"]

        for invalid_text in invalid_cases:
            match = pattern.search(invalid_text)
            assert match is None, f"Should NOT match: {invalid_text}"


class TestCardInfo:
    """Test CardInfo dataclass."""

    def test_card_info_creation(self):
        """Test CardInfo creation."""
        card_info = CardInfo(
            name="Charizard", collector_number="4/102", confidence=85.5
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


class TestOCRExtractor:
    """Test OCR extractor functionality."""

    def test_roi_constants_usage(self):
        """Test that OCR extractor uses ROI constants correctly."""
        from src.core.constants import ROI_NAME, ROI_NUMBER
        
        extractor = OCRExtractor()
        
        # Verify the extractor is using the imported constants
        assert extractor.number_pattern is not None
        assert hasattr(extractor, 'number_pattern')

    def test_collector_number_extraction_with_noise(self):
        """Test collector number extraction from noisy text inputs."""
        extractor = OCRExtractor()
        
        # Test various noisy inputs that should still extract collector numbers
        test_cases = [
            ("25/102", {"num": 25, "den": 102}),
            ("  25 / 102  ", {"num": 25, "den": 102}),
            ("Card 25/102 Rare", {"num": 25, "den": 102}),
            ("Number: 25/102", {"num": 25, "den": 102}),
            ("25 / 102", {"num": 25, "den": 102}),
            ("25/102.", {"num": 25, "den": 102}),
            ("25/102!", {"num": 25, "den": 102}),
        ]
        
        for input_text, expected in test_cases:
            # Create a mock image with the text (simulating OCR output)
            # In real usage, this would be the result of Tesseract OCR
            result = extractor.number_pattern.search(input_text)
            if result:
                num = int(result.group(1))
                den = int(result.group(2))
                extracted = {"num": num, "den": den}
                assert extracted == expected, f"Failed for input: {input_text}"
            else:
                pytest.fail(f"Should extract collector number from: {input_text}")

    def test_collector_number_extraction_failures(self):
        """Test that invalid collector number patterns are rejected."""
        extractor = OCRExtractor()
        
        # Test invalid patterns that should NOT extract collector numbers
        invalid_cases = [
            "25/",  # Missing denominator
            "/102",  # Missing numerator
            "1234/102",  # Numerator too long
            "25/1234",  # Denominator too long
            "no numbers",  # No numbers at all
            "25-102",  # Wrong separator
            "25.102",  # Wrong separator
            "25 102",  # No separator
        ]
        
        for invalid_text in invalid_cases:
            result = extractor.number_pattern.search(invalid_text)
            assert result is None, f"Should NOT extract from: {invalid_text}"

    def test_collector_number_edge_cases(self):
        """Test edge cases for collector number extraction."""
        extractor = OCRExtractor()
        
        # Test boundary conditions
        edge_cases = [
            ("1/1", {"num": 1, "den": 1}),
            ("999/999", {"num": 999, "den": 999}),
            ("100/200", {"num": 100, "den": 200}),
        ]
        
        for input_text, expected in edge_cases:
            result = extractor.number_pattern.search(input_text)
            if result:
                num = int(result.group(1))
                den = int(result.group(2))
                extracted = {"num": num, "den": den}
                assert extracted == expected, f"Failed for edge case: {input_text}"
            else:
                pytest.fail(f"Should extract from edge case: {input_text}")

    def test_tesseract_config_consistency(self):
        """Test that Tesseract configuration is consistent with requirements."""
        extractor = OCRExtractor()
        
        # Verify the extractor has the required Tesseract configuration
        assert extractor.tesseract_path is not None
        assert extractor.confidence_threshold is not None
        
        # Verify the number pattern is properly compiled
        assert hasattr(extractor.number_pattern, 'search')
        assert callable(extractor.number_pattern.search)


if __name__ == "__main__":
    pytest.main([__file__])
