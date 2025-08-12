"""UI overlay for camera feed with ROI boxes and status information."""

from enum import Enum
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from ..utils import LoggerMixin, get_logger
from .warp import CardContour


class OverlayColor(Enum):
    """Colors for different overlay elements."""

    CARD_DETECTED = (0, 255, 0)  # Green
    CARD_SCANNING = (0, 255, 255)  # Yellow
    CARD_ERROR = (0, 0, 255)  # Red
    ROI_BOX = (255, 255, 255)  # White
    TEXT_BG = (0, 0, 0)  # Black
    TEXT_FG = (255, 255, 255)  # White
    PROCESSING = (255, 165, 0)  # Orange


class CameraOverlay(LoggerMixin):
    """Handles camera feed overlay with detection status and ROI indicators."""

    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.7
        self.font_thickness = 2
        self.line_thickness = 2

    def draw_card_contour(
        self, frame: np.ndarray, card: CardContour, status: str = "detected"
    ) -> np.ndarray:
        """Draw card contour with status indicator."""
        overlay_frame = frame.copy()

        # Choose color based on status
        if status == "detected":
            color = OverlayColor.CARD_DETECTED.value
        elif status == "scanning":
            color = OverlayColor.CARD_SCANNING.value
        elif status == "processing":
            color = OverlayColor.PROCESSING.value
        else:
            color = OverlayColor.CARD_ERROR.value

        # Draw contour
        cv2.drawContours(overlay_frame, [card.contour], -1, color, self.line_thickness)

        # Draw corner points
        for corner in card.corners:
            cv2.circle(overlay_frame, tuple(corner.astype(int)), 8, color, -1)

        # Draw confidence score near the card
        if len(card.corners) > 0:
            text_pos = tuple(card.corners[0].astype(int))
            confidence_text = f"Conf: {card.confidence:.2f}"
            self._draw_text_with_background(
                overlay_frame, confidence_text, text_pos, color
            )

        return overlay_frame

    def draw_ocr_roi_rectangles(
        self, frame: np.ndarray, status: str = "detected"
    ) -> np.ndarray:
        """Draw the two specific ROI rectangles for OCR as specified in requirements."""
        overlay_frame = frame.copy()
        height, width = frame.shape[:2]

        # Choose color based on status
        if status == "detected":
            color = OverlayColor.CARD_DETECTED.value
        elif status == "scanning":
            color = OverlayColor.CARD_SCANNING.value
        elif status == "processing":
            color = OverlayColor.PROCESSING.value
        else:
            color = OverlayColor.CARD_ERROR.value

        # TOP name band: y 5-14% height, x 8-92%
        top_y_start = int(height * 0.05)
        top_y_end = int(height * 0.14)
        top_x_start = int(width * 0.08)
        top_x_end = int(width * 0.92)

        # BOTTOM collector band: y 88-98% height, x 5-95%
        bottom_y_start = int(height * 0.88)
        bottom_y_end = int(height * 0.98)
        bottom_x_start = int(width * 0.05)
        bottom_x_end = int(width * 0.95)

        # Draw translucent rectangles
        overlay = overlay_frame.copy()

        # Top ROI (name band)
        cv2.rectangle(
            overlay,
            (top_x_start, top_y_start),
            (top_x_end, top_y_end),
            color,
            -1,  # Filled rectangle
        )

        # Bottom ROI (collector band)
        cv2.rectangle(
            overlay,
            (bottom_x_start, bottom_y_start),
            (bottom_x_end, bottom_y_end),
            color,
            -1,  # Filled rectangle
        )

        # Apply transparency (30% overlay, 70% original)
        cv2.addWeighted(overlay_frame, 0.7, overlay, 0.3, 0, overlay_frame)

        # Draw borders for clarity
        cv2.rectangle(
            overlay_frame,
            (top_x_start, top_y_start),
            (top_x_end, top_y_end),
            color,
            2,  # Border thickness
        )

        cv2.rectangle(
            overlay_frame,
            (bottom_x_start, bottom_y_start),
            (bottom_x_end, bottom_y_end),
            color,
            2,  # Border thickness
        )

        # Add labels
        cv2.putText(
            overlay_frame,
            "NAME",
            (top_x_start + 5, top_y_start - 5),
            self.font,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )

        cv2.putText(
            overlay_frame,
            "COLLECTOR",
            (bottom_x_start + 5, bottom_y_start - 5),
            self.font,
            0.5,
            color,
            1,
            cv2.LINE_AA,
        )

        return overlay_frame

    def draw_roi_regions(
        self,
        frame: np.ndarray,
        corrected_card: np.ndarray,
        regions: Dict[str, np.ndarray],
    ) -> np.ndarray:
        """Draw ROI regions on the corrected card image."""
        overlay_frame = corrected_card.copy()
        height, width = overlay_frame.shape[:2]

        # Region definitions (same as in warp.py)
        region_definitions = {
            "name": (0.05, 0.05, 0.90, 0.25),
            "hp": (0.70, 0.05, 0.25, 0.15),
            "collector": (0.60, 0.85, 0.35, 0.10),
            "set_info": (0.05, 0.85, 0.50, 0.10),
            "full_text": (0.05, 0.60, 0.90, 0.35),
        }

        for region_name, (x_pct, y_pct, w_pct, h_pct) in region_definitions.items():
            x = int(x_pct * width)
            y = int(y_pct * height)
            w = int(w_pct * width)
            h = int(h_pct * height)

            # Draw rectangle
            color = OverlayColor.ROI_BOX.value
            cv2.rectangle(overlay_frame, (x, y), (x + w, y + h), color, 1)

            # Draw label
            label_pos = (x, y - 5 if y > 20 else y + 15)
            self._draw_text_with_background(
                overlay_frame, region_name, label_pos, color, scale=0.5
            )

        return overlay_frame

    def draw_status_panel(self, frame: np.ndarray, status_info: Dict) -> np.ndarray:
        """Draw status information panel on the frame."""
        overlay_frame = frame.copy()
        panel_height = 200
        panel_width = 300

        # Position panel in top-left corner
        panel_x, panel_y = 10, 10

        # Draw semi-transparent background
        overlay = overlay_frame.copy()
        cv2.rectangle(
            overlay,
            (panel_x, panel_y),
            (panel_x + panel_width, panel_y + panel_height),
            OverlayColor.TEXT_BG.value,
            -1,
        )
        cv2.addWeighted(overlay_frame, 0.7, overlay, 0.3, 0, overlay_frame)

        # Draw border
        cv2.rectangle(
            overlay_frame,
            (panel_x, panel_y),
            (panel_x + panel_width, panel_y + panel_height),
            OverlayColor.TEXT_FG.value,
            1,
        )

        # Draw status text
        y_offset = 30
        line_height = 25

        # Title
        self._draw_text(
            overlay_frame,
            "Pokemon Scanner",
            (panel_x + 10, panel_y + y_offset),
            scale=0.6,
            thickness=2,
        )

        y_offset += line_height * 1.5

        # Status information
        for key, value in status_info.items():
            text = f"{key}: {value}"
            self._draw_text(
                overlay_frame,
                text,
                (panel_x + 10, panel_y + y_offset),
                scale=0.5,
                thickness=1,
            )
            y_offset += line_height

            if y_offset > panel_height - 20:  # Prevent overflow
                break

        return overlay_frame

    def draw_scan_progress(
        self, frame: np.ndarray, progress: float, message: str = ""
    ) -> np.ndarray:
        """Draw scanning progress indicator."""
        overlay_frame = frame.copy()
        height, width = frame.shape[:2]

        # Progress bar dimensions
        bar_width = 400
        bar_height = 20
        bar_x = (width - bar_width) // 2
        bar_y = height - 80

        # Background rectangle
        cv2.rectangle(
            overlay_frame,
            (bar_x - 2, bar_y - 2),
            (bar_x + bar_width + 2, bar_y + bar_height + 2),
            OverlayColor.TEXT_BG.value,
            -1,
        )

        # Progress bar background
        cv2.rectangle(
            overlay_frame,
            (bar_x, bar_y),
            (bar_x + bar_width, bar_y + bar_height),
            OverlayColor.TEXT_FG.value,
            1,
        )

        # Progress fill
        if progress > 0:
            fill_width = int(bar_width * min(progress, 1.0))
            color = (
                OverlayColor.PROCESSING.value
                if progress < 1.0
                else OverlayColor.CARD_DETECTED.value
            )
            cv2.rectangle(
                overlay_frame,
                (bar_x, bar_y),
                (bar_x + fill_width, bar_y + bar_height),
                color,
                -1,
            )

        # Progress text
        progress_text = f"{progress * 100:.1f}%"
        text_size = cv2.getTextSize(progress_text, self.font, 0.5, 1)[0]
        text_x = bar_x + (bar_width - text_size[0]) // 2
        text_y = bar_y + bar_height + 20

        self._draw_text_with_background(
            overlay_frame,
            progress_text,
            (text_x, text_y),
            OverlayColor.TEXT_FG.value,
            scale=0.5,
        )

        # Message text
        if message:
            msg_size = cv2.getTextSize(message, self.font, 0.6, 1)[0]
            msg_x = (width - msg_size[0]) // 2
            msg_y = bar_y - 10

            self._draw_text_with_background(
                overlay_frame,
                message,
                (msg_x, msg_y),
                OverlayColor.TEXT_FG.value,
                scale=0.6,
            )

        return overlay_frame

    def draw_card_info(self, frame: np.ndarray, card_info: Dict) -> np.ndarray:
        """Draw extracted card information on the frame."""
        overlay_frame = frame.copy()
        height, width = frame.shape[:2]

        # Panel dimensions
        panel_width = 350
        panel_height = min(300, height - 40)
        panel_x = width - panel_width - 10
        panel_y = 10

        # Draw semi-transparent background
        overlay = overlay_frame.copy()
        cv2.rectangle(
            overlay,
            (panel_x, panel_y),
            (panel_x + panel_width, panel_y + panel_height),
            OverlayColor.TEXT_BG.value,
            -1,
        )
        cv2.addWeighted(overlay_frame, 0.7, overlay, 0.3, 0, overlay_frame)

        # Draw border
        cv2.rectangle(
            overlay_frame,
            (panel_x, panel_y),
            (panel_x + panel_width, panel_y + panel_height),
            OverlayColor.CARD_DETECTED.value,
            2,
        )

        # Draw card information
        y_offset = 30
        line_height = 25

        # Title
        self._draw_text(
            overlay_frame,
            "Card Information",
            (panel_x + 10, panel_y + y_offset),
            scale=0.6,
            thickness=2,
            color=OverlayColor.CARD_DETECTED.value,
        )

        y_offset += line_height * 1.5

        # Card details
        info_items = [
            ("Name", card_info.get("name", "Unknown")),
            ("HP", card_info.get("hp", "N/A")),
            (
                "Number",
                f"{card_info.get('collector_number', {}).get('number', 'N/A')}/{card_info.get('collector_number', {}).get('total', 'N/A')}",
            ),
            ("Set", card_info.get("set_code", "Unknown")),
            ("Type", card_info.get("card_type", "Unknown")),
            ("Confidence", f"{card_info.get('confidence', 0):.1f}%"),
        ]

        for label, value in info_items:
            text = f"{label}: {value}"
            self._draw_text(
                overlay_frame,
                text,
                (panel_x + 10, panel_y + y_offset),
                scale=0.5,
                thickness=1,
            )
            y_offset += line_height

            if y_offset > panel_height - 20:
                break

        return overlay_frame

    def draw_instructions(self, frame: np.ndarray) -> np.ndarray:
        """Draw usage instructions on the frame."""
        overlay_frame = frame.copy()
        height, width = frame.shape[:2]

        instructions = [
            "Position Pokemon card in camera view",
            "Hold steady for automatic scanning",
            "Press 'q' to quit, 's' to save, 'c' to capture",
        ]

        # Calculate starting position
        start_y = height - (len(instructions) * 30) - 20

        for i, instruction in enumerate(instructions):
            y_pos = start_y + (i * 30)
            self._draw_text_with_background(
                overlay_frame,
                instruction,
                (20, y_pos),
                OverlayColor.TEXT_FG.value,
                scale=0.5,
            )

        return overlay_frame

    def _draw_text(
        self,
        frame: np.ndarray,
        text: str,
        position: Tuple[int, int],
        scale: float = 0.7,
        thickness: int = 2,
        color: Tuple[int, int, int] = None,
    ) -> None:
        """Draw text on frame."""
        if color is None:
            color = OverlayColor.TEXT_FG.value

        cv2.putText(
            frame, text, position, self.font, scale, color, thickness, cv2.LINE_AA
        )

    def _draw_text_with_background(
        self,
        frame: np.ndarray,
        text: str,
        position: Tuple[int, int],
        color: Tuple[int, int, int],
        scale: float = 0.7,
        thickness: int = 2,
    ) -> None:
        """Draw text with background for better visibility."""
        # Get text size
        (text_width, text_height), baseline = cv2.getTextSize(
            text, self.font, scale, thickness
        )

        # Draw background rectangle
        x, y = position
        cv2.rectangle(
            frame,
            (x - 2, y - text_height - 2),
            (x + text_width + 2, y + baseline + 2),
            OverlayColor.TEXT_BG.value,
            -1,
        )

        # Draw text
        cv2.putText(
            frame, text, position, self.font, scale, color, thickness, cv2.LINE_AA
        )


# Global overlay instance
camera_overlay = CameraOverlay()
