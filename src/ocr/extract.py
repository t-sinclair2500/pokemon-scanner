"""OCR extraction for Pokemon card text."""

import cv2
import numpy as np
import pytesseract
import re
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from pathlib import Path

from ..utils.log import LoggerMixin
from ..utils.config import settings, ensure_tesseract


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
    collector_number: Optional[str] = None
    confidence: float = 0.0
    ocr_result: Optional[OCRResult] = None


class OCRExtractor(LoggerMixin):
    """Extracts text from Pokemon card regions using OCR."""
    
    def __init__(self):
        self.tesseract_path = ensure_tesseract()
        pytesseract.pytesseract.tesseract_cmd = self.tesseract_path
        self.confidence_threshold = settings.OCR_CONFIDENCE_THRESHOLD
        
        # Collector number regex pattern
        self.number_pattern = re.compile(r'\b\d{1,3}\s*/\s*\d{1,3}\b')
        
        self.logger.info("OCR extractor initialized", 
                        tesseract_path=self.tesseract_path,
                        confidence_threshold=self.confidence_threshold)
    
    def extract_card_info(self, card_image: np.ndarray) -> CardInfo:
        """Extract card name and collector number from image."""
        try:
            self.logger.info("Starting OCR extraction", 
                           image_size=f"{card_image.shape[1]}x{card_image.shape[0]}")
            
            # Extract name from top band
            name_result = self._extract_name(card_image)
            
            # Extract collector number from bottom band
            number_result = self._extract_collector_number(card_image)
            
            # Calculate overall confidence
            confidence = self._calculate_confidence(name_result, number_result)
            
            # Create OCR result
            ocr_result = OCRResult(
                name=name_result.get('text'),
                collector_number=number_result.get('text'),
                confidence=confidence,
                raw_text={
                    'name': name_result.get('text', ''),
                    'collector_number': number_result.get('text', '')
                },
                preprocessing_steps={
                    'name': name_result.get('preprocessing', {}),
                    'collector_number': number_result.get('preprocessing', {})
                }
            )
            
            # Create card info
            card_info = CardInfo(
                name=name_result.get('text'),
                collector_number=number_result.get('text'),
                confidence=confidence,
                ocr_result=ocr_result
            )
            
            self.logger.info("OCR extraction completed",
                           name=card_info.name,
                           collector_number=card_info.collector_number,
                           confidence=confidence)
            
            return card_info
            
        except Exception as e:
            self.logger.error("OCR extraction failed", error=str(e))
            return CardInfo()
    
    def _extract_name(self, card_image: np.ndarray) -> Dict[str, Any]:
        """Extract card name from top band (5-14% height, 8-92% width)."""
        try:
            height, width = card_image.shape[:2]
            
            # Define ROI for name
            y1, y2 = int(height * 0.05), int(height * 0.14)
            x1, x2 = int(width * 0.08), int(width * 0.92)
            
            # Extract ROI
            name_roi = card_image[y1:y2, x1:x2]
            
            # Preprocess for better OCR
            preprocessed = self._preprocess_for_name(name_roi)
            
            # OCR with specific settings for name
            text = pytesseract.image_to_string(
                preprocessed,
                config='--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
            )
            
            # Clean text
            cleaned_text = self._clean_name_text(text)
            
            # Validate name
            if self._validate_name(cleaned_text):
                return {
                    'text': cleaned_text,
                    'preprocessing': {'method': 'name_optimized', 'roi': f"{x1},{y1},{x2},{y2}"}
                }
            else:
                return {'text': None, 'preprocessing': {'method': 'name_optimized', 'roi': f"{x1},{y1},{x2},{y2}"}}
                
        except Exception as e:
            self.logger.error("Name extraction failed", error=str(e))
            return {'text': None, 'preprocessing': {'error': str(e)}}
    
    def _extract_collector_number(self, card_image: np.ndarray) -> Dict[str, Any]:
        """Extract collector number from bottom band (88-98% height, 5-95% width)."""
        try:
            height, width = card_image.shape[:2]
            
            # Define ROI for collector number
            y1, y2 = int(height * 0.88), int(height * 0.98)
            x1, x2 = int(width * 0.05), int(width * 0.95)
            
            # Extract ROI
            number_roi = card_image[y1:y2, x1:x2]
            
            # Preprocess for better OCR
            preprocessed = self._preprocess_for_number(number_roi)
            
            # OCR with specific settings for numbers
            text = pytesseract.image_to_string(
                preprocessed,
                config='--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789/'
            )
            
            # Extract collector number using regex
            match = self.number_pattern.search(text)
            if match:
                return {
                    'text': match.group(),
                    'preprocessing': {'method': 'number_optimized', 'roi': f"{x1},{y1},{x2},{y2}"}
                }
            else:
                return {'text': None, 'preprocessing': {'method': 'number_optimized', 'roi': f"{x1},{y1},{x2},{y2}"}}
                
        except Exception as e:
            self.logger.error("Collector number extraction failed", error=str(e))
            return {'text': None, 'preprocessing': {'error': str(e)}}
    
    def _preprocess_for_name(self, roi: np.ndarray) -> np.ndarray:
        """Preprocess ROI for name extraction."""
        try:
            # Convert to grayscale
            if len(roi.shape) == 3:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                gray = roi
            
            # Apply bilateral filter to reduce noise while preserving edges
            filtered = cv2.bilateralFilter(gray, 9, 75, 75)
            
            # Apply adaptive threshold for better text contrast
            thresh = cv2.adaptiveThreshold(
                filtered, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            # Morphological operations to clean up text
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            cleaned = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            return cleaned
            
        except Exception as e:
            self.logger.error("Name preprocessing failed", error=str(e))
            return roi
    
    def _preprocess_for_number(self, roi: np.ndarray) -> np.ndarray:
        """Preprocess ROI for collector number extraction."""
        try:
            # Convert to grayscale
            if len(roi.shape) == 3:
                gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            else:
                gray = roi
            
            # Apply median blur to reduce noise
            blurred = cv2.medianBlur(gray, 3)
            
            # Apply Otsu's thresholding
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Invert (white text on black background)
            inverted = cv2.bitwise_not(thresh)
            
            return inverted
            
        except Exception as e:
            self.logger.error("Number preprocessing failed", error=str(e))
            return roi
    
    def _clean_name_text(self, text: str) -> str:
        """Clean and validate extracted name text."""
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        cleaned = ' '.join(text.strip().split())
        
        # Remove non-alphanumeric characters (keep spaces)
        cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', cleaned)
        
        # Ensure reasonable length
        if len(cleaned) < 2 or len(cleaned) > 50:
            return ""
        
        return cleaned
    
    def _validate_name(self, name: str) -> bool:
        """Validate extracted name."""
        if not name:
            return False
        
        # Check length
        if len(name) < 2 or len(name) > 50:
            return False
        
        # Check if it contains at least some letters
        if not re.search(r'[a-zA-Z]', name):
            return False
        
        return True
    
    def _calculate_confidence(self, name_result: Dict, number_result: Dict) -> float:
        """Calculate overall confidence score."""
        confidence = 0.0
        total_weight = 0.0
        
        # Name confidence (weight: 0.6)
        if name_result.get('text'):
            confidence += 0.6
            total_weight += 0.6
        
        # Collector number confidence (weight: 0.4)
        if number_result.get('text'):
            confidence += 0.4
            total_weight += 0.4
        
        # Normalize confidence
        if total_weight > 0:
            confidence = (confidence / total_weight) * 100
        
        return confidence


# Global singleton
ocr_extractor = OCRExtractor()