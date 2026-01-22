"""
Configuration management for edge detection system.
Loads and manages settings for YOLO processing, zone detection, and backend communication.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for edge detection."""

    # Defaults
    DEFAULTS = {
        "backend_url": "http://localhost:8003/api/camera",
        "model_path": "yolov8n.pt",
        "device": "cpu",
        "confidence_threshold": 0.5,
        "max_retries": 5,
        "request_timeout": 30,
        # Timing thresholds (seconds)
        "parking_stationary_duration": 30,
        "double_parking_stationary_duration": 60,
        "traffic_monitoring_interval": 60,
        # Tracking parameters
        "stationary_epsilon_px": 10.0,
        "fps": 30.0,
        # Processing
        "max_frames_to_process": None,  # None = process all frames
    }

    def __init__(self, config_file: Optional[Path] = None):
        """
        Initialize configuration.

        Args:
            config_file: Path to config.json (optional). If not provided,
                        uses environment or defaults.
        """
        self.config: Dict[str, Any] = self.DEFAULTS.copy()

        # Load from config file if provided
        if config_file and config_file.exists():
            with open(config_file, "r") as f:
                user_config = json.load(f)
                self.config.update(user_config)
            logger.info(f"Loaded config from {config_file}")
        else:
            logger.info("Using default configuration")
        
        # Override with environment variables if present
        env_overrides = {
            "backend_url": os.getenv("BACKEND_URL"),
            "model_path": os.getenv("YOLO_MODEL_PATH"),
            "device": os.getenv("YOLO_DEVICE"),
        }
        
        for key, value in env_overrides.items():
            if value is not None:
                self.config[key] = value
                logger.info(f"Config override from env: {key} = {value}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value."""
        self.config[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Get all configuration as dictionary."""
        return self.config.copy()

    @staticmethod
    def create_default_config_file(config_file: Path):
        """Create a default config.json file."""
        config_file.parent.mkdir(parents=True, exist_ok=True)

        default_config = {
            "backend_url": "http://localhost:8003/api/camera",
            "model_path": "yolov8n.pt",
            "device": "cpu",  # "cpu" or "cuda:0"
            "confidence_threshold": 0.5,
            "max_retries": 5,
            "request_timeout": 30,
            "parking_stationary_duration": 30,
            "double_parking_stationary_duration": 60,
            "traffic_monitoring_interval": 60,
            "stationary_epsilon_px": 10.0,
            "fps": 30.0,
            "max_frames_to_process": None,
        }

        with open(config_file, "w") as f:
            json.dump(default_config, f, indent=2)

        logger.info(f"Created default config at {config_file}")


def load_camera_zones(zones_file: Path) -> Dict[str, Any]:
    """
    Load camera zone configuration from zones.json.

    Args:
        zones_file: Path to zones.json

    Returns:
        Dictionary mapping camera_id to zone configuration
    """
    if not zones_file.exists():
        logger.warning(f"Zones file not found: {zones_file}")
        return {}

    with open(zones_file, "r") as f:
        zones = json.load(f)

    logger.info(f"Loaded zones for cameras: {list(zones.keys())}")
    return zones


def get_camera_id_from_filename(video_filename: str) -> Optional[str]:
    """
    Extract camera ID from video filename.

    Expected format: {CAMERA_ID}_*.mp4 or {CAMERA_ID}_*.avi etc.
    Example: CAM-VRACH-01_stream.mp4 -> CAM-VRACH-01

    Args:
        video_filename: Video filename

    Returns:
        Camera ID or None if not found
    """
    # Remove extension
    base_name = Path(video_filename).stem

    # Split on first underscore
    if "_" in base_name:
        camera_id = base_name.split("_")[0]
        return camera_id

    return None
