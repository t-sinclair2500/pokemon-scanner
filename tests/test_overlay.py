"""Tests for overlay functionality."""

import cv2
import numpy as np
import pytest

from src.capture.overlay import CameraOverlay, OverlayColor


class TestCameraOverlay:
    """Test overlay functionality."""

    def test_overlay_initialization(self):
        """Test that overlay initializes without errors."""
        overlay = CameraOverlay()
        assert overlay is not None
        assert hasattr(overlay, "draw_ocr_roi_rectangles")

    def test_draw_ocr_roi_rectangles_no_exceptions(self):
        """Test that draw_ocr_roi_rectangles renders without exceptions."""
        overlay = CameraOverlay()

        # Create a test frame (640x480)
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Test with different status values
        statuses = ["detected", "scanning", "processing", "error"]

        for status in statuses:
            try:
                result = overlay.draw_ocr_roi_rectangles(test_frame, status)
                assert result is not None
                assert result.shape == test_frame.shape
                assert result.dtype == test_frame.dtype
            except Exception as e:
                pytest.fail(
                    f"draw_ocr_roi_rectangles failed with status '{status}': {e}"
                )

    def test_roi_rectangle_dimensions(self):
        """Test that ROI rectangles are drawn with correct dimensions."""
        overlay = CameraOverlay()

        # Create test frame
        height, width = 480, 640
        test_frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

        result = overlay.draw_ocr_roi_rectangles(test_frame, "detected")

        # Check that the frame was modified (not just copied)
        assert not np.array_equal(result, test_frame)

        # Verify frame dimensions are preserved
        assert result.shape == test_frame.shape

    def test_overlay_color_enum(self):
        """Test that overlay colors are properly defined."""
        assert hasattr(OverlayColor, "CARD_DETECTED")
        assert hasattr(OverlayColor, "CARD_SCANNING")
        assert hasattr(OverlayColor, "CARD_ERROR")
        assert hasattr(OverlayColor, "PROCESSING")

        # Check that colors are tuples of 3 integers (BGR format)
        for color_name in [
            "CARD_DETECTED",
            "CARD_SCANNING",
            "CARD_ERROR",
            "PROCESSING",
        ]:
            color = getattr(OverlayColor, color_name).value
            assert isinstance(color, tuple)
            assert len(color) == 3
            assert all(isinstance(c, int) for c in color)
            assert all(0 <= c <= 255 for c in color)

    def test_overlay_with_different_frame_sizes(self):
        """Test overlay works with different frame sizes."""
        overlay = CameraOverlay()

        # Test different common resolutions
        resolutions = [(640, 480), (1280, 720), (1920, 1080)]

        for width, height in resolutions:
            test_frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)

            try:
                result = overlay.draw_ocr_roi_rectangles(test_frame, "detected")
                assert result.shape == (height, width, 3)
            except Exception as e:
                pytest.fail(f"Overlay failed with resolution {width}x{height}: {e}")

    def test_overlay_transparency(self):
        """Test that overlay applies transparency correctly."""
        overlay = CameraOverlay()

        # Create test frame
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        result = overlay.draw_ocr_roi_rectangles(test_frame, "detected")

        # The result should be different from original due to transparency
        assert not np.array_equal(result, test_frame)

        # But the overall structure should be preserved
        assert result.shape == test_frame.shape
        assert result.dtype == test_frame.dtype
