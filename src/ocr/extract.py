"""OCR extraction for Pokemon card text."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np
import pytesseract

from ..core.constants import ROI_NAME, ROI_NUMBER
from ..utils.config import ensure_tesseract, settings
from ..utils.log import LoggerMixin
from .regexes import COLLECTOR_NUMBER_PATTERN


@dataclass
class OCRResult:
    """OCR extraction result."""

    name: Optional[str] = None
    collector_number: Optional[str] = None
    confidence: float = 0.0
    raw_text: Dict[str, str] = None
    preprocessing_steps: Dict[str, Any] = None

    def __post_init__(self):
        if self.raw_text is None:
            self.raw_text = {}
        if self.preprocessing_steps is None:
            self.preprocessing_steps = {}


@dataclass
class CardInfo:
    """Extracted card information."""

    name: Optional[str] = None
    collector_number: Optional[Dict[str, int]] = None
    confidence: float = 0.0
    ocr_result: Optional[OCRResult] = None


class OCRExtractor(LoggerMixin):
    """Extracts text from Pokemon card regions using OCR."""

    def __init__(self):
        self.tesseract_path = ensure_tesseract()
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        self.confidence_threshold = settings.OCR_CONFIDENCE_THRESHOLD

        # Use imported regex pattern for consistency
        self.number_pattern = COLLECTOR_NUMBER_PATTERN

        self.logger.info(
            "OCR extractor initialized",
            tesseract_path=self.tesseract_path,
            confidence_threshold=self.confidence_threshold,
        )

    def get_name(self, warped_image: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Extract card name from TOP ROI (y 5-14% height, x 8-92% width).

        Returns:
            Tuple of (extracted_text, confidence_score)
        """
        try:
            height, width = warped_image.shape[:2]

            # Define ROI for name: TOP (y 5-14% height, x 8-92% width)
            y1, y2 = int(height * ROI_NAME[0]), int(height * ROI_NAME[1])
            x1, x2 = int(width * ROI_NAME[2]), int(width * ROI_NAME[3])

            # Extract ROI
            name_roi = warped_image[y1:y2, x1:x2]

            # Apply light denoising
            preprocessed = self._preprocess_name_roi(name_roi)

            # Use Tesseract with '--psm 7' (single line)
            text = pytesseract.image_to_string(preprocessed, config="--psm 7")

            # Strip artifacts and clean text
            cleaned_text = self._clean_name_text(text)

            # Calculate confidence as ratio of A-Z/a-z characters
            confidence = self._calculate_name_confidence(cleaned_text)

            self.logger.debug(
                "Name extraction completed",
                text=cleaned_text,
                confidence=confidence,
                roi=f"y:{y1}-{y2}, x:{x1}-{x2}",
            )

            return cleaned_text, confidence

        except Exception as e:
            self.logger.error("Name extraction failed", error=str(e))
            return None, 0.0

    def get_collector_number(
        self, warped_image: np.ndarray
    ) -> Optional[Dict[str, int]]:
        """
        Extract collector number from BOTTOM ROI (y 88-98% height, x 5-95% width).

        Returns:
            Dict with 'num' and 'den' keys, or None if extraction fails
        """
        try:
            height, width = warped_image.shape[:2]

            # Define ROI for collector number: BOTTOM (y 88-98% height, x 5-95% width)
            y1, y2 = int(height * ROI_NUMBER[0]), int(height * ROI_NUMBER[1])
            x1, x2 = int(width * ROI_NUMBER[2]), int(width * ROI_NUMBER[3])

            # Extract ROI
            number_roi = warped_image[y1:y2, x1:x2]

            # Convert to grayscale and apply adaptive threshold
            preprocessed = self._preprocess_number_roi(number_roi)

            # Use Tesseract '--psm 7' with whitelist '0123456789/'
            text = pytesseract.image_to_string(
                preprocessed, config="--psm 7 -c tessedit_char_whitelist=0123456789/"
            )

            # Apply regex to extract collector number
            match = self.number_pattern.search(text)
            if match:
                num = int(match.group(1))
                den = int(match.group(2))

                self.logger.debug(
                    "Collector number extraction completed",
                    number=f"{num}/{den}",
                    roi=f"y:{y1}-{y2}, x:{x1}-{x2}",
                )

                return {"num": num, "den": den}
            else:
                self.logger.debug(
                    "No collector number pattern found",
                    extracted_text=text,
                    roi=f"y:{y1}-{y2}, x:{x1}-{x2}",
                )
                return None

        except Exception as e:
            self.logger.error("Collector number extraction failed", error=str(e))
            return None

    def extract_card_info(self, warped_image: np.ndarray) -> CardInfo:
        """
        Extract card information from warped image.

        Returns:
            CardInfo dataclass with name, collector_number, and confidence
        """
        try:
            self.logger.info(
                "Starting OCR extraction",
                image_size=f"{warped_image.shape[1]}x{warped_image.shape[0]}",
            )

            # Extract name from top band
            name_text, name_confidence = self.get_name(warped_image)

            # Extract collector number from bottom band
            collector_number = self.get_collector_number(warped_image)

            # Calculate overall confidence
            confidence = self._calculate_overall_confidence(
                name_text, name_confidence, collector_number
            )

            # Create OCR result
            ocr_result = OCRResult(
                name=name_text,
                collector_number=(
                    f"{collector_number['num']}/{collector_number['den']}"
                    if collector_number
                    else None
                ),
                confidence=confidence,
                raw_text={
                    "name": name_text or "",
                    "collector_number": (
                        f"{collector_number['num']}/{collector_number['den']}"
                        if collector_number
                        else ""
                    ),
                },
                preprocessing_steps={
                    "name": {"confidence": name_confidence},
                    "collector_number": {"extracted": collector_number is not None},
                },
            )

            # Create card info
            card_info = CardInfo(
                name=name_text,
                collector_number=collector_number,
                confidence=confidence,
                ocr_result=ocr_result,
            )

            self.logger.info(
                "OCR extraction completed",
                name=card_info.name,
                collector_number=(
                    f"{collector_number['num']}/{collector_number['den']}"
                    if collector_number
                    else None
                ),
                confidence=confidence,
            )

            return card_info

        except Exception as e:
            self.logger.error("OCR extraction failed", error=str(e))
            return CardInfo()

    def _preprocess_name_roi(self, roi: np.ndarray) -> np.ndarray:
        """Preprocess ROI for name extraction with light denoising."""
        try:
            # Convert to grayscale
            if len(roi.shape) == 3:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                gray = roi

            # Apply light denoising with bilateral filter
            filtered = cv2.bilateralFilter(gray, 9, 75, 75)

            # Apply adaptive threshold for better text contrast
            thresh = cv2.adaptiveThreshold(
                filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            return thresh

        except Exception as e:
            self.logger.error("Name ROI preprocessing failed", error=str(e))
            return roi

    def _preprocess_number_roi(self, roi: np.ndarray) -> np.ndarray:
        """Preprocess ROI for collector number extraction."""
        try:
            # Convert to grayscale
            if len(roi.shape) == 3:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                gray = roi

            # Apply adaptive threshold
            thresh = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )

            return thresh

        except Exception as e:
            self.logger.error("Number ROI preprocessing failed", error=str(e))
            return roi

    def _clean_name_text(self, text: str) -> str:
        """Clean and validate extracted name text."""
        if not text:
            return ""

        # Remove extra whitespace and newlines
        cleaned = " ".join(text.strip().split())

        # Remove non-alphanumeric characters (keep spaces)
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", "", cleaned)

        # Ensure reasonable length
        if len(cleaned) < 2 or len(cleaned) > 50:
            return ""

        return cleaned

    def _calculate_name_confidence(self, text: str) -> float:
        """
        Calculate confidence as ratio of A-Z/a-z characters in result.

        Returns:
            Confidence score from 0.0 to 1.0
        """
        if not text:
            return 0.0

        # Count alphabetic characters
        alpha_chars = sum(1 for c in text if c.isalpha())
        total_chars = len(text)

        if total_chars == 0:
            return 0.0

        confidence = alpha_chars / total_chars
        return confidence

    def _calculate_overall_confidence(
        self,
        name_text: Optional[str],
        name_confidence: float,
        collector_number: Optional[Dict[str, int]],
    ) -> float:
        """Calculate overall confidence score."""
        confidence = 0.0
        total_weight = 0.0

        # Name confidence (weight: 0.6)
        if name_text:
            confidence += name_confidence * 0.6
            total_weight += 0.6

        # Collector number confidence (weight: 0.4)
        if collector_number:
            confidence += 0.4
            total_weight += 0.4

        # Normalize confidence
        if total_weight > 0:
            confidence = (confidence / total_weight) * 100

        return confidence


# Global singleton
ocr_extractor = OCRExtractor()
