"""Camera capture and card detection for Pokemon Scanner."""

import cv2
import numpy as np
from typing import Optional, Tuple, List
from pathlib import Path
import time

from ..utils.log import LoggerMixin
from ..utils.config import settings


class CameraCapture(LoggerMixin):
    """Camera capture with card detection and image stabilization."""
    
    def __init__(self):
        self.cap = None
        self.camera_index = settings.CAMERA_INDEX
        self.is_initialized = False
        
    def initialize(self) -> bool:
        """Initialize camera and verify it's working."""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self.logger.error("Failed to open camera", camera_index=self.camera_index)
                return False
            
            # Set camera properties for better quality
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            
            # Test capture
            ret, frame = self.cap.read()
            if not ret:
                self.logger.error("Failed to capture test frame")
                return False
                
            self.is_initialized = True
            self.logger.info("Camera initialized successfully", 
                           camera_index=self.camera_index,
                           frame_size=f"{frame.shape[1]}x{frame.shape[0]}")
            return True
            
        except Exception as e:
            self.logger.error("Camera initialization failed", error=str(e))
            return False
    
    def capture_stable_frame(self, stabilization_frames: int = 5) -> Optional[np.ndarray]:
        """Capture a stable frame by averaging multiple frames."""
        if not self.is_initialized:
            self.logger.error("Camera not initialized")
            return None
            
        try:
            frames = []
            
            # Capture multiple frames
            for i in range(stabilization_frames):
                ret, frame = self.cap.read()
                if ret:
                    frames.append(frame)
                time.sleep(0.1)  # Small delay between captures
            
            if not frames:
                self.logger.error("No frames captured")
                return None
            
            # Average frames for stability
            if len(frames) > 1:
                stable_frame = np.mean(frames, axis=0).astype(np.uint8)
            else:
                stable_frame = frames[0]
            
            self.logger.info("Stable frame captured", 
                           frame_count=len(frames),
                           frame_size=f"{stable_frame.shape[1]}x{stable_frame.shape[0]}")
            return stable_frame
            
        except Exception as e:
            self.logger.error("Frame capture failed", error=str(e))
            return None
    
    def detect_card_region(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """Detect and extract the main card region from the frame."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Apply Gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Edge detection
            edges = cv2.Canny(blurred, 50, 150)
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return None
            
            # Find the largest contour (likely the card)
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            
            # Filter by minimum area (to avoid noise)
            min_area = frame.shape[0] * frame.shape[1] * 0.1  # 10% of frame
            if area < min_area:
                return None
            
            # Approximate contour to polygon
            epsilon = 0.02 * cv2.arcLength(largest_contour, True)
            approx = cv2.approxPolyDP(largest_contour, epsilon, True)
            
            # We want a quadrilateral (4 corners)
            if len(approx) != 4:
                return None
            
            # Extract the card region
            card_region = self._extract_card_region(frame, approx.reshape(4, 2))
            
            self.logger.info("Card region detected", 
                           contour_area=area,
                           corners=len(approx),
                           card_size=f"{card_region.shape[1]}x{card_region.shape[0]}")
            
            return card_region
            
        except Exception as e:
            self.logger.error("Card detection failed", error=str(e))
            return None
    
    def _extract_card_region(self, frame: np.ndarray, corners: np.ndarray) -> np.ndarray:
        """Extract and warp the card region to a standard size."""
        try:
            # Sort corners: top-left, top-right, bottom-right, bottom-left
            corners = self._sort_corners(corners)
            
            # Define target dimensions (standard card aspect ratio ~1.4:1)
            target_width = 900
            target_height = int(target_width * 1.4)  # ~1260
            
            # Define target corners
            target_corners = np.array([
                [0, 0],
                [target_width, 0],
                [target_width, target_height],
                [0, target_height]
            ], dtype=np.float32)
            
            # Calculate perspective transform
            transform_matrix = cv2.getPerspectiveTransform(corners.astype(np.float32), target_corners)
            
            # Apply transform
            warped = cv2.warpPerspective(frame, transform_matrix, (target_width, target_height))
            
            return warped
            
        except Exception as e:
            self.logger.error("Card region extraction failed", error=str(e))
            return frame  # Return original frame if warping fails
    
    def _sort_corners(self, corners: np.ndarray) -> np.ndarray:
        """Sort corners in order: top-left, top-right, bottom-right, bottom-left."""
        # Find center
        center = np.mean(corners, axis=0)
        
        # Sort by angle from center
        def angle_from_center(point):
            return np.arctan2(point[1] - center[1], point[0] - center[0])
        
        sorted_corners = sorted(corners, key=angle_from_center)
        
        # Ensure proper order (top-left first)
        if sorted_corners[0][1] > sorted_corners[1][1]:
            sorted_corners = sorted_corners[1:] + sorted_corners[:1]
        
        return np.array(sorted_corners)
    
    def get_preview_frame(self) -> Optional[np.ndarray]:
        """Get current preview frame for display."""
        if not self.is_initialized:
            return None
            
        ret, frame = self.cap.read()
        if ret:
            return frame
        return None
    
    def release(self):
        """Release camera resources."""
        if self.cap:
            self.cap.release()
            self.is_initialized = False
            self.logger.info("Camera released")
    
    def __enter__(self):
        """Context manager entry."""
        if self.initialize():
            return self
        raise RuntimeError("Failed to initialize camera")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


# Global singleton
camera_capture = CameraCapture()