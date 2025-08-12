"""OCR package for text extraction from Pokemon cards."""

from .extract import CardInfo, OCRResult, ocr_extractor
from .regexes import (
    COLLECTOR_NUMBER_PATTERN,
    is_valid_collector_number,
    parse_collector_number,
)

__all__ = [
    "OCRResult",
    "CardInfo",
    "ocr_extractor",
    "parse_collector_number",
    "is_valid_collector_number",
    "COLLECTOR_NUMBER_PATTERN",
]
