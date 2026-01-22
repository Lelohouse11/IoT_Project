"""
Zone detector module for spatial filtering of detections.
Uses point-in-polygon detection to determine if vehicles are within marked zones.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)


class ZoneDetector:
    """Detects if points are within defined polygon zones."""

    def __init__(self, zones_config: Dict[str, Any]):
        """
        Initialize zone detector with zone configuration.

        Args:
            zones_config: Dict with camera_id as key, containing list of zones
                         Format: {
                             "CAM-ID": {
                                 "zones": [
                                     {
                                         "name": "parking_zone_1",
                                         "type": "parking|double_parking|traffic",
                                         "coordinates": [[x1, y1], [x2, y2], ...]
                                     }
                                 ]
                             }
                         }
        """
        self.zones_config = zones_config
        # Store normalized polygon coordinates
        self.polygons: Dict[str, List[List[Tuple[float, float]]]] = {}
        self._parse_zones()

    def _parse_zones(self):
        """Parse zone configuration into normalized polygons."""
        for camera_id, camera_config in self.zones_config.items():
            self.polygons[camera_id] = {}
            if "zones" not in camera_config:
                continue

            for zone in camera_config["zones"]:
                zone_name = zone.get("name", "")
                zone_type = zone.get("type", "")
                coordinates = zone.get("coordinates", [])

                # Convert to normalized tuples (0-1 range)
                polygon = [(float(x), float(y)) for x, y in coordinates]
                key = f"{zone_name}:{zone_type}"
                self.polygons[camera_id][key] = {
                    "polygon": polygon,
                    "name": zone_name,
                    "type": zone_type,
                }

    def get_zone_coordinates(self, camera_id: str, zone_name: str) -> Optional[List[List[float]]]:
        """
        Get zone coordinates by camera and zone name.

        Args:
            camera_id: Camera identifier
            zone_name: Zone name

        Returns:
            List of [x, y] coordinates or None if zone not found
        """
        if camera_id not in self.zones_config:
            return None

        camera_config = self.zones_config[camera_id]
        if "zones" not in camera_config:
            return None

        for zone in camera_config["zones"]:
            if zone.get("name") == zone_name:
                return zone.get("coordinates", [])

        return None

    def point_in_polygon(
        self, point: Tuple[float, float], polygon: List[Tuple[float, float]]
    ) -> bool:
        """
        Check if point is inside polygon using ray casting algorithm.

        Args:
            point: (x, y) normalized coordinates (0-1)
            polygon: List of (x, y) vertices defining polygon boundary

        Returns:
            True if point is inside polygon, False otherwise
        """
        x, y = point
        inside = False
        n = len(polygon)

        for i in range(n):
            x1, y1 = polygon[i]
            x2, y2 = polygon[(i + 1) % n]

            # Ray casting algorithm
            if ((y1 > y) != (y2 > y)) and (
                x < (x2 - x1) * (y - y1) / (y2 - y1 + 1e-9) + x1
            ):
                inside = not inside

        return inside

    def get_vehicle_zones(
        self,
        camera_id: str,
        detection: Dict[str, Any],
        normalized: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Get all zones that contain a vehicle detection.

        Args:
            camera_id: Camera identifier
            detection: Vehicle detection dict with cx_norm, cy_norm (or cx, cy, img_w, img_h)
            normalized: If True, use normalized coordinates; if False, use pixel coords

        Returns:
            List of zone dicts containing: name, type, polygon
        """
        if camera_id not in self.polygons:
            return []

        # Get normalized point coordinates
        if normalized:
            point = (detection["cx_norm"], detection["cy_norm"])
        else:
            point = (
                detection["cx_norm"],
                detection["cy_norm"],
            )

        zones_hit = []
        for key, zone_info in self.polygons[camera_id].items():
            polygon = zone_info["polygon"]
            if self.point_in_polygon(point, polygon):
                zones_hit.append(
                    {
                        "name": zone_info["name"],
                        "type": zone_info["type"],
                        "polygon": polygon,
                    }
                )

        return zones_hit

    def filter_detections_by_zone(
        self,
        camera_id: str,
        detections: List[Dict[str, Any]],
        zone_type: str,
    ) -> List[Dict[str, Any]]:
        """
        Filter detections to only those within zones of specified type.

        Args:
            camera_id: Camera identifier
            detections: List of vehicle detections
            zone_type: Filter by zone type (e.g., "parking", "double_parking", "traffic")

        Returns:
            Filtered list of detections that are in zones of specified type
        """
        filtered = []
        for detection in detections:
            zones = self.get_vehicle_zones(camera_id, detection, normalized=True)
            for zone in zones:
                if zone["type"] == zone_type:
                    filtered.append({**detection, "zone": zone})
                    break  # Only add once

        return filtered

    def get_detections_in_any_zone_of_type(
        self,
        camera_id: str,
        detections: List[Dict[str, Any]],
        zone_type: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group detections by zone, filtering by type.

        Args:
            camera_id: Camera identifier
            detections: List of vehicle detections
            zone_type: Filter by zone type

        Returns:
            Dict mapping zone name to list of detections in that zone
        """
        zones_to_detections: Dict[str, List[Dict[str, Any]]] = {}

        for detection in detections:
            zones = self.get_vehicle_zones(camera_id, detection, normalized=True)
            for zone in zones:
                if zone["type"] == zone_type:
                    zone_name = zone["name"]
                    if zone_name not in zones_to_detections:
                        zones_to_detections[zone_name] = []
                    zones_to_detections[zone_name].append(detection)

        return zones_to_detections

    def get_zone_by_name(
        self,
        camera_id: str,
        zone_name: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get zone configuration by name.

        Args:
            camera_id: Camera identifier
            zone_name: Name of the zone

        Returns:
            Zone configuration dict or None
        """
        if camera_id not in self.zones_config:
            return None

        camera_config = self.zones_config[camera_id]
        if "zones" not in camera_config:
            return None

        for zone in camera_config["zones"]:
            if zone.get("name") == zone_name:
                return zone

        return None

    def is_point_before_line(
        self,
        point: Tuple[float, float],
        line_coords: List[List[float]],
        img_h: int = 720,
        img_w: int = 1280,
    ) -> bool:
        """
        Check if a normalized point is before (on safe side of) a stop line.
        Stop line is represented as a line segment.

        Args:
            point: (x_norm, y_norm) - normalized coordinates
            line_coords: [[x1, y1], [x2, y2]] - normalized stop line endpoints
            img_h: Image height in pixels
            img_w: Image width in pixels

        Returns:
            True if point is on safe side of line (before the line)
        """
        if len(line_coords) < 2:
            return True
        
        # Safety check for None values in point
        if point is None or point[0] is None or point[1] is None:
            return True
        
        # Safety check for None values in line coordinates
        if (line_coords[0] is None or line_coords[1] is None or
            line_coords[0][0] is None or line_coords[0][1] is None or
            line_coords[1][0] is None or line_coords[1][1] is None):
            return True

        # Convert to pixel coordinates
        px = point[0] * img_w
        py = point[1] * img_h
        x1 = line_coords[0][0] * img_w
        y1 = line_coords[0][1] * img_h
        x2 = line_coords[1][0] * img_w
        y2 = line_coords[1][1] * img_h
        
        # Safety check after conversion
        if None in (px, py, x1, y1, x2, y2):
            return True

        # Calculate which side of the line the point is on
        # Using cross product: (P - A) × (B - A)
        cross_product = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)

        # Returns True if on negative side (safe side)
        return cross_product < 0

    def has_crossed_stop_line(
        self,
        current_detection: Dict[str, Any],
        previous_detection: Optional[Dict[str, Any]],
        stop_line_coords: List[List[float]],
        img_h: int = 720,
        img_w: int = 1280,
    ) -> bool:
        """
        Check if vehicle has crossed a stop line between two frames.

        Args:
            current_detection: Current detection with cx, cy (normalized or pixel)
            previous_detection: Previous detection or None
            stop_line_coords: [[x1, y1], [x2, y2]] normalized stop line
            img_h: Image height
            img_w: Image width

        Returns:
            True if vehicle just crossed the stop line
        """
        # Safety check for None values first
        if current_detection is None or current_detection.get("cx") is None or current_detection.get("cy") is None:
            return False
        
        # Normalize current position
        curr_x_norm = current_detection["cx"] / img_w if current_detection["cx"] > 1 else current_detection["cx"]
        curr_y_norm = current_detection["cy"] / img_h if current_detection["cy"] > 1 else current_detection["cy"]

        curr_before_line = self.is_point_before_line(
            (curr_x_norm, curr_y_norm),
            stop_line_coords,
            img_h,
            img_w,
        )

        if previous_detection is None:
            # No previous frame, can't determine crossing
            return False

        # Safety check for previous detection None values
        if previous_detection.get("cx") is None or previous_detection.get("cy") is None:
            return False
        
        # Normalize previous position
        prev_x_norm = previous_detection["cx"] / img_w if previous_detection["cx"] > 1 else previous_detection["cx"]
        prev_y_norm = previous_detection["cy"] / img_h if previous_detection["cy"] > 1 else previous_detection["cy"]

        prev_before_line = self.is_point_before_line(
            (prev_x_norm, prev_y_norm),
            stop_line_coords,
            img_h,
            img_w,
        )

        # Crossing if was before and now is not (or was not and now is)
        return prev_before_line != curr_before_line

    def is_past_stop_line(
        self,
        detection: Dict[str, Any],
        stop_line_coords: List[List[float]],
        img_h: int = 720,
        img_w: int = 1280,
    ) -> bool:
        """
        Check if vehicle is currently past (on violation side of) stop line.

        Args:
            detection: Detection with cx, cy
            stop_line_coords: [[x1, y1], [x2, y2]] normalized stop line
            img_h: Image height
            img_w: Image width

        Returns:
            True if vehicle is past the stop line
        """
        # Safety check for None values
        if detection is None or detection.get("cx") is None or detection.get("cy") is None:
            return False
        
        x_norm = detection["cx"] / img_w if detection["cx"] > 1 else detection["cx"]
        y_norm = detection["cy"] / img_h if detection["cy"] > 1 else detection["cy"]

        # True if NOT before the line (i.e., past it)
        return not self.is_point_before_line((x_norm, y_norm), stop_line_coords, img_h, img_w)

    @staticmethod
    def load_zones_from_file(zones_file: Path) -> Dict[str, Any]:
        """
        Load zone configuration from JSON file.

        Args:
            zones_file: Path to zones.json file

        Returns:
            Parsed zone configuration dictionary
        """
        if not zones_file.exists():
            logger.warning(f"Zones file not found: {zones_file}")
            return {}

        with open(zones_file, "r") as f:
            return json.load(f)
