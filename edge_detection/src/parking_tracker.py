"""
Parking tracker module for vehicle parking event detection.
Tracks vehicle IDs in parking zones and generates entry/exit events.
"""

from typing import Dict, List, Tuple, Any
from datetime import datetime
import uuid


class ParkingTracker:
    """Tracks vehicle IDs in parking zones and generates entry/exit events."""


    def __init__(
        self,
        exit_cooldown_sec: float = 10.0,
        exit_debounce_frames: int = 100,
    ):
        """Initialize parking tracker.
        
        Args:
            exit_cooldown_sec: Seconds before same position can generate another exit
            exit_debounce_frames: Frames to wait before confirming exit (prevents false exits from tracking loss)
        """
        self.exit_cooldown_sec = exit_cooldown_sec
        self.exit_debounce_frames = exit_debounce_frames
        
        self.zone_tracked_ids: Dict[str, Dict[int, Dict[str, Any]]] = {}
        self.seen_track_ids: Dict[str, set] = {}
        self.recent_exits: Dict[str, List[Dict[str, Any]]] = {}

    def check_parking_entry(
        self,
        zone_name: str,
        detection: Dict[str, Any],
        stationary_seconds: float,
        parking_threshold_sec: float = 30.0,
    ) -> Tuple[bool, str | None]:
        """Generate entry event if vehicle meets parking criteria.
        
        Returns (is_new_entry, event_id).
        """
        if stationary_seconds is None or stationary_seconds < parking_threshold_sec:
            return False, None
        
        track_id = detection.get("track_id", -1)
        if track_id < 0:
            return False, None
        
        if zone_name not in self.zone_tracked_ids:
            self.zone_tracked_ids[zone_name] = {}
            self.recent_exits[zone_name] = []
            self.seen_track_ids[zone_name] = set()
        
        if track_id in self.seen_track_ids[zone_name]:
            return False, None
        
        now = datetime.now()
        self.recent_exits[zone_name] = [
            e for e in self.recent_exits[zone_name] 
            if (now - e["exit_time"]).total_seconds() < self.exit_cooldown_sec
        ]
        
        event_id = str(uuid.uuid4())
        self.zone_tracked_ids[zone_name][track_id] = {
            "entry_time": now,
            "event_id": event_id,
            "missing_frames": 0,
        }
        self.seen_track_ids[zone_name].add(track_id)
        return True, event_id

    def check_parking_exit(
        self,
        zone_name: str,
        vehicles_in_zone: List[Dict[str, Any]],
        current_frame: int = 0,
    ) -> List[Tuple[str, float, int]]:
        """Generate exit events for tracked IDs missing for too long.
        
        Returns list of (event_id, parking_duration_sec, track_id).
        """
        if zone_name not in self.zone_tracked_ids:
            return []
        
        exited_vehicles = []
        now = datetime.now()
        
        current_track_ids = {det.get("track_id") for det in vehicles_in_zone 
                             if det.get("track_id", -1) >= 0}
        
        for track_id in list(self.zone_tracked_ids[zone_name].keys()):
            vehicle_data = self.zone_tracked_ids[zone_name][track_id]
            
            if track_id not in current_track_ids:
                vehicle_data["missing_frames"] += 1
            else:
                vehicle_data["missing_frames"] = 0
            
            if vehicle_data["missing_frames"] >= self.exit_debounce_frames:
                duration = (now - vehicle_data["entry_time"]).total_seconds()
                
                if duration >= 30.0:
                    exited_vehicles.append((vehicle_data["event_id"], duration, track_id))
                
                self.recent_exits[zone_name].append({
                    "exit_time": now,
                    "event_id": vehicle_data["event_id"],
                    "track_id": track_id,
                })
                
                del self.zone_tracked_ids[zone_name][track_id]
                self.seen_track_ids[zone_name].discard(track_id)
        
        return exited_vehicles

