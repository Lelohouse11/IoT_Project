"""
Traffic light detector module for detecting red/green light states.
Uses color detection on a defined traffic light zone.
"""

import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class TrafficLightDetector:
    """
    Detects traffic light state (red, green, yellow, unknown) from video frames.
    Uses HSV color space for robust detection across different lighting conditions.
    """

    def __init__(self):
        """Initialize traffic light detector with color ranges."""
        # HSV color ranges for traffic lights
        # Red light (two ranges because red wraps around in HSV)
        self.red_lower_1 = np.array([0, 100, 100])
        self.red_upper_1 = np.array([10, 255, 255])
        self.red_lower_2 = np.array([170, 100, 100])
        self.red_upper_2 = np.array([180, 255, 255])
        
        # Green light
        self.green_lower = np.array([35, 100, 100])
        self.green_upper = np.array([85, 255, 255])
        
        # Yellow light
        self.yellow_lower = np.array([15, 100, 100])
        self.yellow_upper = np.array([35, 255, 255])
        
        self.last_light_state = "unknown"
        self.light_state_confidence = 0.0

    def detect_light_state(
        self,
        frame: np.ndarray,
        light_zone_coords: Optional[list] = None,
        img_h: int = 720,
        img_w: int = 1280,
    ) -> Dict[str, Any]:
        """
        Detect traffic light state from frame.
        
        Args:
            frame: OpenCV frame (BGR)
            light_zone_coords: Zone coordinates (normalized 0-1) as [[x1,y1], [x2,y2], ...]
            img_h: Frame height in pixels
            img_w: Frame width in pixels
            
        Returns:
            {
                "light_state": "red" | "green" | "yellow" | "unknown",
                "confidence": 0.0-1.0,
                "red_pixels": count,
                "green_pixels": count,
                "yellow_pixels": count
            }
        """
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Extract region of interest if zone provided
        roi = hsv
        if light_zone_coords and len(light_zone_coords) >= 2:
            roi = self._extract_roi(hsv, light_zone_coords, img_h, img_w)
        
        # Count colored pixels
        red_mask_1 = cv2.inRange(roi, self.red_lower_1, self.red_upper_1)
        red_mask_2 = cv2.inRange(roi, self.red_lower_2, self.red_upper_2)
        red_mask = cv2.bitwise_or(red_mask_1, red_mask_2)
        red_pixels = cv2.countNonZero(red_mask)
        
        green_mask = cv2.inRange(roi, self.green_lower, self.green_upper)
        green_pixels = cv2.countNonZero(green_mask)
        
        yellow_mask = cv2.inRange(roi, self.yellow_lower, self.yellow_upper)
        yellow_pixels = cv2.countNonZero(yellow_mask)
        
        # Determine light state
        total_pixels = red_pixels + green_pixels + yellow_pixels
        
        if total_pixels == 0:
            light_state = "unknown"
            confidence = 0.0
        else:
            # Determine which color has the most pixels
            max_pixels = max(red_pixels, green_pixels, yellow_pixels)
            
            if max_pixels == red_pixels:
                light_state = "red"
                confidence = red_pixels / total_pixels
            elif max_pixels == green_pixels:
                light_state = "green"
                confidence = green_pixels / total_pixels
            else:
                light_state = "yellow"
                confidence = yellow_pixels / total_pixels
        
        self.last_light_state = light_state
        self.light_state_confidence = confidence
        
        return {
            "light_state": light_state,
            "confidence": confidence,
            "red_pixels": int(red_pixels),
            "green_pixels": int(green_pixels),
            "yellow_pixels": int(yellow_pixels),
        }

    def _extract_roi(
        self,
        image: np.ndarray,
        coords: list,
        img_h: int,
        img_w: int,
    ) -> np.ndarray:
        """
        Extract region of interest from image using normalized coordinates.
        
        Args:
            image: Input image
            coords: Normalized coordinates [[x1, y1], [x2, y2], ...]
            img_h: Image height
            img_w: Image width
            
        Returns:
            Cropped region of interest
        """
        try:
            # Convert normalized to pixel coordinates
            poly_points = np.array(
                [[int(x * img_w), int(y * img_h)] for x, y in coords],
                dtype=np.int32
            )
            
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(poly_points)
            
            # Ensure bounds are within image
            x = max(0, x)
            y = max(0, y)
            w = min(w, img_w - x)
            h = min(h, img_h - y)
            
            if w > 0 and h > 0:
                return image[y:y+h, x:x+w]
            else:
                return image
        except Exception as e:
            logger.warning(f"Failed to extract ROI: {e}")
            return image

    def is_light_red(self) -> bool:
        """Check if last detected light state is red."""
        return self.last_light_state == "red"

    def is_light_green(self) -> bool:
        """Check if last detected light state is green."""
        return self.last_light_state == "green"

    def get_light_state(self) -> str:
        """Get the last detected light state."""
        return self.last_light_state
