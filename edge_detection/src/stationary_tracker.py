"""
Stationary tracker module for detecting when vehicles stop moving.
Tracks vehicle position over frames to determine stationary state.
"""

from typing import Dict, Any, Optional
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class StationaryTracker:
    """Tracks vehicle movement to detect stationary state."""

    def __init__(self, epsilon_px: float = 10.0, fps: float = 30.0):
        """
        Initialize stationary tracker.

        Args:
            epsilon_px: Distance threshold in pixels - if vehicle center moves
                       less than this between frames, considered stationary
            fps: Frames per second (used to calculate time duration)
        """
        self.epsilon_px = epsilon_px
        self.fps = fps

        # Track state: {track_id: {"last_x": px, "last_y": px, "stationary_start_frame": frame_idx}}
        self.track_state: Dict[int, Dict[str, Any]] = defaultdict(lambda: {})

    def update(
        self,
        detection: Dict[str, Any],
        frame_idx: int,
    ) -> Dict[str, Any]:
        """
        Update tracker with vehicle detection.

        Args:
            detection: Detection dict with track_id, cx (pixel), cy (pixel)
            frame_idx: Current frame index

        Returns:
            Updated detection dict with added fields:
                - is_stationary: bool
                - stationary_duration_sec: float (time since movement stopped)
                - stationary_start_frame: int (frame when movement stopped)
        """
        track_id = detection["track_id"]
        cx = detection["cx"]
        cy = detection["cy"]

        if track_id is None:
            return {**detection, "is_stationary": False, "stationary_duration_sec": 0}

        state = self.track_state[track_id]

        # Initialize state if new track
        if "last_x" not in state:
            state["last_x"] = cx
            state["last_y"] = cy
            state["stationary_start_frame"] = frame_idx
            return {
                **detection,
                "is_stationary": False,
                "stationary_duration_sec": 0,
                "stationary_start_frame": frame_idx,
            }

        # Calculate distance moved
        distance = (
            (cx - state["last_x"]) ** 2 + (cy - state["last_y"]) ** 2
        ) ** 0.5

        # If vehicle moved more than epsilon, reset stationary timer
        if distance > self.epsilon_px:
            state["last_x"] = cx
            state["last_y"] = cy
            state["stationary_start_frame"] = frame_idx
            return {
                **detection,
                "is_stationary": False,
                "stationary_duration_sec": 0,
                "stationary_start_frame": frame_idx,
            }

        # Calculate stationary duration
        stationary_frames = frame_idx - state["stationary_start_frame"]
        stationary_duration_sec = stationary_frames / self.fps

        return {
            **detection,
            "is_stationary": True,
            "stationary_duration_sec": stationary_duration_sec,
            "stationary_start_frame": state["stationary_start_frame"],
        }

    def reset_track(self, track_id: int):
        """
        Reset tracking state for a vehicle (e.g., when it leaves frame).

        Args:
            track_id: Track identifier to reset
        """
        if track_id in self.track_state:
            del self.track_state[track_id]

    def get_stationary_vehicles(
        self,
        detections: list[Dict[str, Any]],
        min_duration_sec: float,
    ) -> list[Dict[str, Any]]:
        """
        Filter detections to only stationary vehicles.

        Args:
            detections: List of detection dicts (already processed with update())
            min_duration_sec: Minimum stationary duration to include

        Returns:
            List of detections that have been stationary for >= min_duration_sec
        """
        return [
            d
            for d in detections
            if d.get("is_stationary", False)
            and d.get("stationary_duration_sec", 0) >= min_duration_sec
        ]

    def clean_old_tracks(self, max_frames_unseen: int = 300):
        """
        Clean up tracking state for vehicles not seen in a while.

        Args:
            max_frames_unseen: Remove tracks not seen for this many frames
        """
        # This would be called periodically, but for simplicity we're not tracking
        # the last frame seen. In production, track "last_seen_frame" in state.
        pass
