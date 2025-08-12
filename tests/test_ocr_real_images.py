"""Tests for OCR functionality using real image files."""

import pytest
from pathlib import Path
import cv2
import numpy as np

from src.ocr.extract import ocr_extractor, CardInfo


class TestOCRWithRealImages:
    """Test OCR functionality using real Pokemon card images."""

    @pytest.fixture(scope="class")
    def fixture_images(self):
        """Load test images from fixtures directory."""
        fixtures_dir = Path(__file__).parent / "fixtures"
        images = {}
        
        # Load all JPG files from fixtures
        for jpg_file in fixtures_dir.glob("*.jpg"):
            image_path = str(jpg_file)
            image = cv2.imread(image_path)
            if image is not None:
                images[jpg_file.stem] = image
            else:
                pytest.fail(f"Failed to load image: {jpg_file}")
        
        return images

    def test_ocr_extractor_initialization(self):
        """Test that OCR extractor initializes correctly."""
        assert ocr_extractor is not None
        assert hasattr(ocr_extractor, 'get_name')
        assert hasattr(ocr_extractor, 'get_collector_number')
        assert hasattr(ocr_extractor, 'extract_card_info')

    def test_image_loading(self, fixture_images):
        """Test that test images can be loaded."""
        assert len(fixture_images) > 0, "No test images loaded"
        
        for name, image in fixture_images.items():
            assert image is not None, f"Image {name} is None"
            assert isinstance(image, np.ndarray), f"Image {name} is not numpy array"
            assert len(image.shape) == 3, f"Image {name} is not 3D (BGR)"
            assert image.shape[2] == 3, f"Image {name} does not have 3 color channels"

    def test_name_extraction_from_images(self, fixture_images):
        """Test name extraction from real images."""
        for name, image in fixture_images.items():
            print(f"\nTesting name extraction from {name}")
            
            # Extract name from the image
            extracted_name, confidence = ocr_extractor.get_name(image)
            
            print(f"  Extracted name: {extracted_name}")
            print(f"  Confidence: {confidence:.2f}")
            
            # Basic validation - name should be a string (even if empty)
            assert isinstance(extracted_name, (str, type(None)))
            assert isinstance(confidence, (int, float))
            assert 0.0 <= confidence <= 100.0

    def test_collector_number_extraction_from_images(self, fixture_images):
        """Test collector number extraction from real images."""
        for name, image in fixture_images.items():
            print(f"\nTesting collector number extraction from {name}")
            
            # Extract collector number from the image
            collector_number = ocr_extractor.get_collector_number(image)
            
            print(f"  Extracted number: {collector_number}")
            
            # Basic validation - should be either a dict or None
            if collector_number is not None:
                assert isinstance(collector_number, dict)
                assert 'num' in collector_number
                assert 'den' in collector_number
                assert isinstance(collector_number['num'], int)
                assert isinstance(collector_number['den'], int)
                print(f"  Number: {collector_number['num']}/{collector_number['den']}")
            else:
                print(f"  No collector number found")

    def test_full_card_extraction_from_images(self, fixture_images):
        """Test full card information extraction from real images."""
        for name, image in fixture_images.items():
            print(f"\nTesting full card extraction from {name}")
            
            # Extract full card info
            card_info = ocr_extractor.extract_card_info(image)
            
            print(f"  Card name: {card_info.name}")
            print(f"  Collector number: {card_info.collector_number}")
            print(f"  Overall confidence: {card_info.confidence:.2f}")
            
            # Validate CardInfo structure
            assert isinstance(card_info, CardInfo)
            assert isinstance(card_info.name, (str, type(None)))
            assert isinstance(card_info.collector_number, (dict, type(None)))
            assert isinstance(card_info.confidence, (int, float))
            assert 0.0 <= card_info.confidence <= 100.0

    def test_image_preprocessing(self, fixture_images):
        """Test that image preprocessing works correctly."""
        for name, image in fixture_images.items():
            print(f"\nTesting preprocessing for {name}")
            
            # Test name ROI preprocessing
            height, width = image.shape[:2]
            y1, y2 = int(height * 0.05), int(height * 0.14)
            x1, x2 = int(width * 0.08), int(width * 0.92)
            name_roi = image[y1:y2, x1:x2]
            
            # Test the preprocessing method directly
            preprocessed = ocr_extractor._preprocess_name_roi(name_roi)
            
            assert preprocessed is not None
            assert isinstance(preprocessed, np.ndarray)
            assert len(preprocessed.shape) == 2  # Should be grayscale after preprocessing

    def test_confidence_calculation(self, fixture_images):
        """Test confidence calculation from real images."""
        for name, image in fixture_images.items():
            print(f"\nTesting confidence calculation for {name}")
            
            # Extract name and calculate confidence
            extracted_name, confidence = ocr_extractor.get_name(image)
            
            if extracted_name and extracted_name.strip():  # Only check non-empty text
                # Test that confidence calculation is reasonable
                assert confidence > 0.0, f"Confidence should be > 0 for text: '{extracted_name}'"
                assert confidence <= 100.0, f"Confidence should be <= 100, got: {confidence}"
                
                print(f"  Text: '{extracted_name}' -> Confidence: {confidence:.2f}")
            else:
                print(f"  No meaningful text extracted, confidence: {confidence:.2f}")
                # For empty text, confidence can be 0
                assert confidence >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
