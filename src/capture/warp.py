"""Card detection and perspective correction."""

from dataclasses import dataclass
from typing import Optional, Tuple, List

import cv2
import numpy as np

from ..utils.log import get_logger


@dataclass
class CardContour:
    """Detected card contour with confidence."""

    contour: np.ndarray
    confidence: float
    corners: np.ndarray


class CardDetector:
    """Detects Pokemon cards in camera frames."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.min_area = 10000
        self.target_aspect_ratio = 2.5 / 3.5  # Standard card ratio

    def get_best_card(self, frame: np.ndarray) -> Optional[CardContour]:
        """Find the best card contour in frame - largest quadrilateral."""
        try:
            # Convert to grayscale and detect edges
            edges = self._detect_edges(frame)

            # Find contours
            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            # Find the best card contour
            best_contour, best_corners = self._find_best_contour(contours)

            if best_contour is not None and best_corners is not None:
                confidence = min(cv2.contourArea(best_contour) / 100000, 1.0)
                return CardContour(
                    contour=best_contour, confidence=confidence, corners=best_corners
                )

            return None

        except Exception as e:
            self.logger.error("Error detecting card", error=str(e))
            return None

    def _detect_edges(self, frame: np.ndarray) -> np.ndarray:
        """Detect edges in the frame for contour detection."""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply blur and edge detection
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 50, 150)

        # Dilate to connect broken edges
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(edges, kernel, iterations=1)

        return dilated

    def _find_best_contour(self, contours: List[np.ndarray]) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Find the best contour that represents a card."""
        best_contour = None
        best_area = 0
        best_corners = None

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < self.min_area:
                continue

            corners = self._extract_corners_from_contour(contour, area)
            if corners is not None and area > best_area:
                best_area = area
                best_contour = contour
                best_corners = corners

        return best_contour, best_corners

    def _extract_corners_from_contour(self, contour: np.ndarray, area: float) -> Optional[np.ndarray]:
        """Extract corner points from a contour."""
        # Approximate to polygon
        epsilon = 0.02 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)

        # Look for quadrilateral (4 corners)
        if len(approx) == 4:
            if self._is_valid_card_shape(approx):
                return approx.reshape(4, 2).astype(np.float32)

        # If no perfect quadrilateral, try to extract from larger polygon
        if len(approx) > 4:
            return self._extract_corners_from_large_polygon(contour, area)

        return None

    def _is_valid_card_shape(self, approx: np.ndarray) -> bool:
        """Check if the approximated contour has a valid card-like shape."""
        rect = cv2.boundingRect(approx)
        w, h = rect[2], rect[3]
        aspect_ratio = min(w, h) / max(w, h)
        
        # Cards should be roughly rectangular
        return aspect_ratio > 0.6

    def _extract_corners_from_large_polygon(self, contour: np.ndarray, area: float) -> Optional[np.ndarray]:
        """Extract 4 corner points from a large polygon."""
        # Try to extract 4 corner points from larger polygon
        hull = cv2.convexHull(contour)
        epsilon = 0.05 * cv2.arcLength(hull, True)
        approx_hull = cv2.approxPolyDP(hull, epsilon, True)

        if len(approx_hull) >= 4:
            # Use first 4 points or corner points
            if len(approx_hull) == 4:
                return approx_hull.reshape(4, 2).astype(np.float32)
            elif len(approx_hull) > 4:
                # Find the 4 most distant points
                points = approx_hull.reshape(-1, 2)
                return self._find_four_corners(points)

        return None

    def _find_four_corners(self, points: np.ndarray) -> Optional[np.ndarray]:
        """Find 4 corner points from a set of points."""
        if len(points) < 4:
            return None

        # Find centroid
        centroid = np.mean(points, axis=0)

        # Find points in each quadrant
        quadrants = self._assign_points_to_quadrants(points, centroid)

        # Get the most extreme point in each quadrant
        corners = self._get_extreme_points_from_quadrants(quadrants)
        
        if corners is None:
            return None

        return np.array(corners, dtype=np.float32)

    def _assign_points_to_quadrants(self, points: np.ndarray, centroid: np.ndarray) -> List[List[np.ndarray]]:
        """Assign points to quadrants based on centroid position."""
        quadrants = [[], [], [], []]  # TL, TR, BR, BL

        for point in points:
            if point[0] < centroid[0] and point[1] < centroid[1]:
                quadrants[0].append(point)  # Top-left
            elif point[0] >= centroid[0] and point[1] < centroid[1]:
                quadrants[1].append(point)  # Top-right
            elif point[0] >= centroid[0] and point[1] >= centroid[1]:
                quadrants[2].append(point)  # Bottom-right
            else:
                quadrants[3].append(point)  # Bottom-left

        return quadrants

    def _get_extreme_points_from_quadrants(self, quadrants: List[List[np.ndarray]]) -> Optional[List[np.ndarray]]:
        """Get the most extreme point from each quadrant."""
        corners = []
        
        for i, quad_points in enumerate(quadrants):
            if not quad_points:
                return None  # Must have point in each quadrant

            corner = self._get_extreme_point_for_quadrant(i, quad_points)
            corners.append(corner)

        return corners

    def _get_extreme_point_for_quadrant(self, quadrant_index: int, quad_points: List[np.ndarray]) -> np.ndarray:
        """Get the most extreme point for a specific quadrant."""
        if quadrant_index == 0:  # Top-left: minimize distance from origin
            return min(quad_points, key=lambda p: p[0] + p[1])
        elif quadrant_index == 1:  # Top-right: minimize distance from top-right
            return max(quad_points, key=lambda p: p[0] - p[1])
        elif quadrant_index == 2:  # Bottom-right: maximize distance from origin
            return max(quad_points, key=lambda p: p[0] + p[1])
        else:  # Bottom-left: minimize x, maximize y
            return min(quad_points, key=lambda p: p[0] - p[1])


class PerspectiveCorrector:
    """Corrects perspective of detected cards."""

    def __init__(self):
        self.logger = get_logger(__name__)

    def warp_card(
        self,
        image: np.ndarray,
        card_contour: CardContour,
        out_w: int = 900,
        out_h: int = 1260,
    ) -> Optional[np.ndarray]:
        """Warp card to rectangular shape."""
        try:
            # Order corners: top-left, top-right, bottom-right, bottom-left
            corners = self._order_corners(card_contour.corners)

            # Define destination points
            dst_points = np.array(
                [[0, 0], [out_w - 1, 0], [out_w - 1, out_h - 1], [0, out_h - 1]],
                dtype=np.float32,
            )

            # Get perspective transform matrix
            matrix = cv2.getPerspectiveTransform(corners.astype(np.float32), dst_points)

            # Apply transformation
            warped = cv2.warpPerspective(image, matrix, (out_w, out_h))

            return warped

        except Exception as e:
            self.logger.error("Error warping card", error=str(e))
            return None

    def _order_corners(self, corners: np.ndarray) -> np.ndarray:
        """Order corners as top-left, top-right, bottom-right, bottom-left."""
        # Calculate centroid
        centroid = np.mean(corners, axis=0)

        # Sort by position relative to centroid
        ordered = np.zeros((4, 2), dtype=np.float32)

        for corner in corners:
            if corner[0] < centroid[0] and corner[1] < centroid[1]:
                ordered[0] = corner  # top-left
            elif corner[0] > centroid[0] and corner[1] < centroid[1]:
                ordered[1] = corner  # top-right
            elif corner[0] > centroid[0] and corner[1] > centroid[1]:
                ordered[2] = corner  # bottom-right
            else:
                ordered[3] = corner  # bottom-left

        return ordered


# Global singletons
card_detector = CardDetector()
perspective_corrector = PerspectiveCorrector()
