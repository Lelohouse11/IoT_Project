"""
Red light violation tracker for detecting vehicles running red lights.
Tracks vehicles crossing stop lines during red light states.
"""

from typing import Dict, List, Tuple, Any, Optional, Set
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class RedLightViolationTracker:
    """
    Tracks vehicles that cross stop lines while traffic light is red.
    Prevents duplicate violations for the same vehicle.
    """

    def __init__(self, cooldown_sec: float = 30.0):
        """
        Initialize red light violation tracker.
        
        Args:
            cooldown_sec: Seconds before same vehicle can trigger another violation
        """
        self.cooldown_sec = cooldown_sec
        
        # Track violations: {track_id: {"violation_time": datetime, "position_key": tuple}}
        self.violations: Dict[int, Dict[str, Any]] = {}
        
        # Track vehicles that have crossed stop line: {track_id: position_key}
        self.crossed_vehicles: Dict[int, Tuple[int, int]] = {}

    def get_position_key(self, detection: Dict[str, Any]) -> Tuple[int, int]:
        """Get quantized position key from detection."""
        return (round(detection["cx"] / 50) * 50, round(detection["cy"] / 50) * 50)

    def check_violation(
        self,
        detection: Dict[str, Any],
        light_is_red: bool,
        vehicle_crossed_stop_line: bool,
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if vehicle has violated a red light.
        
        Args:
            detection: Detection dictionary with track_id, cx, cy
            light_is_red: Boolean indicating if traffic light is currently red
            vehicle_crossed_stop_line: Boolean indicating if vehicle is past stop line
            
        Returns:
            (is_violation, violation_id)
            - is_violation: True if new violation detected
            - violation_id: Unique ID for this violation (for pairing with backend)
        """
        track_id = detection.get("track_id", -1)
        if track_id < 0:
            return False, None
        
        pos_key = self.get_position_key(detection)
        now = datetime.now()
        
        # Clean up old violations outside cooldown window
        self.violations = {
            tid: v for tid, v in self.violations.items()
            if (now - v["violation_time"]).total_seconds() < self.cooldown_sec
        }
        
        # If light is not red, just track that vehicle crossed the line
        if not light_is_red:
            if vehicle_crossed_stop_line:
                self.crossed_vehicles[track_id] = pos_key
            else:
                self.crossed_vehicles.pop(track_id, None)
            return False, None
        
        # Light IS red
        # Check if vehicle just crossed the stop line (was not before, now is)
        was_before_line = track_id in self.crossed_vehicles
        is_now_past_line = vehicle_crossed_stop_line
        
        if is_now_past_line:
            self.crossed_vehicles[track_id] = pos_key
            
            # Check if this is a new violation (not already recorded in cooldown)
            if track_id not in self.violations:
                # New violation!
                violation_id = f"{track_id}_{int(now.timestamp() * 1000)}"
                self.violations[track_id] = {
                    "violation_time": now,
                    "position_key": pos_key,
                    "violation_id": violation_id,
                }
                logger.info(f"Red light violation: track_id={track_id}, violation_id={violation_id}")
                return True, violation_id
        else:
            # Vehicle moved back before the line
            self.crossed_vehicles.pop(track_id, None)
        
        return False, None

    def is_vehicle_violating(self, track_id: int) -> bool:
        """Check if vehicle has a recent violation."""
        now = datetime.now()
        if track_id in self.violations:
            violation = self.violations[track_id]
            if (now - violation["violation_time"]).total_seconds() < self.cooldown_sec:
                return True
        return False

    def get_violation_id(self, track_id: int) -> Optional[str]:
        """Get violation ID for a vehicle."""
        if track_id in self.violations:
            return self.violations[track_id].get("violation_id")
        return None

    def reset_violation(self, track_id: int):
        """Reset violation for a track ID (e.g., vehicle left camera view)."""
        self.violations.pop(track_id, None)
        self.crossed_vehicles.pop(track_id, None)
