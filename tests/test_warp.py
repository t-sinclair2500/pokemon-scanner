"""Tests for perspective correction and card detection."""

import cv2
import numpy as np
import pytest

from src.capture.warp import CardContour, CardDetector, PerspectiveCorrector


class TestPerspectiveCorrector:
    """Test perspective correction functionality."""

    def test_warp_card_output_shape(self):
        """Test that warp_card returns correct output shape (900x1260)."""
        corrector = PerspectiveCorrector()

        # Create synthetic test image (640x480)
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Create a card contour with 4 corners (a rectangle)
        corners = np.array(
            [
                [100, 100],  # top-left
                [300, 100],  # top-right
                [300, 400],  # bottom-right
                [100, 400],  # bottom-left
            ],
            dtype=np.float32,
        )

        # Create dummy contour
        contour = np.array([[100, 100], [300, 100], [300, 400], [100, 400]])

        card_contour = CardContour(contour=contour, confidence=0.8, corners=corners)

        # Test warp with default output size
        warped = corrector.warp_card(test_image, card_contour)

        assert warped is not None
        assert warped.shape == (
            1260,
            900,
            3,
        ), f"Expected (1260, 900, 3), got {warped.shape}"

    def test_warp_card_custom_size(self):
        """Test warp_card with custom output size."""
        corrector = PerspectiveCorrector()

        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        corners = np.array(
            [[50, 50], [250, 50], [250, 350], [50, 350]], dtype=np.float32
        )

        contour = np.array([[50, 50], [250, 50], [250, 350], [50, 350]])

        card_contour = CardContour(contour=contour, confidence=0.9, corners=corners)

        # Test with custom size
        warped = corrector.warp_card(test_image, card_contour, out_w=300, out_h=400)

        assert warped is not None
        assert warped.shape == (400, 300, 3)

    def test_order_corners(self):
        """Test corner ordering functionality."""
        corrector = PerspectiveCorrector()

        # Create corners in random order
        random_corners = np.array(
            [
                [200, 300],  # bottom-right
                [50, 50],  # top-left
                [200, 50],  # top-right
                [50, 300],  # bottom-left
            ],
            dtype=np.float32,
        )

        ordered = corrector._order_corners(random_corners)

        # Should be ordered as: top-left, top-right, bottom-right, bottom-left
        assert ordered.shape == (4, 2)

        # Check that top-left is actually top-left (smallest x+y)
        tl = ordered[0]
        tr = ordered[1]
        br = ordered[2]
        bl = ordered[3]

        # Basic sanity checks
        assert tl[0] < tr[0]  # top-left x < top-right x
        assert tl[1] < bl[1]  # top-left y < bottom-left y
        assert tr[1] < br[1]  # top-right y < bottom-right y
        assert bl[0] < br[0]  # bottom-left x < bottom-right x


class TestCardDetector:
    """Test card detection functionality."""

    def test_synthetic_rectangle_detection(self):
        """Test detection with a synthetic rectangular card."""
        detector = CardDetector()

        # Create image with white rectangle on black background
        test_image = np.zeros((600, 800, 3), dtype=np.uint8)

        # Draw a white rectangle (simulating a card)
        cv2.rectangle(test_image, (200, 150), (600, 450), (255, 255, 255), -1)

        # Add some noise/texture
        noise = np.random.randint(200, 255, (300, 400, 3), dtype=np.uint8)
        test_image[150:450, 200:600] = noise

        result = detector.get_best_card(test_image)

        # Should detect something
        assert result is not None
        assert result.confidence > 0
        assert result.corners.shape == (4, 2)

        # Corners should be roughly in the right area
        corners = result.corners
        min_x, min_y = np.min(corners, axis=0)
        max_x, max_y = np.max(corners, axis=0)

        # Should be roughly in the rectangle area (with some tolerance)
        assert 150 <= min_x <= 250  # Around 200
        assert 100 <= min_y <= 200  # Around 150
        assert 550 <= max_x <= 650  # Around 600
        assert 400 <= max_y <= 500  # Around 450

    def test_small_area_no_detection(self):
        """Test that no card is detected when area is too small."""
        detector = CardDetector()

        # Create image with small white square (below min_area threshold)
        test_image = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.rectangle(test_image, (200, 200), (220, 220), (255, 255, 255), -1)

        result = detector.get_best_card(test_image)

        # Should not detect a card when area is too small
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__])
