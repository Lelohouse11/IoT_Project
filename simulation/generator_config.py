"""Centralized configuration for all simulation generators."""

from dataclasses import dataclass
from typing import Tuple

# ============================================================================
# ORION CONTEXT BROKER SETTINGS
# ============================================================================

ORION_BASE_URL = "http://orion:1026"
FIWARE_SERVICE_PATH = "/"
REQUEST_TIMEOUT = 5


# ============================================================================
# ACCIDENT GENERATOR CONFIG
# ============================================================================

@dataclass
class AccidentGeneratorConfig:
    """Configuration for accident event generation."""
    center_lat: float = 38.2464
    center_lng: float = 21.7346
    max_offset_deg: float = 0.02
    interval_sec: float = 3.0
    prob_new: float = 0.6
    prob_update: float = 0.25
    prob_clear: float = 0.15
    severity_update_probability: float = 0.2
    location_jitter: float = 0.001


# ============================================================================
# PARKING GENERATOR CONFIG
# ============================================================================

@dataclass
class ParkingGeneratorConfig:
    """Configuration for parking occupancy simulation."""
    interval_sec: float = 8.0
    max_step_change: int = 4
    jitter_prob: float = 0.45


# ============================================================================
# TRAFFIC GENERATOR CONFIG
# ============================================================================

@dataclass
class TrafficGeneratorConfig:
    """Configuration for traffic flow simulation."""
    interval_sec: float = 2.0
    base_intensity_range: Tuple[int, int] = (300, 1100)  # vehicles/hour
    base_speed_range: Tuple[float, float] = (28.0, 55.0)  # km/h
    speed_jitter: float = 6.0
    congestion_chance: float = 0.18
    congestion_speed_drop: float = 0.45  # multiply by this factor on congestion
    congestion_intensity_boost: float = 1.35
    jam_density: float = 120.0  # vehicles/km where traffic is considered jammed


# ============================================================================
# TRAFFIC VIOLATION GENERATOR CONFIG
# ============================================================================

@dataclass
class TrafficViolationGeneratorConfig:
    """Configuration for traffic violation event generation."""
    center_lat: float = 38.2464
    center_lng: float = 21.7346
    max_offset_deg: float = 0.02
    interval_sec: float = 4.0


# ============================================================================
# VIOLATION TYPES
# ============================================================================

VIOLATION_TYPES = [
    {"code": "double-parking", "desc": "Double parking detected"},
    {"code": "red-light", "desc": "Red light violation"},
    {"code": "no-stopping", "desc": "Stopping in no stopping zone"},
    {"code": "near-intersection", "desc": "Parking too close to intersection"},
]

# ============================================================================
# EQUIPMENT CONFIGURATION
# ============================================================================

EQUIPMENT_IDS = ("CAM-01", "CAM-02", "SENSOR-05", "SENSOR-09")
EQUIPMENT_TYPES = ("camera", "roadsideSensor")
