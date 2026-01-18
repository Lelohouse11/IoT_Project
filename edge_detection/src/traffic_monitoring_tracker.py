"""Traffic monitoring event tracker with configurable interval-based event generation."""


class TrafficMonitoringTracker:
    """Enforces periodic traffic monitoring event generation."""
    
    def __init__(self, interval_frames: int = 1500):
        """
        Initialize traffic monitoring tracker.
        
        Args:
            interval_frames: Frame interval between events (default: 1500 frames = 60s @ 25fps)
        """
        self.interval_frames = interval_frames
        self.last_event_frame = {}
    
    def should_send_event(self, camera_id: str, current_frame_number: int) -> bool:
        """
        Determine if a traffic monitoring event should be sent.
        
        Args:
            camera_id: Camera identifier
            current_frame_number: Current frame number
            
        Returns:
            True if sufficient frames have elapsed since last event
        """
        if camera_id not in self.last_event_frame:
            self.last_event_frame[camera_id] = 0
        
        last_frame = self.last_event_frame[camera_id]
        frames_since_last = current_frame_number - last_frame
        
        should_send = frames_since_last >= self.interval_frames
        
        if should_send:
            self.last_event_frame[camera_id] = current_frame_number
        
        return should_send
    
    def set_interval_seconds(self, seconds: float, fps: float = 25):
        """
        Configure interval in seconds.
        
        Args:
            seconds: Interval in seconds
            fps: Frames per second
        """
        self.interval_frames = int(seconds * fps)
    
    def get_interval_frames(self) -> int:
        """Get current interval in frames."""
        return self.interval_frames
    
    def reset_camera(self, camera_id: str):
        """Reset frame counter for specific camera."""
        if camera_id in self.last_event_frame:
            self.last_event_frame[camera_id] = 0
